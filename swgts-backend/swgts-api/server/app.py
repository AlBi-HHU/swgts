# coding=utf-8
import sys
from time import time
from typing import Union

from flask import Flask, request, make_response

from .context_manager import *
from .version import VERSION_INFORMATION

app = Flask(__name__)

@app.route('/server-status', methods=['GET'])
def server_status() -> dict[str, Union[str, float]]:
    """Returns information about the server. Unfortunately, proper version discovery only works if the package is
    installed, which is true for the deployment Dockerfile. Reading the git revision would require additional
    dependencies. """
    answer: dict[str, Union[str, float]] = VERSION_INFORMATION.copy()
    answer['uptime'] = time() - SERVER_LAUNCH_TIME
    answer['maximum pending bytes'] = app.config['MAXIMUM_PENDING_BYTES']
    return make_response(answer, 200)


@app.route('/context/create', methods=['POST'])
def context_create() -> dict[str, UUID]:
    json_body: dict[str, Any]
    try:
        json_body = request.get_json()
        if 'filenames' not in json_body:
            return make_response({'message': 'filenames missing in request.'}, 400)
        if not isinstance(json_body['filenames'], list):
            return make_response({'message': 'filenames is not a list.'}, 400)
    except TypeError:
        return make_response({'message': 'expected json body.'}, 400)

    context = create_context(filenames=json_body['filenames'])
    if context is None:
        app.logger.error('Could not create context.')

    return {'context': context}


@app.route('/context/<uuid:context_id>/close', methods=['POST']) #TODO: Avoid race condition (close before last reads)
def post_close_context(context_id: UUID) -> dict[str, Union[int, str, list[str]]]:

    if not context_exists(context_id):
        app.logger.warn(f'Tried to close non-existent context {context_id}.')
        return make_response({'message': 'No such context.'}, 404)

    # We test if the context still has pending bytes and only delete it if no more bytes are pending (everything is filtered)
    pending_bytes : int = get_pending_bytes_count(context_id)
    if pending_bytes != 0:
        return make_response({
            'Retry-After': pending_bytes*get_queue_speed(),
            'message' : 'There are still reads pending, try again later!'
        }, 503)

    result = close_context(context_id,app.config['HANDS_OFF'])
    if result is None:
        return make_response({'message': 'Could not close context.'}, 500)
    else:
        app.logger.info(f'Closed context {context_id}, saved {len(result[1])} of {result[0]}.')
        return make_response({'saved': result[1], 'total': result[0]}, 200)

@app.route('/context/<uuid:context_id>/reads', methods=['POST'])
def post_context_reads(context_id: UUID) -> dict[str, Union[int, str]]:
    if not context_exists(context_id):
        return make_response({'message': 'No such context.'}, 404)

    chunks: list[list[list[str]]]
    try:
        chunks = request.get_json()
    except TypeError:
        return make_response({'message': 'Expected json body.'}, 400)
    except OSError:
        return make_response({'message': 'The connection was interrupted.'}, 400)

    if not isinstance(chunks, list):
        return make_response({'message': '"chunks" is not a list.'}, 400)

    effective_cumulated_chunk_size: int = 0
    pair_count: int = get_pair_count(context_id)  # We expect as much reads to be paired as we have open file streams. (Support for strobe reads in theory)
    for chunk in chunks:
        if not isinstance(chunk, list):
            return make_response({'message': 'There is a chunk which is not a list.'}, 400)
        if len(chunk) != pair_count:
            return make_response({'message': f'I thought you wanted to submit {pair_count}-paired reads, '
                                             f'but here I got a pair that had {len(chunk)} reads.'}, 400)
        for read in chunk:
            if not isinstance(read, list):
                return make_response({'message': 'There is a read which is not a list.'}, 400)
            if len(read) != 4:
                return make_response({'message': 'There is a read with a length != 4.'}, 400)
            # Here would be the place to test if a read looks suspicious TODO
            # Only count the length of the actual sequence
            effective_cumulated_chunk_size += len(read[1])

    current_pending : int  = get_pending_bytes_count(context_id)
    excess : int  = current_pending + effective_cumulated_chunk_size - app.config['MAXIMUM_PENDING_BYTES']

    if excess > 0:
        resp =  make_response(
            {'message': f'You sent too much data.', 'pending bytes': current_pending, 'processed reads': get_processed_read_count(context_id)}, 422)
        #Fetch current average processing
        resp.headers['Retry-After'] = excess*get_queue_speed()
        return resp

    #Execution from here on means accepting the chunk and processing the reads
    #Adjust pending bytes stat in redis
    current_pending = change_pending_bytes_count(context_id, effective_cumulated_chunk_size)

    #Queue job
    enqueue_chunks(chunks, context_id, effective_cumulated_chunk_size)

    return make_response({
        'processed reads': get_processed_read_count(context_id),
        'pending bytes': current_pending},
                         200)


app.config.from_pyfile('config.py')
if os.path.exists(app.config['CONFIG_FILE']):
    print('found additional config file, overwriting defaults ...')
    app.config.from_pyfile(app.config['CONFIG_FILE'])
logging.basicConfig(filename=app.config['LOG_FILE'], level='INFO',
                    format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
logging.getLogger().addHandler(logging.StreamHandler())

for k in app.config:
    app.logger.info(f'Configuration {k} -> {app.config[k]}')


app.logger.info('Connecting to stateful backend.')
setup_state_server(app.config)
if not redis_ping():
    app.logger.fatal('Could not connect to stateful backend. Goodbye.')
    sys.exit(1)


SERVER_LAUNCH_TIME = time()
app.logger.info('Server launched.')
