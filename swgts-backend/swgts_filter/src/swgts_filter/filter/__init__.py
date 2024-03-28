# coding=utf-8
import os
import time
from logging import getLogger
from typing import Optional, Callable

from mappy import Aligner

ALL = ['is_read_legal', 'init_filter']

aligner: Optional[Aligner] = None
MINIMAP2_CONTIG: Optional[str] = None
MINIMAP2_QUALITY_THRESHOLD: Optional[int] = None
_actual_is_read_legal: Optional[Callable[[list[str]], bool]] = None
logger = getLogger(__name__)


def info(*args, **kwargs) -> None:
    logger.info(*args, **kwargs)


def is_read_legal(read: list[list[str]]) -> bool:
    """Return True if you want to keep the read.
    :param read: The read as n lists of reads (n=1 for single end, n=2 for paired end) ( 4 element List of str) ."""
    if read[0][2] == 'TOO_LONG':
        return False
    return _actual_is_read_legal(read)


def init_filter(filter_mode : str, mapping_preset: str, minimap2_reference_database: str, minimap2_positive_contig: str, minimap2_quality_threshold : int):
    global _actual_is_read_legal

    info(f'Filter initialization {filter_mode}')

    if filter_mode in ['COMBINED', 'NEGATIVE']:
        global aligner
        # TODO: Minimap2 Args to CONFIG
        print(f'Loading database {minimap2_reference_database} from {os.getcwd()}')
        aligner = Aligner(minimap2_reference_database, preset=mapping_preset, best_n=1)
        if not os.path.isfile(minimap2_reference_database):
            raise Exception('ERROR: failed to locate index')
        if filter_mode == 'COMBINED':
            global MINIMAP2_CONTIG
            MINIMAP2_CONTIG = minimap2_positive_contig
            _actual_is_read_legal = is_read_legal_combined
        elif filter_mode == 'NEGATIVE':
            global MINIMAP2_QUALITY_THRESHOLD
            _actual_is_read_legal = is_read_legal_negative
            MINIMAP2_QUALITY_THRESHOLD = minimap2_quality_threshold
    elif filter_mode == 'NONE':
        _actual_is_read_legal = is_read_legal_dummy
    else:
        raise NotImplemented()
    info(f'Filter initialized.')


def is_read_legal_dummy(_: list[list[str]]) -> bool:
    time.sleep(0.005)
    """Always returns True, pauses however for one second which can be used for benchmarking purposes"""
    return True

def is_read_legal_combined(read: list[list[str]]) -> bool:
    """Return True if you want to keep the read.
    :param read: The read as n lists of reads (n=1 for single end, n=2 for paired end) ( 4 element List of str) ."""

    try:
        hit = next(aligner.map(*[r[1] for r in read]))
    except StopIteration:
        return False
    return hit.ctg == MINIMAP2_CONTIG


def is_read_legal_negative(read: list[list[str]]) -> bool:
    """Return True if you want to keep the read.
    :param read: The read as n lists of reads (n=1 for single end, n=2 for paired end) ( 4 element List of str) ."""

    try:
        hit = next(aligner.map(*[r[1] for r in read]))
    except StopIteration:
        return True

    return hit.mapq < MINIMAP2_QUALITY_THRESHOLD
