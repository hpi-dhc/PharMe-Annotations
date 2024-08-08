import copy
import csv
import json
import os
import requests
from bs4 import BeautifulSoup

from constants import ANY_OTHER_PHENOTYPE, FDA_STANDARD, \
    IGNORE_GENES_NOT_IN_CPIC_LOOKUPS, RECOMMENDATIONLESS_PREFIX, TEMP_DIR, \
    UNRESOLVED_DIR, fdaFurtherGenesImplication

FDA_URL = 'https://www.fda.gov/medical-devices/precision-medicine/table-pharmacogenetic-associations'
FDA_INFO_FILE = 'FDA_info.csv'

class UnexpectedWebpageFormatError(Exception):
    def __init__(self, reason=None):
        message = '[ERROR] Unexpected webpage format'
        if reason is not None:
            message += f': {reason}'
        super().__init__(message)

class NoRxCuiFoundError(Exception):
    def __init__(self, drugName):
        message = f'[ERROR] No RxCui found for {drugName}'
        super().__init__(message)

def getFdaContent():
    fdaFileName = 'fda-content.html'
    fdaFilePath = os.path.join(TEMP_DIR, fdaFileName)
    if os.path.isfile(fdaFilePath):
        with open(fdaFilePath, 'r') as fdaFile:
            return fdaFile.read()
    fdaContent = requests.get(FDA_URL).text
    with open(fdaFilePath, 'w') as fdaFile:
        fdaFile.write(fdaContent)
    return fdaContent

def getSectionLink(soup, id):
    sectionLink = soup.find('a', id=id)
    if sectionLink is None:
        raise UnexpectedWebpageFormatError(f'no link with id {id}')
    return sectionLink

def getTable(soup, id):
    sectionLink = getSectionLink(soup, id)
    table = sectionLink.find_next('table')
    if table is None:
        raise UnexpectedWebpageFormatError(f'no table after link with id {id}')
    return table

def _getCpicInformation(urlResource, params, fileName, responseHandler):
    cpicUrl = f'https://api.cpicpgx.org/v1/{urlResource}'
    cpicFilePath = os.path.join(TEMP_DIR, fileName)
    if os.path.isfile(cpicFilePath):
        with open(cpicFilePath, 'r') as cpicFile:
            return  json.load(cpicFile)
    cpicInformation = \
        responseHandler(requests.get(cpicUrl, params=params).json())
    with open(cpicFilePath, 'w') as cpicFile:
        json.dump(cpicInformation, cpicFile, indent=4)
    return cpicInformation

def getCpicDrugs():
    def responseHandler(cpicRecommendations):
        cpicDrugs = set()
        for recommendation in cpicRecommendations:
            cpicDrugs.add(recommendation['drug']['name'])
        with open(
            os.path.join(UNRESOLVED_DIR, f'{RECOMMENDATIONLESS_PREFIX}CPIC.json'),
            'r',
        ) as manualCpicFile:
            manualCpicGuidelines = json.load(manualCpicFile)
            for entry in manualCpicGuidelines:
                cpicDrugs.add(entry['drug']['name'])
        cpicDrugs = list(cpicDrugs)
    return _getCpicInformation(
        'recommendation',
        { 'select': 'drug(name)' },
        'cpic-drugs.json',
        responseHandler,
    )

def getGenesInCpicLookups():
    def responseHandler(cpicGenes):
        return list(set(map(lambda geneInfo: geneInfo['genesymbol'], cpicGenes)))
        
    return _getCpicInformation(
        'diplotype',
        { 'select': 'genesymbol' },
        'cpic-genes.json',
        responseHandler,
    )

def addToFdaInfoFile(drug, gene, section, in_cpic_lookups):
    with open(FDA_INFO_FILE, 'a') as infoFile:
        writer = csv.writer(infoFile)
        writer.writerow([drug, gene, section, in_cpic_lookups])

