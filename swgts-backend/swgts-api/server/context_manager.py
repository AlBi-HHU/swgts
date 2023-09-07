import logging
import os
from os import path
from typing import Tuple, Optional, Any
from uuid import UUID, uuid4
from redis import Redis

lo = logging.getLogger('Context Manager')
lo.setLevel('DEBUG')

redis_server: Optional[Redis] = None
CONFIG: Optional[dict[str, Any]] = None


def setup_state_server(config: dict[str, Any]):
    global CONFIG, redis_server
    CONFIG = config
    redis_server = Redis(host=config.get('REDIS_SERVER'))

def redis_ping() -> bool:
    return redis_server.ping()


def context_exists(context: UUID) -> bool:
    return redis_server.exists(f'context:{context}:pair_count') == 1


def get_pair_count(context: UUID) -> int:
    return int(redis_server.get(f'context:{context}:pair_count'))


def get_pending_bytes_count(context: UUID) -> int:
    return int(redis_server.get(f'context:{context}:pending_bytes'))

def get_processed_read_count(context: UUID) -> int:
    return int(redis_server.get(f'context:{context}:processed_reads'))


def create_context(filenames: list[str]) -> UUID:
    new_context_id = uuid4()
    pipeline = redis_server.pipeline()

    pipeline.setex(f'context:{new_context_id}:pending_bytes', CONFIG['CONTEXT_TIMEOUT'], 0)
    pipeline.setex(f'context:{new_context_id}:pair_count', CONFIG['CONTEXT_TIMEOUT'], len(filenames))
    pipeline.setex(f'context:{new_context_id}:processed_reads', CONFIG['CONTEXT_TIMEOUT'], 0)

    for pair_index, filename in enumerate(filenames):
        #We save only the basename to avoid creating of directories etc.
        pipeline.setex(f'context:{new_context_id}:pair:{pair_index}:filename', CONFIG['CONTEXT_TIMEOUT'], path.basename(filename))

    pipeline.execute()
    return new_context_id

def change_pending_bytes_count(context: UUID, diff: int) -> int:
    now_pending = redis_server.incrby(f'context:{context}:pending_bytes', diff)
    redis_server.expire(f'context:{context}:pending_bytes', CONFIG['CONTEXT_TIMEOUT'])
    return int(now_pending)

def enqueue_chunks(chunks : list[list[list[str]]], context_id:UUID, effective_cumulated_chunk_size:int):
    job_id = uuid4()
    #TODO: Implement cleanup strategy for orphaned jobs
    transaction = redis_server.pipeline(transaction=True)
    transaction.lpush(f'work:queue',f"{job_id}") #Implicit conversion to string
    transaction.lpush(f'work:{job_id}',f"{context_id}") #Implicit conversion to string
    transaction.lpush(f'work:{job_id}',effective_cumulated_chunk_size)
    read_count : int = len(chunks)
    pair_count : int = len(chunks[0])
    transaction.lpush(f'work:{job_id}', read_count)  # Number of paired reads
    transaction.lpush(f'work:{job_id}', pair_count)  # Pair Count
    for read_idx, reads in enumerate(chunks):
        for pair_idx, read in enumerate(chunks[read_idx]):
            for line in chunks[read_idx][pair_idx]:
                transaction.lpush(f'work:{job_id}',line)

    transaction.execute()

def get_queue_speed() -> float:
    last_speed_measurements = [float(x.decode()) for x in redis_server.lrange(f'queue:speed',0,-1)]
    if len(last_speed_measurements) == 0:
        #edge case
        return 0
    return sum(last_speed_measurements) / len(last_speed_measurements)

def close_context(context: UUID, hands_off: bool) -> Tuple[int, list[str]]:
    # FIXME sanity check redis response
    # FIXME redis-server-side CONTEXT_TIMEOUT may happen while writing

    context_output_folder = path.join(CONFIG['UPLOAD_DIRECTORY'], str(context))
    if not hands_off:
        os.makedirs(context_output_folder)

    pair_count = int(redis_server.get(f'context:{context}:pair_count'))
    redis_server.delete(f'context:{context}:pair_count')

    saved_reads_ids = list(read.split(b'\n', 1)[0].decode('ascii') for read in redis_server.smembers(f'context:{context}:pair:{0}:reads'))

    for pair_index in range(pair_count):
        #redis_server.persist(f'context:{context}:pair:{pair_index}:filename')
        #redis_server.persist(f'context:{context}:pair:{pair_index}:reads')

        output_filename = redis_server.get(f'context:{context}:pair:{pair_index}:filename').decode('utf-8')
        redis_server.delete(f'context:{context}:pair:{pair_index}:filename')

        if not hands_off:
            with open(path.join(context_output_folder, output_filename), 'wb') as handle:
                handle.write(b'\n'.join(redis_server.smembers(f'context:{context}:pair:{pair_index}:reads')))

        redis_server.delete(f'context:{context}:pair:{pair_index}:reads')

    processed_reads = int(redis_server.get(f'context:{context}:processed_reads'))
    redis_server.delete(f'context:{context}:processed_reads')
    redis_server.delete(f'context:{context}:pending_bytes')

    return processed_reads, saved_reads_ids


def get_saved_read_count(context: UUID) -> int:
    # We assume that this context has at least 1 file.
    return int(redis_server.scard(f'context:{context}:pair:0:reads'))

