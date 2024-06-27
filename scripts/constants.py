import os

UNRESOLVED_DIR = 'unresolved-annotations'
RESOLVED_DIR = 'annotations'

TEMP_DIR = 'temp'
if not os.path.isdir(TEMP_DIR):
    os.mkdir(TEMP_DIR)

DEFAULT_ID_AND_VERSION = 1

MANUAL_PREFIX = 'manual_'
RECOMMENDATIONLESS_PREFIX = 'recommendationless_'

ANY_OTHER_PHENOTYPE = 'Any not handled in guideline'

FDA_RECOMMENDATION = 'Might be included in implication text (imported from ' \
    'FDA; source only states one text per guideline)'

class CacheMissError(Exception):
    def __init__(self, key, path):
        message = f'[ERROR] Cache miss in {path} for {key}; ' \
            'please remove cache file and try again'
        super().__init__(message)