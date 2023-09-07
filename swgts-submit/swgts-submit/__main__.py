import gzip
import mimetypes
from argparse import ArgumentParser
from json import JSONDecodeError
from time import sleep
from typing import Optional, Union, AnyStr, List, Tuple, Dict, TextIO, Generator
from uuid import UUID

import os
import httpx
from tqdm import tqdm

#TODO: Differentiate between file and stream and show progress bar accordingly for files (count reads prior to parsing and set total accordingly)

class Read:
    def __init__(self, lines: List[AnyStr]) -> None:
        self.barcode: AnyStr = lines[0].rstrip('\n')
        self.sequence: AnyStr = lines[1].rstrip('\n')
        self.plus: AnyStr = lines[2].rstrip('\n')
        self.quality: AnyStr = lines[3].rstrip('\n')

    def __iter__(self) -> None:
        yield self.barcode
        yield self.sequence
        yield self.plus
        yield self.quality

    def bp_count(self) -> int:
        return len(self.sequence)

    def __str__(self) -> str:
        return f'{self.barcode}\n{self.sequence}\n{self.plus}\n{self.quality}\n'

def create_context(client: httpx.Client, filenames: List[str]) -> Optional[UUID]:
    result = client.post('/context/create', json={'filenames': filenames})
    if result.is_error:
        print('Could not create context.')
        return None
    else:
        payload = result.json()
        if 'context' not in payload:
            print('The server sent a malformed answer.')
        else:
            new_context: UUID
            try:
                new_context = UUID(payload['context'])
            except ValueError:
                print('The server sent a malformed response, the UUID is broken.')
                return None
            return new_context


def query_server_status(client: httpx.Client) -> Dict[str, Union[str, float, int]]:
    result = client.get('/server-status')
    if result.is_error:
        raise Exception("Couldn't retrieve server status. Is it even running?")
    else:
        return result.json()

def read_reads_from_file(filepath: str) -> Generator[Read, None, None]:
    guessed_mimetype : Tuple[str,str] = mimetypes.guess_type(filepath)
    file = gzip.open(filepath,'rt') if guessed_mimetype[1] == 'gzip' else open(filepath,'r')
    buffer = []
    while True:
        line = next(file, None)
        if line is not None:
            buffer.append(line)
        else:
            break
        if len(buffer) == 4:
            yield Read(buffer)
            buffer = []
    file.close()


def read_reads_from_files(all_files: List[TextIO]) -> Tuple[Generator[Read, None, None], ...]:

    '''
    # This is medium naive, and consumes tons of RAM.
    all_lines = list(map(lambda f: f.read().splitlines(), all_files))
    all_reads = [[Read(all_lines[file][i:i + 4]) for i in range(0, len(all_lines[file]), 4)] for file in
                 range(len(all_lines))]
    return list(zip(*all_reads))
    '''

    # This is stream-based
    reads_per_file = map(lambda f : read_reads_from_file(f), all_files)
    return zip(*reads_per_file)


def split_n_bp_worth_of_reads(reads: List[Tuple[Read]], max_bp: int, progress_bar: tqdm) -> Generator[List[Tuple[Read]], None, None]:
    """
    Split the reads list into chunk so that they never hit the sequence size limit.
    The smallest chunk will always be at least a single read.

    :param reads: The list of the reads to chomp.
    :param max_bp: The maximum bps in the reads per chunk.
    """
    result: List[List[Tuple[Read]]] = []

    current_buffer_size: int = 0
    current_buffer: List[Tuple[Read]] = []

    for corresponding_reads in reads:
        this_reads_length: int = sum(map(lambda r: r.bp_count(), corresponding_reads))

        if this_reads_length > max_bp:
            raise Exception(f'Your file contains a single read that is larger ({this_reads_length}) than the allowed buffer size, this file can thus not be uploaded!')

        if this_reads_length + current_buffer_size >= max_bp:
            if len(current_buffer) > 0:
                # The current buffer can be empty here if the length of the first corresponding_reads already
                # exceeds our size hint. This can happen if you have
                # a) a ridiculous low maximum bp count

                progress_bar.total += 1
                progress_bar.refresh()
                yield current_buffer
            current_buffer = []
            current_buffer_size = 0

        current_buffer.append(corresponding_reads)
        current_buffer_size += this_reads_length

    if len(current_buffer) > 0:
        # If we have something left in the buffer (we will!), we need to also add it to the result.
        progress_bar.total += 1
        progress_bar.refresh()
        yield current_buffer


