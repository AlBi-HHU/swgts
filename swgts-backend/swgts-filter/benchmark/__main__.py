# coding=utf-8
import glob
import gzip
import sys
import os
import time
from importlib import reload
from typing import Optional

from Bio import SeqIO

import filter
from .config import TEST_MODES_PATH, TEST_SAMPLES_PATH

# TODO: Multiprocessing to add parallel processing of benchmarks?

if __name__ == '__main__':

    if len(sys.argv) != 2:
        print('specify output file ...')

    TEST_MODES = []
    for f in glob.glob(os.path.join(TEST_MODES_PATH, '*')):
        TEST_MODES.append(os.path.join(TEST_MODES_PATH, f))


    print(f'Found the following filter configurations: {TEST_MODES}')
    with open(sys.argv[1],'w') as outfile:
        print("Running Benchmarks ...")
        for filter_cfg in TEST_MODES:

            with open(filter_cfg, 'r') as cfg_file:

                content = cfg_file.read()

                params: Optional[dict[str, str]] = None
                samples: Optional[list[str]] = None

                exec(content)  # Very Python

                if params is None:
                    # The exec should have initialized parameters
                    print(f"{filter_cfg} hasn't initialized the benchmark. Please check the file!")
                    sys.exit(-1)


                if samples is None:
                    # The exec should have initialized samples
                    print(f"{filter_cfg} hasn't provided any samples. Please check the file!")
                    sys.exit(-1)

                for sample in samples:

                    #append path
                    sample = os.path.join(TEST_SAMPLES_PATH, sample)

                    start = time.time()

                    reload(filter)

                    print(f'Initializing the filter with: {params}')  # params comes from the exec
                    filter.init_filter(params)
                    # TODO: Actually do something
                    print(f'Benchmarking the file: {sample}')

                    reads = None

                    if sample.endswith('.gz'):
                        handle = gzip.open(sample, "rt")
                        reads = SeqIO.parse(handle, 'fastq')
                    else:
                        reads = SeqIO.parse(sample, 'fastq')

                    total = 0
                    filtered = 0

                    tp = 0
                    tn = 0
                    fp = 0
                    fn = 0

                    for read in reads:
                        total += 1

                        hasFiltered = not filter.is_read_legal(
                            ['dummyid',
                             read.seq,
                             '+',
                             'dummyquality'
                             ])

                        identifier = read.id.split('_')[0]
                        try:
                            assert(identifier in ['human','pathogen'])
                        except AssertionError as msg:
                                print('Identifier: {} makes no sense (should be human or pathogen)'.format(identifier))
                        shouldFilter = identifier == 'human'

                        filtered += hasFiltered

                        if shouldFilter and hasFiltered:
                            tp += 1
                        elif not shouldFilter and hasFiltered:
                            fp += 1
                        elif shouldFilter and not hasFiltered:
                            fn += 1
                        elif not shouldFilter and not hasFiltered:
                            tn += 1

                    end = time.time()

                    elapsed_time = end - start
                    print('Filtered {} of {} reads! (elapsed time: {}s)'.format(filtered,total,elapsed_time))
                    print('TP: {} TN: {} FP: {} FN: {}'.format(tp, tn, fp, fn))

                    if filtered == 0:
                        print('Nothing was filtered ... this is probably suspicious!')
                    else:
                        prec = tp / (tp + fp)
                        rec = tp / (tp + fn)
                        f1 = 2 * tp / (2 * tp + fp + fn)
                        print('Precision: {} Recall: {} F1: {}'.format(prec,rec,f1))

                    #Write to csv for easier downstream analysis
                    outfile.write('{},{},{},{},{},{},{},{},{},{},{},{}\n'.format(
                        params,sample,filtered,total,elapsed_time,tp,tn,fp,fn,prec,rec,f1
                    ))