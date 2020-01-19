#!/usr/bin/env python
"""Provides methods for converting D2TXT objects to and from INI files."""

from configparser import ConfigParser
import argparse

from .d2txt import D2TXT


def escape_column_name(column_name):
    """Escapes a D2TXT column name to a valid INI key.

    The given string is escaped (i.e. surrounded by backticks) if it matches any
    of the following:

    - Is empty
    - Surrounded by backticks
    - Has leading/trailing whitespace (includes whitespace-only strings)
    - Has leading semicolon

    Also, all equal signs (`=`) are replaced with `${eq}`.

    Args:
        column_name: A column name string.

    Returns:
        An escaped key string.
    """
    column_name = column_name.replace('=', '${eq}')
    if (
            (not column_name)
            or (column_name[0] == column_name[-1] == '`')
            or (column_name[0].isspace() or column_name[-1].isspace())
            or (column_name[0] == ';')
    ):
        return f'`{column_name}`'
    return column_name


def escape_cell_value(value):
    """Escapes a D2TXT cell value to a valid INI value.

    The given string is escaped (i.e. surrounded by backticks) if it matches any
    of the following:

    - Surrounded by backticks
    - Has leading/trailing whitespace (includes whitespace-only strings)

    Args:
        value: A cell value string.

    Returns:
        An escaped value string.
    """
    if value and (
            value[0] == value[-1] == '`'
            or value[0].isspace()
            or value[-1].isspace()
    ):
        return f'`{value}`'
    return value


def unescape_column_name(column_name):
    """Un-escapes an INI key to a valid D2TXT column name.

    If the given string is wrapped in a pair of backticks, removes them.
    Also, all occurrences of `${eq}` are replaced with `=`.
    """
    column_name = column_name.replace('${eq}', '=')
    if column_name and column_name[0] == column_name[-1] == '`':
        return column_name[1:-1]
    return column_name


def unescape_cell_value(value):
    """Un-escapes an INI key or value to a valid D2TXT column name or value.

    If the given string is wrapped in a pair of backticks, removes them.
    """
    if value and value[0] == value[-1] == '`':
        return value[1:-1]
    return value


