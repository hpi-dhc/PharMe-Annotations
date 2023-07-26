import copy
import itertools
import json
import os
import requests

from constants import UNRESOLVED_DIR, RESOLVED_DIR, TEMP_DIR
from constants import CacheMissError

from crawl_fda import getRxCuiForDrug, formatRxCui

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

def resolveDrug(drug):
    return {
        'id': 1,
        'drugid': formatRxCui(getRxCuiForDrug(drug)),
        'version': 1,
        'drug': { 'name': drug },
        'lookupkey': { 'foo': 'bar' },
        'phenotypes': { 'foo': 'bar' },
        'guideline': { 'name': 'foo', 'url': 'foo.bar' },
        'implications': { 'foo': 'bar' },
        'drugrecommendation': 'foobar',
    }

lookupkeyMap = getLookupkeyMap()
for fileName in os.listdir(UNRESOLVED_DIR):
    with open(os.path.join(UNRESOLVED_DIR, fileName), 'r') as unresolvedFile:
        unresolvedContent = json.load(unresolvedFile)
        resolvedContent = []
        for unresolvedGuideline in unresolvedContent:
            if (fileName.startswith('additional_drugs')):
                resolvedContent.append(resolveDrug(unresolvedGuideline))
                continue
            unresolvedLookupkeys = {}
            for gene, phenotype in unresolvedGuideline['phenotypes'].items():
                lookupkeys = getLookupkeys(lookupkeyMap, gene, phenotype)
                if len(lookupkeys) == 0:
                    print('[WARNING] No CPIC guideline for ' \
                          f'({unresolvedGuideline["drug"]["name"]}, {gene}, ' \
                            f'{phenotype}); using FDA phenotype "{phenotype}"')
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
        with open(os.path.join(RESOLVED_DIR, fileName), 'w') as resolvedFile:
            json.dump(resolvedContent, resolvedFile, indent=4)

if not areLookupkeysCached():
    with open(lookupkeysPath(), 'w')  as lookupkeysFile:
        json.dump(lookupkeyMap, lookupkeysFile, indent=4)