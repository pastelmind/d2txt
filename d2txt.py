#!/usr/bin/env python

import csv
from configparser import ConfigParser
import collections.abc
import argparse


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
        txt_reader = csv.reader(txtfile, dialect='excel-tab',
            quoting=csv.QUOTE_NONE, quotechar=None)
        self._column_names = list(next(txt_reader))
        self._rows = [D2TXTRow(row, self._column_names) for row in txt_reader]

    def to_txt(self, txtfile):
        txt_writer = csv.writer(txtfile, dialect='excel-tab',
            quoting=csv.QUOTE_NONE, quotechar=None)
        txt_writer.writerow(self._column_names)
        txt_writer.writerows(self._rows)

    def load_ini(self, inifile):
        ini_parser = ConfigParser(interpolation=None, comment_prefixes=';')
        ini_parser.optionxform = str    # Make column names case-sensitive
        ini_parser.read_file(inifile)

        self._column_names = list(ini_parser['Columns'].keys())

        for section_name, section in ini_parser.items():
            try:
                row_index = int(section_name) - 1
            except ValueError:
                continue

            while len(self._rows) <= row_index:
                self._rows.append(D2TXTRow([], self._column_names))

            row = self._rows[row_index]
            for column_name, value in section.items():
                row[column_name] = value

    def to_ini(self, inifile):
        ini_parser = ConfigParser(interpolation=None, comment_prefixes=';')
        ini_parser.optionxform = str    # Make column names case-sensitive
        ini_parser['Columns'] = {column_name: '' for column_name in self._column_names}

        for row_index, row in enumerate(self._rows):
            section_name = str(row_index + 1)
            ini_parser[section_name] = {}
            for column_index, value in enumerate(row):
                if value:
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
        with open(args.inifile) as inifile:
            d2txtfile.load_ini(inifile)
        with open(args.txtfile, mode='w', newline='') as txtfile:
            d2txtfile.to_txt(txtfile)
    elif args.command == 'decompile':
        with open(args.txtfile) as txtfile:
            d2txtfile.load_txt(txtfile)
        with open(args.inifile, mode='w', newline='') as inifile:
            d2txtfile.to_ini(inifile)
    else:
        print(f'Unknown command: {args.command}')