def close_context(client: httpx.Client, context: UUID, verbose: bool, progress_bar : tqdm) -> Optional[Tuple[List[str], int]]:
    """
    Request a context close on the server.
    :param client: Our main http client for signalization.
    :param context: The context to close.
    :return: The total statistics we get from the server.
    """

    while (True):
        result = client.post(f'/context/{context}/close')
        payload = None
        try:
            payload = result.json()
        except:
            pass

        if result.status_code == httpx.codes.SERVICE_UNAVAILABLE: #Reads are still being processed
            timeout : float = float(payload['Retry-After'])
            if verbose:
                progress_bar.write(f'Reads are still being processed, server asks us to check back in {timeout} seconds')
            sleep(timeout)
            continue

        if result.status_code != httpx.codes.OK:
            progress_bar.write(f'Could not close context {context}. Tell the server admin. Your upload is most likely gone.')
            return None

        if payload is None:
            progress_bar.write(f'The server did not send any payload in the response. or the payload could not be parsed.')
            return None

        return payload['saved'], payload['total']


def submit_chunks(client: httpx.Client, context: UUID, reads: List[Tuple[Read]],
                  size_hint: int, retries: int, verbose: bool, progress_bar: tqdm) -> bool:
    """
    Work on a chunk of reads.
    Split a chunk of reads into smaller chunks, and send them sequentially. We do this with our own http client class
    instance.
    :param progress_bar: The progress bar to use to print the status.
    :param retries: How many retries to do if one chunk failed.
    :param client: The httpx-Client to use.
    :param context: The context we should submit it to.
    :param reads: The reads to submit. 1-tuples for single file submission, 2-tuples for paired-end.
    :param size_hint: The maximum read sequence length.
    :return False if cancelled, else True
    """

    def update_progress_bar(progress_bar: tqdm, reads: int):
        progress_bar.n = reads
        progress_bar.last_n = reads
        progress_bar.update()



    rejections: int = 0
    chunks_to_send: Generator[List[Tuple[Read]], None, None] = split_n_bp_worth_of_reads(reads, size_hint, progress_bar)

    # progress_bar.write(f'Hi! This is a worker. I will take care of {len(reads)} reads. To make the server happy, '
    #                    f'I split them into {len(chunks_to_send)} transmissions.')

    for chunk in chunks_to_send:
        chunk_transmitted = False
        while not chunk_transmitted:
            if retries != -1 and rejections > retries: #Only handle if retries is set
                progress_bar.write(f'Too many retries ({rejections}).')
                return False

            try:
                #print(f'Sending chunk of length {len(chunk)}')
                response = client.post(f'/context/{context}/reads',
                                       json=[[list(read) for read in corresponding_reads]
                                             for corresponding_reads in chunk])
            except Exception as e:
                progress_bar.write(f'We had a failure, now at {rejections}. {e}')
                return False

            try:
                response_json = response.json()
            except JSONDecodeError:
                progress_bar.write(
                    f"The server did not return a proper json (Code: {response.status_code}). We can't really handle this.")
                return False

            if response.status_code == httpx.codes.NOT_FOUND:
                progress_bar.write(f'The server return 404 for the context {context}.')
                return False

            elif response.status_code == httpx.codes.BAD_REQUEST:
                progress_bar.write(f'We did something wrong.\n'
                                   f'{response.json()["message"]}')
                return False
            #Orderly timeout
            elif response.status_code == httpx.codes.UNPROCESSABLE_ENTITY:
                rejections += 1
                if verbose:
                    progress_bar.write(f"Received timeout: Server wants retry after {float(response.headers['Retry-After'])} s")
                    update_progress_bar(progress_bar, int(response.json()['processed reads']))
                if 'Retry-After' not in response.headers:
                    progress_bar.write(f"We received an orderly timeout without Retry-After headers, this should not happen!")
                    return False
                sleep(float(response.headers['Retry-After']))
                continue
            elif response.is_error:
                progress_bar.write(f"We received an error ({response.status_code}), let's treat it as a simple failure.")
                return False
            else:
                update_progress_bar(progress_bar, int(response.json()['processed reads']))
                chunk_transmitted = True

    progress_bar.write(f'Transmission had {rejections} retries due to exceeding the server buffer')

    return True


