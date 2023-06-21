import copy
import json
import os
import requests

from constants import UNRESOLVED_DIR, RESOLVED_DIR, TEMP_DIR
from constants import CacheMissError

DIPLOTYPE_ENDPOINT = 'https://api.cpicpgx.org/v1/diplotype'

def lookupkeysPath():
    return os.path.join(TEMP_DIR, 'cpic-lookupkeys.json')

def areLookupkeysCached():
    return os.path.isfile(lookupkeysPath())

def getLookupkeyMap():
    lookupkeyMap = {}
    if areLookupkeysCached():
        with open(lookupkeysPath(), 'r')  as lookupkeysFile:
            lookupkeyMap = json.load(lookupkeysFile)
    return lookupkeyMap

def getLookupkeys(lookupkeyMap, gene, phenotype):
    if areLookupkeysCached():
        if gene not in lookupkeyMap or phenotype not in lookupkeyMap[gene]:
            raise CacheMissError(f'({gene}, {phenotype})', lookupkeysPath())
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
    if not gene in lookupkeyMap:
        lookupkeyMap[gene] = {}
    lookupkeyMap[gene][phenotype] = uniqueLookupkeys
    return uniqueLookupkeys
    

lookupkeyMap = getLookupkeyMap()
for fileName in os.listdir(UNRESOLVED_DIR):
    with open(os.path.join(UNRESOLVED_DIR, fileName), 'r') as unresolvedFile:
        unresolvedContent = json.load(unresolvedFile)
        resolvedContent = []
        for unresolvedGuideline in unresolvedContent:
            # TODO: need to account for multiple genes
            for gene, phenotype in unresolvedGuideline['phenotypes'].items():
                lookupkeys = getLookupkeys(lookupkeyMap, gene, phenotype)
                if len(lookupkeys) == 0:
                    print('[WARNING] No CPIC guideline for ' \
                          f'({unresolvedGuideline["drug"]["name"]}, {gene}, ' \
                            f'{phenotype}); using FDA phenotype "{phenotype}"')
                    lookupkeys = [{ gene: phenotype }]
                for lookupkey in lookupkeys:
                    resolvedGuideline = copy.deepcopy(unresolvedGuideline)
                    resolvedGuideline['lookupkey'] = lookupkey
                    resolvedContent.append(resolvedGuideline)
        with open(os.path.join(RESOLVED_DIR, fileName), 'w') as resolvedFile:
            json.dump(resolvedContent, resolvedFile, indent=4)

if not areLookupkeysCached():
    with open(lookupkeysPath(), 'w')  as lookupkeysFile:
        json.dump(lookupkeyMap, lookupkeysFile, indent=4)