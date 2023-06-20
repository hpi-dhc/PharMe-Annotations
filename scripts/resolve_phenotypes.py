# `https://api.cpicpgx.org/v1/diplotype?genesymbol=eq.<GENE_SYMBOL>&generesult=eq.<GENE_RESULT>&select=lookupkey,generesult`
# by replacing `GENE_SYMBOL` and `GENE_RESULT` with the desired
# phenotype information, e.g. `CYP2D6` and `Poor Metabolizer` respectively.

import copy
import json
import os
import requests

from constants import UNRESOLVED_DIR, RESOLVED_DIR


DIPLOTYPE_ENDPOINT = 'https://api.cpicpgx.org/v1/diplotype'

for fileName in os.listdir(UNRESOLVED_DIR):
    with open(os.path.join(UNRESOLVED_DIR, fileName), 'r') as unresolvedFile:
        unresolvedContent = json.load(unresolvedFile)
        resolvedContent = []
        for unresolvedGuideline in unresolvedContent:
            for gene, phenotype in unresolvedGuideline['phenotypes'].items():
                params = {
                    'genesymbol': f'eq.{gene}',
                    'generesult': f'eq.{phenotype}',
                    'select': 'lookupkey',
                }
                lookupkeys = map(
                    lambda result: result['lookupkey'],
                    requests.get(DIPLOTYPE_ENDPOINT, params).json())
                resolvedLookupkeys = []
                for lookupkey in lookupkeys:
                    if not str(lookupkey) in resolvedLookupkeys:
                        resolvedGuideline = copy.deepcopy(unresolvedGuideline)
                        resolvedGuideline['lookupkey'] = lookupkey
                        resolvedContent.append(resolvedGuideline)
                        resolvedLookupkeys.append(str(lookupkey))
        with open(os.path.join(RESOLVED_DIR, fileName), 'w') as resolvedFile:
            json.dump(resolvedContent, resolvedFile, indent=4)