def get_argument_parser() -> ArgumentParser:
    parser = ArgumentParser(description='Upload fastq data to the filtering server.')
    parser.add_argument('--server', type=str, default='https://127.0.0.1/api',
                        help='The server base URL.')
    parser.add_argument('--paired', action='store_true', help='Paired end mode.')
    parser.add_argument('--count', type=int, help='Override the maximum amount the server gets from us at a time.')
    parser.add_argument('--retries', type=int, default=-1,
                        help='How many times to retry a submission that soft-failed. If -1 no limit is set.')
    parser.add_argument('files', type=str, help='The fastq files to submit.', nargs='+')
    parser.add_argument('--outfolder', type=str, help='The folder to save the filtered reads in')
    parser.add_argument('--verbose', action='store_true', help='Output detailed information about the transaction')
    return parser


def get_maximum_pending_bytes(client: httpx.Client) -> int:
    try:
        server_info = query_server_status(client)
    except Exception as e:
        print('Could not query server status. Is the server running?')
        raise e

    return server_info['maximum pending bytes']


def main() -> None:
    arguments = get_argument_parser().parse_args()

    if arguments.paired:
        if len(arguments.files) == 1:
            print(f'You chose paired mode, but you provided only one file. Did you mean to just upload one file?')
        elif len(arguments.files) != 2:
            print(f'Paired mode with {len(arguments.files)} seems suspicious. Was this intentional? Proceeding anyway.')
    else:
        if len(arguments.files) != 1:
            print(f'You provided multiple files, but did not enable paired mode. If you want to upload multiple '
                  f'non-paired-end files, please upload them separately. Continuing with only the first one.')
            arguments.files = [arguments.files[0]]

    filenames: List[str] = list(map(lambda x: x, arguments.files))
    with httpx.Client(base_url=arguments.server, verify=False, http2=True) as client:

        print(f'Submitting {", ".join(filenames)}{" in paired-end mode" if len(filenames) > 1 else ""}')

        context = create_context(client, filenames)
        mpb: int = get_maximum_pending_bytes(client)

        if arguments.count is None:
            arguments.count = mpb // 10
        print(f'The server wants {mpb} bytes max, attempting chunks of {arguments.count} basepairs')

        progress_bar_tm = tqdm(desc=filenames[0] if len(filenames) == 1 else f'Pair (First File: {filenames[0]})',
                            unit=' reads' if len(filenames) == 1 else ' read pairs',
                            total=0, position = 0)

        all_reads = read_reads_from_files(arguments.files)

        submit_chunks(client, context, all_reads, arguments.count, arguments.retries, arguments.verbose, progress_bar_tm)
        statistics = close_context(client, context, arguments.verbose, progress_bar_tm)
        if statistics != None:
            progress_bar_tm.write(f'The server saved {len(statistics[0])} of {statistics[1]}.')
        progress_bar_tm.close()
        #Post Processing: If an output folder is given save the reads there
        if arguments.outfolder:
            print(f'Reconstructing the filtered read files in {arguments.outfolder}')
            os.makedirs(arguments.outfolder,exist_ok=True)

            filehandles = {}
            for fileidx, filename in enumerate(filenames):
                print(f'Reconstructing the filtered read files for file: {filename}')
                guessed_mimetype: Tuple[str, str] = mimetypes.guess_type(filename)
                #Generate output folder and create modified (infixed) filename for output
                split_components = os.path.basename(filename).split('.')
                new_filename = '.'.join([split_components[0]]+['filtered']+split_components[1:])
                outfile = os.path.join(arguments.outfolder,new_filename)
                filehandles[fileidx] = gzip.open(outfile,'wt') if guessed_mimetype[1] == 'gzip' else open(outfile,'w')
            for read_tuple in read_reads_from_files(arguments.files):
                #If we have paired-end reads the server only responds by sending the first read-id
                if read_tuple[0].barcode in statistics[0]:
                    for fileidx, read in enumerate(read_tuple):
                            filehandles[fileidx].write(str(read))

            for fileidx, filename in enumerate(filenames):
                filehandles[fileidx].close()

if __name__ == '__main__':
    main()
