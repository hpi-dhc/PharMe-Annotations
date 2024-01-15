import copy
import csv
import json
import os
import requests
from bs4 import BeautifulSoup

from constants import TEMP_DIR, UNRESOLVED_DIR
from constants import CacheMissError

FDA_URL = 'https://www.fda.gov/medical-devices/precision-medicine/table-pharmacogenetic-associations'
FDA_INFO_FILE = 'FDA_info.csv'

class UnexpectedWebpageFormatError(Exception):
    def __init__(self, reason=None):
        message = '[ERROR] Unexpected webpage format'
        if reason is not None:
            message += f': {reason}'
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

def getCpicDrugs():
    cpicUrl = 'https://api.cpicpgx.org/v1/recommendation'
    params = { 'select': 'drug(name)' }
    cpicRecommendationsPath = os.path.join(TEMP_DIR, 'cpic-drugs.json')
    if os.path.isfile(cpicRecommendationsPath):
        with open(cpicRecommendationsPath, 'r') as cpicFile:
            return  json.load(cpicFile)
    cpicRecommendations = requests.get(cpicUrl, params=params).json()
    cpicDrugs = set()
    for recommendation in cpicRecommendations:
        cpicDrugs.add(recommendation['drug']['name'])
    with open(os.path.join(UNRESOLVED_DIR, 'CPIC.json')) as manualCpicFile:
        manualCpicGuidelines = json.load(manualCpicFile)
        for entry in manualCpicGuidelines:
            cpicDrugs.add(entry['drug']['name'])
    cpicDrugs = list(cpicDrugs)
    with open(cpicRecommendationsPath, 'w') as cpicFile:
        json.dump(cpicDrugs, cpicFile, indent=4)
    return cpicDrugs

def addToFdaInfoFile(drug, gene, section):
    with open(FDA_INFO_FILE, 'a') as infoFile:
        writer = csv.writer(infoFile)
        writer.writerow([drug, gene, section])

def rxCuiPath():
    return os.path.join(TEMP_DIR, 'rx-cuis.json')

def areRxCuisCached():
    return os.path.isfile(rxCuiPath())

def getRxCuis():
    rxCuis = {}
    if areRxCuisCached():
        with open(rxCuiPath(), 'r')  as rxCuiFile:
            rxCuis = json.load(rxCuiFile)
    return rxCuis

def getRxCuiForDrug(drug):
    rxUrl = f'https://rxnav.nlm.nih.gov/REST/rxcui.json?name={drug}'
    rxNorms = requests.get(rxUrl).json()['idGroup']['rxnormId']
    if len(rxNorms) != 1:
        raise Exception('[ERROR] Expecting Rx response of length 1')
    rxCui = rxNorms[0]
    return rxCui

def getRxCui(rxCuis, drug):
    if areRxCuisCached():
        if drug not in rxCuis:
            raise CacheMissError(drug, rxCuiPath())
        return rxCuis[drug]
    else:
        rxCui = getRxCuiForDrug(drug)
        rxCuis[drug] = rxCui
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
    skippedRows = set()
    with open(FDA_INFO_FILE, 'w') as fdaInfoFile:
        fdaInfoFile.write('')
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

            for gene in genes:
                addToFdaInfoFile(drug, gene, sectionName)

            if drug in fdaAssociations:
                skippedRows.add(drug)
                continue

            phenotypes = cpicFormatFdaPhenotypes(cells[2].text)

            # Only case with multiple genes in FDA and not in CPIC is Belzutifan,
            # which has only one phenotype, so not implemented multiple phenotypes
            # (would need to implement combinations of multiple phenotypes, too).
            if len(genes) > 1 and  len(phenotypes) > 1:
                print(f'[WARNING] Skipping {drug} (multiple genes and phenotypes ' \
                        'not implemented yet, will lack phenotype combinations)')
                continue

            fdaAssociations[drug] = {
                'genes': genes,
                'phenotypes': phenotypes,
                'description': cells[3].text,
                'guideline': {
                    'name': sectionSourceName,
                    'url': sectionSourceUrl
                }
            }

    for drug in skippedRows:
        del fdaAssociations[drug]
        print(f'[INFO] Skipping {drug} (multiple rows)')

    rxCuis = getRxCuis()
    fdaAnnotations = []
    for drug, fdaAssociation in fdaAssociations.items():
        rxCui = getRxCui(rxCuis, drug)
        genes = fdaAssociation['genes']
        phenotypes = fdaAssociation['phenotypes']
        description = fdaAssociation['description']
        guideline = fdaAssociation['guideline']

        geneImplications = {}
        for index, gene in enumerate(genes):
            if index == 0:
                geneImplications[gene] = description
            else:
                geneImplications[gene] = f'Might be included in {genes[0]} ' \
                    'implication; mind that description might not apply if' \
                    'one gene is "Indeterminate" (generated by script to ' \
                    'match CPIC behavior)'

        # Create gene and phenotype combinations – for each phenotype, one
        # annotation will be created.
        # If multiple genes are present, include 'Indeterminate' phenotype,
        # as formulation on FDA website is "and/or".
        genePhenotypeCombinations = []
        for phenotype in phenotypes:
            completePhenotype = {}
            for gene in genes:
                completePhenotype[gene] = phenotype
            genePhenotypeCombinations.append(completePhenotype)
            if len(genes) > 1:
                indeterminatePhenotypes = []
                for gene in genes:
                    geneUnknownPhenotype = copy.deepcopy(completePhenotype)
                    geneUnknownPhenotype[gene] = 'Indeterminate'
                    genePhenotypeCombinations.append(geneUnknownPhenotype)

        for genePhenotypeCombination in genePhenotypeCombinations:
            fdaAnnotations.append({
                'drugid': formatRxCui(rxCui),
                'drug': {
                    'name': drug
                },
                'phenotypes': genePhenotypeCombination,
                'guideline': guideline,
                'implications': geneImplications,
                'drugrecommendation': 'Might be included in implication text ' \
                    '(imported from FDA; source only states one text per guideline)'
            })

    if not areRxCuisCached():
        with open(rxCuiPath(), 'w') as rxCuiFile:
            json.dump(rxCuis, rxCuiFile, indent=4)

    with open(os.path.join(UNRESOLVED_DIR, 'FDA.json'), 'w') as unresolvedFile:
        json.dump(fdaAnnotations, unresolvedFile, indent=4)

if __name__ == '__main__':
    main()