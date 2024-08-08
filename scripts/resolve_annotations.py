import copy
import itertools
import json
import os
import requests

from constants import ALL_PHENOTYPES, FDA_RECOMMENDATION, SPECIAL_LOOKUP_KEYS, \
    SPECIAL_PHENOTYPES, UNRESOLVED_DIR, RESOLVED_DIR, TEMP_DIR, \
    DEFAULT_ID_AND_VERSION, RECOMMENDATIONLESS_PREFIX, MANUAL_PREFIX

from crawl_fda import NoRxCuiFoundError, getRxCui, formatRxCui

DIPLOTYPE_ENDPOINT = 'https://api.cpicpgx.org/v1/diplotype'

def getLookupkeys(gene, phenotype):
    if phenotype in SPECIAL_PHENOTYPES:
        return [{ gene: SPECIAL_LOOKUP_KEYS[phenotype] }]
    lookupkeysPath = os.path.join(TEMP_DIR, 'cpic-lookupkeys.json')
    lookupkeyMap = {}
    if os.path.isfile(lookupkeysPath):
        with open(lookupkeysPath, 'r')  as lookupkeysFile:
            lookupkeyMap = json.load(lookupkeysFile)
    if gene in lookupkeyMap and phenotype in lookupkeyMap[gene]:
        return lookupkeyMap[gene][phenotype] 
    params = {
        'genesymbol': f'eq.{gene}',
        'generesult': f'eq.{phenotype}',
        'select': 'lookupkey',
    }
    lookupkeys = map(
        lambda result: result['lookupkey'],
        requests.get(DIPLOTYPE_ENDPOINT, params).json())
    uniqueLookupkeys = []
    for lookupkey in lookupkeys:
        if not str(lookupkey) in map(lambda key: str(key), uniqueLookupkeys):
            uniqueLookupkeys.append(lookupkey)
    # Sort lookupkeys for robust order in resolved guidelines
    uniqueLookupkeys.sort(key = lambda item: str(item))
    if not gene in lookupkeyMap:
        lookupkeyMap[gene] = {}
    lookupkeyMap[gene][phenotype] = uniqueLookupkeys
    with open(lookupkeysPath, 'w')  as lookupkeysFile:
        json.dump(lookupkeyMap, lookupkeysFile, indent=4)
    return uniqueLookupkeys

def resolveDrug(drug):
    return {
        'id': DEFAULT_ID_AND_VERSION,
        'drugid': formatRxCui(getRxCui(drug)),
        'version': DEFAULT_ID_AND_VERSION,
        'drug': { 'name': drug },
        'lookupkey': {},
        'phenotypes': {},
        'guideline': {},
        'implications': {},
        'drugrecommendation': '',
    }

def main():
    for fileName in os.listdir(RESOLVED_DIR):
        os.remove(os.path.join(RESOLVED_DIR, fileName))
    for fileName in os.listdir(UNRESOLVED_DIR):
        with open(os.path.join(UNRESOLVED_DIR, fileName), 'r') as unresolvedFile:
            unresolvedContent = json.load(unresolvedFile)
            resolvedContent = []
            for unresolvedGuideline in unresolvedContent:
                if (fileName.startswith('additional_drugs')):
                    resolvedContent.append(resolveDrug(unresolvedGuideline))
                    continue
                unresolvedLookupkeys = {}
                if not 'id' in unresolvedGuideline:
                    unresolvedGuideline['id'] = DEFAULT_ID_AND_VERSION
                if not 'version' in unresolvedGuideline:
                    unresolvedGuideline['version'] = DEFAULT_ID_AND_VERSION
                if not 'drugid' in unresolvedGuideline:
                    try:
                        rxCui = getRxCui(unresolvedGuideline['drug']['name'])
                    except NoRxCuiFoundError as e:
                        print(f'{str(e)}; skipping guideline')
                        continue
                    else:
                        unresolvedGuideline['drugid'] = formatRxCui(rxCui)
                if (fileName.startswith(RECOMMENDATIONLESS_PREFIX)):
                    if not 'phenotypes' in unresolvedGuideline:
                        unresolvedGuideline['phenotypes'] = {}
                    unresolvedGuideline['implications'] = {}                        
                    genes = unresolvedGuideline['genes'] \
                        if 'genes' in unresolvedGuideline \
                        else unresolvedGuideline['phenotypes'].keys()
                    for gene in genes:
                        if not gene in unresolvedGuideline['phenotypes']:
                            unresolvedGuideline['phenotypes'][gene] = ALL_PHENOTYPES
                        unresolvedGuideline['implications'][gene] = \
                            'No implication'
                    unresolvedGuideline['drugrecommendation'] = 'No recommendation'
                    if 'genes' in unresolvedGuideline:
                        del unresolvedGuideline['genes']
                if 'FDA' in fileName:
                    unresolvedGuideline['drugrecommendation'] = FDA_RECOMMENDATION
                for gene, phenotype in unresolvedGuideline['phenotypes'].items():
                    lookupkeys = getLookupkeys(gene, phenotype)
                    if len(lookupkeys) == 0:
                        print('[WARNING] No CPIC or special lookup for ' \
                            f'({unresolvedGuideline["drug"]["name"]}, {gene}, ' \
                                f'{phenotype}); using phenotype "{phenotype}"')
                        lookupkeys = [{gene: phenotype}]
                    unresolvedLookupkeys[gene] = lookupkeys
                lookupkeyCombinations = list(itertools.product(*unresolvedLookupkeys.values()))
                for lookupkeyCombination in lookupkeyCombinations:
                    lookupkey = {}
                    for lookupitem in lookupkeyCombination:
                        lookupkey = {**lookupkey, **lookupitem}
                    resolvedGuideline = copy.deepcopy(unresolvedGuideline)
                    resolvedGuideline['lookupkey'] = lookupkey
                    resolvedContent.append(resolvedGuideline)
            resolvedFileName = fileName
            if fileName.startswith(RECOMMENDATIONLESS_PREFIX):
                resolvedFileName = fileName.removeprefix(RECOMMENDATIONLESS_PREFIX)
            if fileName.startswith(MANUAL_PREFIX):
                resolvedFileName = fileName.removeprefix(MANUAL_PREFIX)
            resolvedFilePath = os.path.join(RESOLVED_DIR, resolvedFileName)
            if os.path.exists(resolvedFilePath):
                with open(resolvedFilePath, 'r') as resolvedFile:
                    presentResolvedContent = json.load(resolvedFile)
                    resolvedContent.extend(presentResolvedContent)
            with open(resolvedFilePath, 'w') as resolvedFile:
                json.dump(resolvedContent, resolvedFile, indent=4)        

if __name__ == '__main__':
    main()