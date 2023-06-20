import os

UNRESOLVED_DIR = 'unresolved-annotations'
RESOLVED_DIR = 'annotations'

TEMP_DIR = 'temp'
if not os.path.isdir(TEMP_DIR):
    os.mkdir(TEMP_DIR)