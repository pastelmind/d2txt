#!/usr/bin/env python

import csv
from configparser import ConfigParser
import collections.abc
import argparse


def _backtickify(s):
    '''If the given string s has leading or trailing space characters, wraps it
    with a pair of backticks.'''
    if s[0] == ' ' or s[-1] == ' ':
        return '`' + s + '`'
    else:
        return s

def _unbacktickify(s):
    '''If the given string s is wrapped in a pair of backticks, removes it.'''
    if s[0] == s[-1] == '`':
        return s[1:-1]
    else:
        return s


def _column_index_to_str(column_index):
    '''Converts a 1-indexed column number to an Excel-style column name string
    (A, B, ...).'''
    column_name = ''
    while column_index > 0:
        modulo = (column_index - 1) % 26
        column_name = chr(modulo + ord('A')) + column_name
        column_index = (column_index - modulo) // 26
    return column_name


def txt2ini(txtfile, inifile):
    '''Decompiles Diablo 2 TXT files to INI files.

    Args:
        txtfile: A path string or readable file object
        inifile: A path string or writable file object
    '''
    if isinstance(txtfile, str):
        with open(txtfile) as txtfile_obj:
            txt2ini(txtfile_obj, inifile)
            return
    if isinstance(inifile, str):
        with open(inifile, mode='w', newline='') as inifile_obj:
            txt2ini(txtfile, inifile_obj)
            return

    txt_reader = csv.reader(txtfile, dialect='excel-tab',
        quoting=csv.QUOTE_NONE, quotechar=None)

    ini_parser = ConfigParser(interpolation=None, comment_prefixes=';')
    ini_parser.optionxform = str    # Make column names case-sensitive

    # Parse the first row (column names)
    column_names = []
    column_name_set = set()
    for column_index, column_name in enumerate(next(txt_reader)):
        #Fix for empty column names
        if column_name == '':
            column_name = f'(col{_column_index_to_str(column_index + 1)})'

        #Fix for duplicate column names
        while column_name in column_name_set:
            alt_column_name = f'{column_name}({_column_index_to_str(column_index + 1)})'
            print(f'Duplicate column name detected: {column_name} replaced with {alt_column_name}')
            column_name = alt_column_name

        column_name_set.add(column_name)
        column_names.append(_backtickify(column_name))

    ini_parser['Columns'] = {column_name: '' for column_name in column_names}

    # Parse the remaining rows
    for row_index, txt_row in enumerate(txt_reader):
        section_name = str(row_index + 1)
        ini_parser[section_name] = {}
        for column_index, value in enumerate(txt_row):
            if value:
                value = _backtickify(value)
                ini_parser[section_name][column_names[column_index]] = value

    ini_parser.write(inifile, space_around_delimiters=False)



class D2TXTRow(collections.abc.Sequence):
    '''
    Represents a single row in a tabbed txt file.
    '''

    def __init__(self, row, column_names):
        self._row = list(row) + [None] * (len(column_names) - len(row))
        self._column_names = column_names

    def __getitem__(self, key):
        if isinstance(key, str):
            key = self._column_names.index(key)
        return self._row[key]

    def __len__(self):
        return len(self._row)

    def __setitem__(self, key, value):
        if isinstance(key, str):
            key = self._column_names.index(key)
        self._row[key] = value


