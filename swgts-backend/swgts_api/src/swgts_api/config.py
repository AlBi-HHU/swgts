# coding=utf-8
from os import getcwd, path

INPUT_DIRECTORY: str = path.join(getcwd(), 'input')

# The parent directory for everything that the server will write to
OUTPUT_DIRECTORY: str = path.join(getcwd(), 'output')

# The secondary configuration file to load to override the defaults set in here
CONFIG_FILE: str = path.join(INPUT_DIRECTORY, 'config_api.py')

# The log file
LOG_FILE: str = path.join(OUTPUT_DIRECTORY, 'server.log')
# The per-context directories are created under the UPLOAD_DIRECTORY
UPLOAD_DIRECTORY: str = path.join(OUTPUT_DIRECTORY, 'uploads')
# In hands-off mode filtered read ids are returned but no reads are saved to disk
HANDS_OFF : bool = False

# The count of base pairs aka bytes per context that are allowed to be in RAM at a time
MAXIMUM_PENDING_BYTES: int = 300000
# How long after the last contact should a context be deleted?
CONTEXT_TIMEOUT: int = 60

#docker name or hostname of the redis service
REDIS_SERVER: str = 'redis'