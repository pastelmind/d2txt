#!/usr/bin/env python

"""Provides methods for converting D2TXT objects to and from INI files."""


from d2txt import D2TXT
from configparser import ConfigParser
import argparse


def _backtickify(s):
    """If the given string s has leading or trailing space characters, wraps it
    with a pair of backticks."""
    if s and (s[0].isspace() or s[-1].isspace()):
        return '`' + s + '`'
    else:
        return s

def _unbacktickify(s):
    """If the given string s is wrapped in a pair of backticks, removes it."""
    if s and s[0] == s[-1] == '`':
        return s[1:-1]
    else:
        return s


# See https://d2mods.info/forum/viewtopic.php?t=43737 for more information
AURAFILTER_FLAGS = {
    0x00000001: 'FindPlayers',
    0x00000002: 'FindMonsters',
    0x00000004: 'FindOnlyUndead',
    0x00000008: 'FindMissiles',         # Ignores missiles with explosion=1 in missiles.txt
    0x00000010: 'FindObjects',
    0x00000020: 'FindItems',
#   0x00000040: 'Unknown40',
    0x00000080: 'FindAttackable',       # Target units flagged as IsAtt in monstats2.txt
    0x00000100: 'NotInsideTowns',
    0x00000200: 'UseLineOfSight',
    0x00000400: 'FindSelectable',       # Checked manually by curse skill functions
#   0x00000800: 'Unknown800',
    0x00001000: 'FindCorpses',          # Targets corpses of monsters and players
    0x00002000: 'NotInsideTowns2',
    0x00004000: 'IgnoreBoss',           # Ignores units with SetBoss=1 in MonStats.txt
    0x00008000: 'IgnoreAllies',
    0x00010000: 'IgnoreNPC',           # Ignores units with npc=1 in MonStats.txt
    0x00020000: 'Unknown20000',
    0x00040000: 'IgnorePrimeEvil',     # Ignores units with primeevil=1 in MonStats.txt
    0x00080000: 'IgnoreJustHitUnits',  # Used by chainlightning
    # Rest are unknown
}

AURAFILTER_NAMES = {v: k for k, v in AURAFILTER_FLAGS.items()}


def decode_aurafilter(aurafilter):
    """Decodes an aurafilter value (integer) to a string of flag names."""
    aurafilter = int(aurafilter)
    if not aurafilter:
        return '0'

    af_names = []
    for bitshift in range(0, 32):
        flag = 1 << bitshift
        if aurafilter & flag:
            af_names.append(AURAFILTER_FLAGS.get(flag, f'{flag:#x}'))

    if af_names:
        return ' | '.join(af_names)
    else:
        return '0'


def encode_aurafilter(af_str):
    """
    Encodes a string of flag names separated by pipe characters (|) to an
    aurafilter value (string representation of decimal number).
    """
    if not af_str:
        return 0

    aurafilter = 0
    for flag_name in af_str.split('|'):
        flag = AURAFILTER_NAMES.get(flag_name.strip())
        if not flag:
            flag = int(flag_name, 0)
        aurafilter |= flag

    return str(aurafilter)


def txt_value_to_ini(value, column_name):
    """
    Decode a value from a TXT file to a string for an INI file. Uses the given
    column name to decide how to encode the value.
    """
    if column_name == 'aurafilter':
        return decode_aurafilter(value)

    return _backtickify(value)


def ini_value_to_txt(text, column_name):
    """
    Encode a string from an INI file to a value for a TXT file. Uses the given
    column name to decide how to decode the value.
    """
    if column_name == 'aurafilter':
        return encode_aurafilter(text)

    return _unbacktickify(text)


def ini_to_d2txt(inifile):
    """Creates a D2TXT object from an INI file.

    Args:
        inifile: A path string or readable file object
    """
    if isinstance(inifile, str):
        with open(inifile) as inifile_obj:
            return ini_to_d2txt(inifile_obj)

    ini_parser = ConfigParser(interpolation=None, delimiters='=', comment_prefixes=';')
    ini_parser.optionxform = str    # Make column names case-sensitive
    ini_parser.read_file(inifile)

    # Manually dedupe column names to ensure that warnings point to correct
    # lines in the source code
    unescaped_column_names = map(_unbacktickify, ini_parser['Columns'].keys())
    d2txt = D2TXT(D2TXT.dedupe_column_names(unescaped_column_names))

    for section_name, section in ini_parser.items():
        # Use each section name as the row index
        try:
            row_index = int(section_name) - 1
        except ValueError:
            continue

        while len(d2txt) <= row_index:
            d2txt.append([])

        for column_name, value in section.items():
            d2txt[row_index][column_name] = ini_value_to_txt(value, column_name)

    return d2txt


def d2txt_to_ini(d2txt, inifile):
    """Writes a D2TXT object to an INI file.

    Args:
        d2txt: A D2TXT object
        inifile: A path string or writable file object
    """
    if isinstance(inifile, str):
        with open(inifile, mode='w', newline='') as inifile_obj:
            d2txt_to_ini(d2txt, inifile_obj)
            return

    ini_parser = ConfigParser(interpolation=None, comment_prefixes=';')
    ini_parser.optionxform = str    # Make column names case-sensitive
    ini_parser['Columns'] = {_backtickify(name): '' for name in d2txt.column_names()}

    for row_index, row in enumerate(d2txt):
        section_name = str(row_index + 1)
        ini_parser[section_name] = {}
        for column_name, value in row.items():
            if value:
                ini_parser[section_name][column_name] = txt_value_to_ini(value, column_name)

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