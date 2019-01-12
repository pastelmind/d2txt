#!/usr/bin/env python

'''Provides methods for converting D2TXT objects to and from INI files.'''


from d2txt import D2TXT
from configparser import ConfigParser
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


def ini_to_d2txt(inifile):
    '''Creates a D2TXT object from an INI file.

    Args:
        inifile: A path string or readable file object
    '''
    if isinstance(inifile, str):
        with open(inifile) as inifile_obj:
            return ini_to_d2txt(inifile_obj)

    ini_parser = ConfigParser(interpolation=None, comment_prefixes=';')
    ini_parser.optionxform = str    # Make column names case-sensitive
    ini_parser.read_file(inifile)

    d2txt = D2TXT()
    d2txt._column_names = [_unbacktickify(column_name) for column_name in ini_parser['Columns'].keys()]

    for section_name, section in ini_parser.items():
        # Use each section name as the row index
        try:
            row_index = int(section_name) - 1
        except ValueError:
            continue

        while len(d2txt) <= row_index:
            d2txt.append([])

        for column_name, value in section.items():
            d2txt[row_index, column_name] = _unbacktickify(value)

    return d2txt


def d2txt_to_ini(d2txt, inifile):
    '''Writes a D2TXT object to an INI file.

    Args:
        d2txt: A D2TXT object
        inifile: A path string or writable file object
    '''
    if isinstance(inifile, str):
        with open(inifile, mode='w', newline='') as inifile_obj:
            d2txt_to_ini(d2txt, inifile_obj)
            return

    ini_parser = ConfigParser(interpolation=None, comment_prefixes=';')
    ini_parser.optionxform = str    # Make column names case-sensitive
    ini_parser['Columns'] = {_backtickify(column_name): '' for column_name in d2txt._column_names}

    for row_index, row in enumerate(d2txt):
        section_name = str(row_index + 1)
        ini_parser[section_name] = {}
        for column_index, value in enumerate(row):
            if value:
                column_name = d2txt._column_names[column_index]
                ini_parser[section_name][column_name] = _backtickify(value)

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

    if args.command == 'compile':
        d2txt = ini_to_d2txt(args.inifile)
        d2txt.to_txt(args.txtfile)
    elif args.command == 'decompile':
        d2txt = D2TXT.load_txt(args.txtfile)
        d2txt_to_ini(d2txt, args.inifile)
    else:
        print(f'Unknown command: {args.command}')