#!/usr/bin/env python
"""Benchmark D2TXT performance against Python's csv package."""
import csv
from io import StringIO
from pathlib import Path
from timeit import timeit
from typing import Dict

from d2txt import D2TXT


def load_txt_files():
    txt_files = {}
    for txt_path in Path('./data/global/excel').glob('*.txt'):
        with open(txt_path) as txt_file:
            txt_files[txt_path.name] = StringIO(
                initial_value=txt_file.read(), newline=''
            )
    return txt_files


def load_all_csv(txt_files: Dict[str, StringIO]) -> None:
    for txt_file in txt_files.values():
        tsv_file = csv.reader(
            txt_file,
            dialect='excel-tab',
            quoting=csv.QUOTE_NONE,
            quotechar=None,
        )
        all(1 for _ in tsv_file)
        txt_file.seek(0)


def load_all_csv_dict(txt_files: Dict[str, StringIO]) -> None:
    for txt_file in txt_files.values():
        tsv_file = csv.DictReader(
            txt_file,
            dialect='excel-tab',
            quoting=csv.QUOTE_NONE,
            quotechar=None,
        )
        all(1 for _ in tsv_file)
        txt_file.seek(0)


def load_all_d2txt(txt_files: Dict[str, StringIO]) -> None:
    for txt_file in txt_files.values():
        D2TXT.load_txt(txt_file)
        txt_file.seek(0)

txt_files = load_txt_files()

# Test loading speed
TRIES = 10
print(f'load_all_d2txt()    : {timeit(lambda: load_all_d2txt(txt_files), number=TRIES):.4f}')
print(f'load_all_csv()      : {timeit(lambda: load_all_csv(txt_files), number=TRIES):.4f}')
print(f'load_all_csv_dict() : {timeit(lambda: load_all_csv_dict(txt_files), number=TRIES):.4f}')