def getRxCui(drug):
    rxCuis = {}
    rxCuiPath = os.path.join(TEMP_DIR, 'rx-cuis.json')
    if os.path.isfile(rxCuiPath):
        with open(rxCuiPath, 'r')  as rxCuiFile:
            rxCuis = json.load(rxCuiFile)
    rxCui = None
    if drug in rxCuis:
        rxCui = rxCuis[drug]
    else:
        rxUrl = f'https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug}'
        rxNormResponse = requests.get(rxUrl).json()['idGroup']
        if 'rxnormId' in rxNormResponse:
            rxNorms = rxNormResponse['rxnormId']
            if len(rxNorms) != 1:
                raise Exception('[ERROR] Expecting Rx response of length 1')
            rxCui = rxNorms[0]
        rxCuis[drug] = rxCui
        with open(rxCuiPath, 'w') as rxCuiFile:
            json.dump(rxCuis, rxCuiFile, indent=4)
    # Keep a record that no rxCui exists in "cache" but throw exception to be
    # handled elsewhere
    if rxCui is None:
        raise NoRxCuiFoundError(drugName=drug)
    return rxCui

def formatRxCui(rxCui):
    return f'RxNorm:{rxCui}'

def cpicFormatFdaDrug(fdaDrug):
    return fdaDrug.lower().replace(' and ', ' / ').strip()

def cpicFormatFdaGenes(fdaGenes):
    return fdaGenes.split(' and/or ')

# This is a bit hacky as it is very tailored to the content present at the
# time of coding
def cpicFormatFdaPhenotypes(fdaPhenotypes):
    cpicPhenotypes = []
    fdaPhenotypes = fdaPhenotypes.replace('allele positive', 'positive')
    fdaPhenotypes = fdaPhenotypes.replace('allele negative', 'negative')
    if 'poor' in fdaPhenotypes:
        cpicPhenotypes.append('Poor Metabolizer')
    if 'intermediate' in fdaPhenotypes:
        cpicPhenotypes.append('Intermediate Metabolizer')
    if 'ultrarapid' in fdaPhenotypes:
        cpicPhenotypes.append('Ultrarapid Metabolizer')
    if 'normal' in fdaPhenotypes:
        cpicPhenotypes.append('Normal Metabolizer')
    if len(cpicPhenotypes) == 0:
        cpicPhenotypes = [fdaPhenotypes]
    return cpicPhenotypes

