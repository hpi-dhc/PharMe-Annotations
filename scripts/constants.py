import os

IGNORE_GENES_NOT_IN_CPIC_LOOKUPS = True

UNRESOLVED_DIR = 'unresolved-annotations'
RESOLVED_DIR = 'annotations'

TEMP_DIR = 'temp'
if not os.path.isdir(TEMP_DIR):
    os.mkdir(TEMP_DIR)

DEFAULT_ID_AND_VERSION = 1

MANUAL_PREFIX = 'manual_'
RECOMMENDATIONLESS_PREFIX = 'recommendationless_'

ANY_OTHER_PHENOTYPE = 'Any not handled in guideline'
ALL_PHENOTYPES = 'All'
SPECIAL_PHENOTYPES = [ ANY_OTHER_PHENOTYPE, ALL_PHENOTYPES ]
SPECIAL_LOOKUP_KEYS = {
    ALL_PHENOTYPES: '*',
    ANY_OTHER_PHENOTYPE: '~',
}

FDA_EXCUSE = '(imported from FDA, source only states one text per guideline)'
def fdaFurtherGenesImplication(genes):
    return f'Might be included in {genes[0]} implication {FDA_EXCUSE}; ' \
        f'joint implication does not apply for this gene in case the ' \
        f'phenotype is "{ANY_OTHER_PHENOTYPE}"'
FDA_RECOMMENDATION = f'Might be included in implication text {FDA_EXCUSE}'
FDA_STANDARD_PROCEDURE = 'Standard procedure'
