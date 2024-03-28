# coding=utf-8
from os import getcwd, path

# The log file
LOG_FILE: str = 'server.log'

INPUT_DIRECTORY: str = path.join(getcwd(), 'input')
# The secondary configuration file to load to override the defaults set in here
CONFIG_FILE: str = path.join(INPUT_DIRECTORY, 'config_filter.py')

#Can be either COMBINED or NEGATIVE, NONE is a dummy that simply accepts all reads
#COMBINED: Uses a database where one reference is labeled as the target (MINIMAP2_POSITIVE_CONTIG)
#NEGATIVE: Only host database is provided and all hits are discarded
FILTER_MODE: str = 'COMBINED'
MINIMAP2_REFERENCE_DATABASE: str = path.join(INPUT_DIRECTORY, 'databases', 'combinedHumanCovid.mmi')
# The contig identifier (needs to be contained in the mm2 database) that indicates a positive (KEEP) result for the
# read if it is the primary alignment match
MINIMAP2_POSITIVE_CONTIG: str = 'hCoV-19/Wuhan/WIV04/2019|EPI_ISL_402124'
# Minimap2 Mapping Preset
MAPPING_PRESET: str = 'map-ont'
#Quality threshold, only used in negative filtering mode
MINIMAP2_QUALITY_THRESHOLD : int = 20

#docker name or hostname of the redis service
REDIS_SERVER: str = 'redis'

#Number of concurrent worker threads used for filtering
WORKER_THREADS: int = 8