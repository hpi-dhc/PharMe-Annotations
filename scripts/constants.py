import os

UNRESOLVED_DIR = 'unresolved-annotations'
RESOLVED_DIR = 'annotations'

TEMP_DIR = 'temp'
if not os.path.isdir(TEMP_DIR):
    os.mkdir(TEMP_DIR)

class CacheMissError(Exception):
    def __init__(self, key, path):
        message = f'[ERROR] cache miss in {path} for {key}; ' \
            'please remove cache file and try again'
        super().__init__(message)