class D2TXT(collections.abc.Sequence):
    '''
    Represents a tab-separated TXT file used in Diablo 2.
    '''

    def __init__(self):
        self._column_names = []
        self._rows = []

    # def col(self, column_name):
    #     pass

    def __getitem__(self, key):
        if isinstance(key, tuple):
            if len(key) != 2:
                raise KeyError(f'Invalid number of keys given, expected 2: {key}')
            row_index, column_key = key
            return self.__getitem__(row_index)[column_key]
        else:
            return self._rows[key]

    def __len__(self):
        return len(self._rows)

    def __setitem__(self, key, value):
        if isinstance(key, tuple):
            if len(key) != 2:
                raise KeyError(f'Invalid number of keys given, expected 2: {key}')
            row_index, column_key = key
            self.__getitem__(row_index)[column_key] = value
        else:
            self._rows[key] = D2TXTRow(value, self._column_names)

    def column_names(self):
        '''Returns a tuple of column names.'''
        return tuple(self._column_names)


    def load_txt(self, txtfile):
        if isinstance(txtfile, str):
            with open(txtfile) as txtfile_obj:
                self.load_txt(txtfile_obj)
                return

        txt_reader = csv.reader(txtfile, dialect='excel-tab',
            quoting=csv.QUOTE_NONE, quotechar=None)

        self._column_names = list(next(txt_reader))

        column_name_set = set()
        for column_index, column_name in enumerate(self._column_names):
            #Fix for empty column names
            if column_name == '':
                column_name = f'(col{_column_index_to_str(column_index + 1)})'

            #Fix for duplicate column names
            while column_name in column_name_set:
                alt_column_name = f'{column_name}({_column_index_to_str(column_index + 1)})'
                print(f'Duplicate column name detected: {column_name} replaced with {alt_column_name}')
                column_name = alt_column_name

            column_name_set.add(column_name)
            self._column_names[column_index] = column_name

        self._rows = [D2TXTRow(row, self._column_names) for row in txt_reader]

    def to_txt(self, txtfile):
        if isinstance(txtfile, str):
            with open(txtfile, mode='w', newline='') as txtfile_obj:
                self.to_txt(txtfile_obj)
                return

        txt_writer = csv.writer(txtfile, dialect='excel-tab',
            quoting=csv.QUOTE_NONE, quotechar=None)
        txt_writer.writerow(self._column_names)
        txt_writer.writerows(self._rows)

    def load_ini(self, inifile):
        if isinstance(inifile, str):
            with open(inifile) as inifile_obj:
                self.load_ini(inifile_obj)
                return

        ini_parser = ConfigParser(interpolation=None, comment_prefixes=';')
        ini_parser.optionxform = str    # Make column names case-sensitive
        ini_parser.read_file(inifile)

        self._column_names = [_unbacktickify(column_name) for column_name in ini_parser['Columns'].keys()]

        for section_name, section in ini_parser.items():
            try:
                row_index = int(section_name) - 1
            except ValueError:
                continue

            while len(self._rows) <= row_index:
                self._rows.append(D2TXTRow([], self._column_names))

            row = self._rows[row_index]
            for column_name, value in section.items():
                row[column_name] = _unbacktickify(value)

    def to_ini(self, inifile):
        if isinstance(inifile, str):
            with open(inifile, mode='w', newline='') as inifile_obj:
                self.to_ini(inifile_obj)
                return

        ini_parser = ConfigParser(interpolation=None, comment_prefixes=';')
        ini_parser.optionxform = str    # Make column names case-sensitive
        ini_parser['Columns'] = {_backtickify(column_name): '' for column_name in self._column_names}

        for row_index, row in enumerate(self._rows):
            section_name = str(row_index + 1)
            ini_parser[section_name] = {}
            for column_index, value in enumerate(row):
                if value:
                    value = _backtickify(value)
                    ini_parser[section_name][self._column_names[column_index]] = value

        ini_parser.write(inifile, space_around_delimiters=False)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_subparsers = arg_parser.add_subparsers(dest='command', required=True)

    arg_parser_compile = arg_subparsers.add_parser('compile', help='Compile an INI file to a tabbed TXT file')
    arg_parser_compile.add_argument('inifile')
    arg_parser_compile.add_argument('txtfile')

    arg_parser_decompile = arg_subparsers.add_parser('decompile', help='Decompile a tabbed TXT file to an INI file')
    arg_parser_decompile.add_argument('txtfile')
    arg_parser_decompile.add_argument('inifile')

    args = arg_parser.parse_args()

    d2txtfile = D2TXT()

    if args.command == 'compile':
        d2txtfile.load_ini(args.inifile)
        d2txtfile.to_txt(args.txtfile)
    elif args.command == 'decompile':
        txt2ini(args.txtfile, args.inifile)
    else:
        print(f'Unknown command: {args.command}')