def main():
    soup = BeautifulSoup(getFdaContent(), 'html.parser')
    includedSections = { 'section1': 'Section 1', 'section2': 'Section 2' }
    cpicDrugs = getCpicDrugs()
    fdaAssociations = {}
    multipleRows = set()
    with open(FDA_INFO_FILE, 'w') as fdaInfoFile:
        fdaInfoFile.write('drug,gene,section,in_cpic_lookups\n')
    for sectionId, sectionName in includedSections.items():
        sectionTable = getTable(soup, sectionId)
        sectionSourceName = f'Table of Pharmacogenetic Associations ({sectionName})'
        sectionSourceUrl = f"{FDA_URL}#{getSectionLink(soup, sectionId)['name']}"
        for row in sectionTable.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) == 0:
                continue
            if len(cells) != 4:
                raise UnexpectedWebpageFormatError('expecting 4 table cells')
            
            drug = cpicFormatFdaDrug(cells[0].text)

            if drug in cpicDrugs:
                print(f'[INFO] Skipping {drug} (included in CPIC)')
                continue

            genes = cpicFormatFdaGenes(cells[1].text)
            cpicGenes = getGenesInCpicLookups()

            for gene in genes:
                addToFdaInfoFile(drug, gene, sectionName, gene in cpicGenes)

            includedGenes = []
            if IGNORE_GENES_NOT_IN_CPIC_LOOKUPS:
                includedGenes = list(filter(
                    lambda gene: gene in cpicGenes,
                    genes,
                ))
            else:
                includedGenes = genes
            
            if len(includedGenes) == 0:
                print(f'[INFO] Skipping {drug} ({", ".join(genes)} not in CPIC lookups)')
                continue

            if drug in fdaAssociations:
                multipleRows.add(drug)
                continue
            
            skippedGenes = list(filter(lambda gene: not gene in includedGenes, genes))
            print(f'[INFO] Skipping {", ".join(skippedGenes)} for {drug} (not in CPIC lookups)')

            phenotypes = cpicFormatFdaPhenotypes(cells[2].text)
            description = cells[3].text
            if len(skippedGenes) > 0:
                description = f'{description} ({", ".join(skippedGenes)} ' \
                    'also included in FDA guideline but not in CPIC lookups ' \
                        'and therefore not shown in PharMe)'

            # Only case with multiple genes in FDA and not in CPIC is Belzutifan,
            # which has only one phenotype (and second gene is potentially
            # ignored anyways), so not implemented multiple phenotypes (would
            # need to implement combinations of multiple phenotypes, too).
            if len(includedGenes) > 1 and  len(phenotypes) > 1:
                print(f'[WARNING] Skipping {drug} (multiple genes and phenotypes ' \
                        'not implemented yet, will lack phenotype combinations)')
                continue

            fdaAssociations[drug] = {
                'genes': includedGenes,
                'phenotypes': phenotypes,
                'description': description,
                'guideline': {
                    'name': sectionSourceName,
                    'url': sectionSourceUrl
                }
            }

    for drug in multipleRows:
        del fdaAssociations[drug]
        print(f'[INFO] Skipping {drug} (multiple rows); ' \
              'consider adding manually')

    fdaAnnotations = []
    for drug, fdaAssociation in fdaAssociations.items():
        rxCui = formatRxCui(getRxCui(drug))
        genes = fdaAssociation['genes']
        phenotypes = fdaAssociation['phenotypes']
        description = fdaAssociation['description']
        guideline = fdaAssociation['guideline']

        geneImplications = {}
        for index, gene in enumerate(genes):
            if index == 0:
                geneImplications[gene] = description
            else:
                geneImplications[gene] = fdaFurtherGenesImplication(genes)

        # Create gene and phenotype combinations – for each phenotype, one
        # annotation will be created.
        # If multiple genes are present, include 'Indeterminate' phenotype,
        # as formulation on FDA website is "and/or".
        genePhenotypeCombinations = []
        for phenotype in phenotypes:
            completePhenotype = {}
            anyOtherPhenotype = {}
            for gene in genes:
                completePhenotype[gene] = phenotype
                anyOtherPhenotype[gene] = ANY_OTHER_PHENOTYPE
            genePhenotypeCombinations.append(completePhenotype)
            if len(genes) > 1:
                for gene in genes:
                    geneAnyOtherPhenotype = copy.deepcopy(completePhenotype)
                    geneAnyOtherPhenotype[gene] = ANY_OTHER_PHENOTYPE
                    genePhenotypeCombinations.append(geneAnyOtherPhenotype)
            genePhenotypeCombinations.append(anyOtherPhenotype)

        for genePhenotypeCombination in genePhenotypeCombinations:
            isFallback = all(map(
                lambda phenotype: phenotype == ANY_OTHER_PHENOTYPE,
                genePhenotypeCombination.values(),
            ))
            implications = geneImplications if not isFallback else FDA_STANDARD
            fdaAnnotations.append({
                'drugid': rxCui,
                'drug': {
                    'name': drug
                },
                'phenotypes': genePhenotypeCombination,
                'guideline': guideline,
                'implications': implications,
            })
    with open(os.path.join(UNRESOLVED_DIR, 'FDA.json'), 'w') as unresolvedFile:
        json.dump(fdaAnnotations, unresolvedFile, indent=4)

if __name__ == '__main__':
    main()