# See https://d2mods.info/forum/viewtopic.php?t=43737 for more information
AURAFILTER_FLAGS = {
    0x00000001: 'FindPlayers',
    0x00000002: 'FindMonsters',
    0x00000004: 'FindOnlyUndead',
    # Ignores missiles with explosion=1 in missiles.txt
    0x00000008: 'FindMissiles',
    0x00000010: 'FindObjects',
    0x00000020: 'FindItems',
    #   0x00000040: 'Unknown40',
    # Target units flagged as IsAtt in monstats2.txt
    0x00000080: 'FindAttackable',
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

    return ' | '.join(af_names) if af_names else '0'


def encode_aurafilter(af_str):
    """
    Encodes a string of flag names separated by pipe characters (|) to an
    aurafilter value (string representation of decimal number).
    """
    if not af_str:
        return 0

    aurafilter = 0
    for flag_name in af_str.split('|'):
        flag_name = flag_name.strip()
        flag = AURAFILTER_NAMES.get(flag_name)
        if not flag:
            try:
                flag = int(flag_name, 0)
            except ValueError:
                raise ValueError(
                    f'Unknown bit flag for aurafilter: {flag_name!r}'
                ) from None
        aurafilter |= flag

    return str(aurafilter)


def txt_value_to_ini(value, column_name):
    """
    Decode a value from a TXT file to a string for an INI file. Uses the given
    column name to decide how to encode the value.
    """
    if column_name == 'aurafilter':
        return decode_aurafilter(value)

    return escape_cell_value(value)


def ini_value_to_txt(text, column_name):
    """
    Encode a string from an INI file to a value for a TXT file. Uses the given
    column name to decide how to decode the value.
    """
    if column_name == 'aurafilter':
        return encode_aurafilter(text)

    return unescape_cell_value(text)


def ini_to_d2txt(inifile):
    """Creates a D2TXT object from an INI file.

    Args:
        inifile: A path string or readable file object
    """
    if isinstance(inifile, str):
        with open(inifile) as inifile_obj:
            return ini_to_d2txt(inifile_obj)

    ini_parser = ConfigParser(
        interpolation=None,
        comment_prefixes=';',
        delimiters='=',
        allow_no_value=True,
    )
    ini_parser.optionxform = str    # Make column names case-sensitive
    ini_parser.read_file(inifile)

    ini_keys = []
    for key, value in ini_parser['Columns'].items():
        if value and '\n' in value:
            raise ValueError(
                f'Multiple lines found in value for key {key!r}, section [Columns].\n'
                f'Try removing all whitespace characters before {value.splitlines()[1]!r}.'
            )
        ini_keys.append(key)

    # Manually dedupe column names to ensure that warnings point to correct
    # lines in the source code
    d2txt_file = D2TXT(
        D2TXT.dedupe_column_names(map(unescape_column_name, ini_keys))
    )
    # Mapping of INI key => unescaped, deduped column name
    ini_key_to_column_name = dict(zip(ini_keys, d2txt_file.column_names()))

    for section_name, section in ini_parser.items():
        # Use each section name as the row index
        try:
            row_index = int(section_name) - 1
        except ValueError:
            continue

        while len(d2txt_file) <= row_index:
            d2txt_file.append([])

        for ini_key, value in section.items():
            if value and '\n' in value:
                raise ValueError(
                    f'Multiple lines found in value for key {ini_key!r}, '
                    f'section [{section_name}].\n'
                    f'Try removing all whitespace characters before '
                    f'{value.splitlines()[1]!r}.'
                )
            column_name = ini_key_to_column_name[ini_key]
            d2txt_file[row_index][column_name] = ini_value_to_txt(
                value, column_name
            )

    return d2txt_file


def d2txt_to_ini(d2txt_file, inifile):
    """Writes a D2TXT object to an INI file.

    Args:
        d2txt_file: A D2TXT object
        inifile: A path string or writable file object
    """
    if isinstance(inifile, str):
        with open(inifile, mode='w', newline='') as inifile_obj:
            d2txt_to_ini(d2txt_file, inifile_obj)
            return

    ini_parser = ConfigParser(
        interpolation=None,
        comment_prefixes=';',
        delimiters='=',
        allow_no_value=True,
    )
    # Note: ConfigParser calls optionxform multiple times for each key/value.
    #       Because of this, escape_column_name cannot be directly assigned to
    #       optionxform; doing so causes each column name to be escaped *twice*
    #       when assigning a dictionary, as well as being generally inefficent.
    #       Hence, escape_column_name() must be called explicitly.
    ini_parser.optionxform = str    # Make column names case-sensitive
    ini_parser['Columns'] = {
        escape_column_name(name): None for name in d2txt_file.column_names()
    }

    for row_index, row in enumerate(d2txt_file):
        section = {}
        for column_name, value in row.items():
            if value:
                ini_key = escape_column_name(column_name)
                section[ini_key] = txt_value_to_ini(value, column_name)
        ini_parser[str(row_index + 1)] = section

    ini_parser.write(inifile, space_around_delimiters=True)


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_subparsers = arg_parser.add_subparsers(dest='command', required=True)

    arg_parser_compile = arg_subparsers.add_parser(
        'compile', help='Compile an INI file to a tabbed TXT file'
    )
    arg_parser_compile.add_argument('inifile')
    arg_parser_compile.add_argument('txtfile')

    arg_parser_decompile = arg_subparsers.add_parser(
        'decompile', help='Decompile a tabbed TXT file to an INI file'
    )
    arg_parser_decompile.add_argument('txtfile')
    arg_parser_decompile.add_argument('inifile')

    args = arg_parser.parse_args()

    if args.command == 'compile':
        d2txt_file = ini_to_d2txt(args.inifile)
        d2txt_file.to_txt(args.txtfile)
    elif args.command == 'decompile':
        d2txt_file = D2TXT.load_txt(args.txtfile)
        d2txt_to_ini(d2txt_file, args.inifile)
    else:
        print(f'Unknown command: {args.command}')
