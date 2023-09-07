# coding=utf-8
import logging
import sys
import os
from time import time, sleep
from uuid import UUID

from filter import init_filter, is_read_legal
from redis import Redis
from multiprocessing import Pool, Event, Manager
from config import *
import signal

if os.path.exists(CONFIG_FILE):
    print(f'Found config file: {CONFIG_FILE}, overwriting defaults!')
    with open (CONFIG_FILE,'r') as add_cfg:
        exec(add_cfg.read())
else:
    print('Using defaults, no config file specified')


logging.basicConfig(filename=LOG_FILE, level='INFO',
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')

redis_server = Redis(host=REDIS_SERVER)

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())

logger.info('Setting up server.')

logger.info('Calling init_filter')

init_filter(FILTER_MODE, MAPPING_PRESET, MINIMAP2_REFERENCE_DATABASE, MINIMAP2_POSITIVE_CONTIG, MINIMAP2_QUALITY_THRESHOLD)

if not redis_server.ping():
    logger.fatal('Could not connect to stateful backend. Goodbye.')
    sys.exit(1)

logger.info('Setting up queue and worker')

def mark_for_saving(context: UUID, reads: list[list[list[str]]], how_many_were_processed: int) -> None:
    pipeline = redis_server.pipeline()

    for pair in reads:
        for pair_index, read in enumerate(pair):
            pipeline.sadd(f'context:{context}:pair:{pair_index}:reads', '\n'.join(read))

    pair_count_raw = redis_server.get(f'context:{context}:pair_count')

    if pair_count_raw  == None:
        logger.warning(f"Attempting to process reads for context {context} but no pair_count is stored, maybe the context is orphaned")
        return

    #TODO: Check if expiration shouldn't be set in close_context
    for pair_index in range(int(pair_count_raw)):
        pipeline.expire(f'context:{context}:pair:{pair_index}:reads', CONTEXT_TIMEOUT)
        pipeline.expire(f'context:{context}:pair:{pair_index}:filename', CONTEXT_TIMEOUT)

    pipeline.incrby(f'context:{context}:processed_reads', how_many_were_processed)
    pipeline.expire(f'context:{context}:processed_reads', CONTEXT_TIMEOUT)
    pipeline.expire(f'context:{context}:pair_count', CONTEXT_TIMEOUT)
    logger.info('Will now execute')
    pipeline.execute()

def change_pending_bytes_count(context: UUID, diff: int) -> int:
    now_pending = redis_server.incrby(f'context:{context}:pending_bytes', diff)
    redis_server.expire(f'context:{context}:pending_bytes', CONTEXT_TIMEOUT)
    return int(now_pending)

def spawn_worker(worker_id: int, is_shutting_down : Event):
    logger.info(f'Worker spawned with id {worker_id}')
    while not is_shutting_down.is_set():
        #Fetch a job
        work_assignment = redis_server.brpop(f'work:queue',60)
        start_time = time()
        if work_assignment is None:
            logger.info(f'Worker {worker_id} reporting: Nothing to be done here, boring ...')
            continue
        else:
            # Redis blpop can be called on multiple lists and thus returns a tuple, first value is the list
            pending_job_id = work_assignment[1].decode()
            context_id = redis_server.brpop(f'work:{pending_job_id}')[1].decode()
            #TODO: Extract correct type instead of casting to int
            effective_cumulative_chunk_size = int(redis_server.brpop(f'work:{pending_job_id}')[1].decode())

            read_count = int(redis_server.brpop(f'work:{pending_job_id}')[1].decode())
            pair_count = int(redis_server.brpop(f'work:{pending_job_id}')[1].decode())

            logger.info(f'Worker {worker_id} reporting: I am working on a chunk for context {context_id} (ECCS: {effective_cumulative_chunk_size}) with {read_count} reads (in pairs of {pair_count})!')

            #reconstruct chunk
            chunk = []
            for read_idx in range(read_count):
                reads = []
                for pair_idx in range(pair_count):
                    l1 = redis_server.brpop(f'work:{pending_job_id}')[1].decode()
                    l2 = redis_server.brpop(f'work:{pending_job_id}')[1].decode()
                    l3 = redis_server.brpop(f'work:{pending_job_id}')[1].decode()
                    l4 = redis_server.brpop(f'work:{pending_job_id}')[1].decode()
                    reads.append([l1, l2, l3, l4])
                chunk.append(reads)
            #logger.info(f'Worker {worker_id} reporting: I reconstructed the reads, time to filter them!')
            to_save: list[list[list[str]]] = []
            for corresponding_reads in chunk:
                if is_read_legal(corresponding_reads):
                    to_save.append(corresponding_reads)
            logger.info(f'Worker {worker_id} reporting: I filtered {len(chunk)-len(to_save)} of {len(chunk)}, time to mark the reads for saving')
            mark_for_saving(context_id, to_save, len(chunk))
            #logger.info(f'Worker {worker_id} reporting: I will now update the pending byte count')
            change_pending_bytes_count(context_id, -effective_cumulative_chunk_size)
            logger.info(f'Worker {worker_id} reporting: Done!')
        end_time = time()
        redis_server.lpush(f'queue:speed',(end_time-start_time)/effective_cumulative_chunk_size)
        redis_server.ltrim(f'queue:speed',0,9)
    logger.info(f'Worker {worker_id} shutting down.')

with Manager() as manager:

    IS_SHUTTING_DOWN: Event = manager.Event()
    def signal_handler(sig, frame):
        logger.info('Got SIGINT, trying to shut down.')
        IS_SHUTTING_DOWN.set()

    signal.signal(signal.SIGINT, signal_handler)
    logger.info('Press Ctrl+C to safely shutdown')

    pool: Pool = Pool(processes = WORKER_THREADS)
    SERVER_LAUNCH_TIME = time()
    logger.info('Server launched.')
    dummy_result = pool.starmap_async(spawn_worker, ((x, IS_SHUTTING_DOWN) for x in range(WORKER_THREADS)))
    logger.info('Worker threads launched!')
    while not IS_SHUTTING_DOWN.is_set():
        #logger.info('I am still alive')
        # Main thread may not block since this would prevent signal handler from working
        sleep(10)
    logger.info('Closing worker pool')
    pool.close()
    logger.info('Joining worker pool')
    pool.join()
