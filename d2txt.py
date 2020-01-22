#!/usr/bin/env python
"""Provides the D2TXT class for loading and saving Diablo 2 TXT files."""

from argparse import ArgumentParser
import collections.abc
import csv
from itertools import islice
from os import PathLike
import sys
from typing import Any
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Sequence
from typing import TextIO
from typing import Tuple
from typing import Union
from warnings import warn

import qtoml
import toml


class DuplicateColumnNameWarning(Warning):
    """A warning issued when a duplicate column name is encountered and has been
    renamed."""


def _column_index_to_symbol(column_index: int) -> str:
    """Converts a column index to Excel-style column symbol.

    Args:
        column_index: Column index, first column starts at 0.

    Returns:
        Excel-syle column symbols in uppercase. Example:
            0 -> "A", 1 -> "B", ..., 25 -> "Z", 26 -> "AA", 27 -> "AB", ...
        If `column_index` is less than 0, returns an empty string.
    """
    column_symbol = ""
    while column_index >= 0:
        modulo = column_index % 26
        column_symbol = chr(modulo + ord("A")) + column_symbol
        column_index = (column_index - modulo) // 26 - 1
    return column_symbol


_RowPrototype = Union[Mapping[str, Any], Sequence[Any]]


class D2TXTRow(collections.abc.Mapping):
    """
    Represents a single row in a tabbed txt file.
    """

    def __init__(self, d2txt: "D2TXT", row: _RowPrototype) -> None:
        """Creates a row object for D2TXT.

        If `row` is a mapping, each key-value pair is copied to the new row.
        Keys that do not match any column name in `d2txt` are ignored.
        Otherwise, `row` is treated as an iterable of values to insert into each
        cell of the new row.

        Args:
            d2txt: The parent D2TXT object.
            row: Mapping or iterable of values to fill the row with.
        """
        self._d2txt = d2txt
        num_columns = len(d2txt.column_names())

        if isinstance(row, collections.abc.Mapping):
            self._row = [None] * num_columns
            for column_name, value in row.items():
                try:
                    self[column_name] = value
                except KeyError:
                    pass
        else:
            self._row = list(islice(row, num_columns))
            self._row += [None] * (num_columns - len(self._row))

    def __getitem__(self, key: str) -> Any:
        return self._row[self._d2txt.column_index(key)]

    def __iter__(self) -> Iterator:
        return iter(self._d2txt.column_names())

    def __len__(self) -> int:
        return len(self._row)

    def __setitem__(self, key: str, value: Any) -> None:
        self._row[self._d2txt.column_index(key)] = value


class D2TXTColumnNameView(collections.abc.Sequence):
    """A read-only view of the list of column names in a D2TXT object."""

    def __init__(self, column_names: Sequence[str]) -> None:
        self._column_names = column_names

    def __getitem__(self, index: int) -> str:
        return self._column_names[index]

    def __len__(self) -> int:
        return len(self._column_names)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}: {self._column_names!r}>"


class D2TXT(collections.abc.MutableSequence):
    """
    Represents a tab-separated TXT file used in Diablo 2.
    """

    def __init__(self, column_names: Iterable[str]) -> None:
        """Create a D2TXT object.

        Args:
            column_names: An iterable of column name strings. Duplicate column
                names are automatically renamed.
        """
        self._column_names = self.__class__.dedupe_column_names(column_names)
        self._column_indices = {
            name: index for index, name in enumerate(self._column_names)
        }
        self._rows = []

    def __getitem__(self, index: Union[int, slice]) -> Union[D2TXTRow, List[D2TXTRow]]:
        """Returns a row at the given index, or a `list` of rows if slice syntax
        is used."""
        return self._rows[index]

    def __len__(self) -> int:
        return len(self._rows)

    def __setitem__(
        self,
        index: Union[int, slice],
        value: Union[_RowPrototype, Iterable[_RowPrototype]],
    ) -> None:
        """Sets a row at the given index to `value`. If slice syntax is used,
        replaces the rows with each item in `value`."""
        if isinstance(index, slice):
            self._rows[index] = [D2TXTRow(self, row) for row in value]
        else:
            self._rows[index] = D2TXTRow(self, value)

    def __delitem__(self, index: int) -> None:
        """Deletes a row at the given index, or multiple rows if slice syntax
        is used."""
        del self._rows[index]

    def insert(self, index: int, value: _RowPrototype) -> None:
        self._rows.insert(index, D2TXTRow(self, value))

    def column_names(self) -> D2TXTColumnNameView:
        """Returns a read-only view of the list of column names."""
        return D2TXTColumnNameView(self._column_names)

    def column_index(self, column_name: str) -> int:
        """Returns the index of a column.

        Args:
            column_name: Column to search for. Column names are case-sensitive.

        Returns:
            0-based index of the column name.

        Raises:
            KeyError: If the column name does not exist.
        """
        return self._column_indices[column_name]

    @classmethod
    def load_txt(cls, txtfile: Union[str, PathLike, TextIO]) -> "D2TXT":
        """Creates a D2TXT object from a tabbed TXT file.

        Args:
            txtfile: A path string or readable text file object.

        Returns:
            The loaded D2TXT object.
        """
        try:
            txtfile_fd = open(txtfile, encoding="cp437")
        except TypeError:
            pass
        else:
            with txtfile_fd:
                return cls.load_txt(txtfile_fd)

        txt_reader = csv.reader(
            txtfile, dialect="excel-tab", quoting=csv.QUOTE_NONE, quotechar=None
        )

        # Manually dedupe column names to ensure that warnings point to correct
        # lines in the source code
        d2txt = cls(cls.dedupe_column_names(next(txt_reader)))
        d2txt.extend(txt_reader)
        return d2txt

    def to_txt(self, txtfile: Union[str, PathLike, TextIO]) -> None:
        """Writes the contents of this object to a TXT file.

        Args:
            txtfile: A path string or writable text file object.
        """
        try:
            txtfile_fd = open(txtfile, mode="w", newline="", encoding="cp437")
        except TypeError:
            pass
        else:
            with txtfile_fd:
                self.to_txt(txtfile_fd)
                return

        txt_writer = csv.writer(
            txtfile, dialect="excel-tab", quoting=csv.QUOTE_NONE, quotechar=None
        )
        txt_writer.writerow(self._column_names)
        txt_writer.writerows(row.values() for row in self._rows)

    @staticmethod
    def dedupe_column_names(column_names: Iterable[str]) -> List[str]:
        """Returns a list of de-duplicated names taken from `column_names`.

        Returns a list of names in `column_names`. If a duplicate name is found,
        issues a DuplicateColumnNameWarning and renames it to a unique name.

        Args:
            column_names: Iterable of column name strings.
        """
        # Build a list rather than yielding each name, as using a generator can
        # obfuscate the warning message when nested inside another generator.
        deduped_column_names = []
        column_names_seen = set()

        for column_index, name in enumerate(column_names):
            if name in column_names_seen:
                new_name = f"{name}({_column_index_to_symbol(column_index)})"
                while new_name in column_names_seen:
                    new_name += f"({_column_index_to_symbol(column_index)})"
                warn(
                    f"Column name {name!r} replaced with {new_name!r}",
                    DuplicateColumnNameWarning,
                    stacklevel=3,
                )
                name = new_name
            column_names_seen.add(name)
            deduped_column_names.append(name)

        return deduped_column_names


# See https://d2mods.info/forum/viewtopic.php?t=43737 for more information
# fmt: off
AURAFILTER_FLAGS = {
    "FindPlayers":          0x00000001,
    "FindMonsters":         0x00000002,
    "FindOnlyUndead":       0x00000004,
    # Ignores missiles with explosion=1 in missiles.txt
    "FindMissiles":         0x00000008,
    "FindObjects":          0x00000010,
    "FindItems":            0x00000020,
    # "Unknown40":          0x00000040,
    # Target units flagged as IsAtt in monstats2.txt
    "FindAttackable":       0x00000080,
    "NotInsideTowns":       0x00000100,
    "UseLineOfSight":       0x00000200,
    # Checked manually by curse skill functions
    "FindSelectable":       0x00000400,
    # "Unknown800":         0x00000800,
    # Targets corpses of monsters and players
    "FindCorpses":          0x00001000,
    "NotInsideTowns2":      0x00002000,
    # Ignores units with SetBoss=1 in MonStats.txt
    "IgnoreBoss":           0x00004000,
    "IgnoreAllies":         0x00008000,
    # Ignores units with npc=1 in MonStats.txt
    "IgnoreNPC":            0x00010000,
    # "Unknown20000":       0x00020000,
    # Ignores units with primeevil=1 in MonStats.txt
    "IgnorePrimeEvil":      0x00040000,
    "IgnoreJustHitUnits":   0x00080000,  # Used by chainlightning
    # Rest are unknown
}
# fmt: on


class _Hex(int):
    """Subclass of int that is always converted to a hexadecimal format string.

    This takes advantage of the way toml.dumps() and qtoml.dumps() handles
    integers: they simply convert them to strings.
    """

    def __str__(self) -> str:
        """Returns a hexadecimal representation of this value."""
        return f"0x{self:X}"


def decode_aurafilter(aurafilter: int) -> Tuple[List[str], _Hex]:
    """Decodes an AuraFilter value into a list of flag names.

    Args:
        aurafilter: Value of AuraFilter field in Skills.txt

    Returns:
        Tuple of (flag_names, unknown_bits).
        `flag_names` is a list containing known aurafilter names.
        `unknown_bits` is an integer containing all unknown bits in aurafilter.

    Raises:
        TypeError: If aurafilter is not an integer.
    """
    af_names = []
    for name, flag in AURAFILTER_FLAGS.items():
        if aurafilter & flag:
            aurafilter &= ~flag
            af_names.append(name)
    return af_names, _Hex(aurafilter)


def encode_aurafilter(flags: List[str]) -> int:
    """Returns an integer made from combining the list of AuraFilter flag names.

    Args:
        flags: List of AuraFilter flag names.

    Returns:
        Integer representing the combination of the given flags.
        If `flags` is empty, returns 0.

    Raises:
        ValueError: If an unknown flag name is encountered.
    """
    aurafilter = 0
    for name in flags:
        try:
            aurafilter |= AURAFILTER_FLAGS[name]
        except KeyError:
            raise ValueError(f"Unknown AuraFilter flag name: {name!r}") from None
    return aurafilter


def decode_txt_value(column_name: str, value: Union[int, str]) -> Any:
    """Decodes a value from a TXT cell so that it can be converted to TOML.

    Args:
        column_name: Column name of the cell, used to determine the appropriate
            decoding method.
        value: Value of the cell.

    Returns:
        Decoded value suitable for passing to a TOML dumper.
    """
    # If possible, attempt to convert strings to integers (but not other types)
    if isinstance(value, str):
        try:
            value = int(value)
        except ValueError:
            pass

    if column_name.casefold() == "aurafilter":
        try:
            af_flags, unknown_bits = decode_aurafilter(value)
        except TypeError:
            return value
        # Dirty workaround for the lack of heterogeneous arrays in TOML v0.5.0
        # NOTE: Revisit this when uiri/toml adds support for hetero arrays.
        return [af_flags, [unknown_bits]] if unknown_bits else [af_flags]

    return value


def encode_txt_value(column_name: str, value: Any) -> Union[int, str]:
    """Encodes a value loaded from TOML so that it can be stored in D2TXT.

    Args:
        column_name: Column name of the cell, used to determine the appropriate
            encoding method.
        value: Value loaded from TOML.

    Returns:
        Decoded value suitable for passing to D2TXT.
    """
    if column_name.casefold() == "aurafilter":
        try:
            aurafilter = encode_aurafilter(value[0])
        except TypeError:
            return value
        try:
            unknown_bits = value[1][0]
        except (IndexError, TypeError):
            unknown_bits = 0
        return aurafilter | unknown_bits

    return value


def d2txt_to_toml(d2txt: D2TXT) -> str:
    """Converts a D2TXT object to TOML markup.

    Args:
        d2txt: D2TXT object to convert.

    Returns:
        String containing TOML markup.
    """
    # Use qtoml.dumps(), because toml does not properly escape backslashes.
    # Possibly related issues:
    #   https://github.com/uiri/toml/issues/261
    #   https://github.com/uiri/toml/issues/201
    toml_rows = qtoml.dumps(
        {
            "rows": [
                {
                    key: decode_txt_value(key, value)
                    for key, value in row.items()
                    if not (value is None or value == "")
                }
                for row in d2txt
            ],
        }
    )
    toml_encoder = qtoml.encoder.TOMLEncoder()
    toml_columns = (
        "columns = [\n"
        + "".join(
            f"  {toml_encoder.dump_value(key)},\n" for key in d2txt.column_names()
        )
        + "]\n\n"
    )
    return toml_columns + toml_rows


def toml_to_d2txt(toml_data: str) -> D2TXT:
    """Loads a D2TXT file from TOML markup.

    Args:
        toml_data: String containing TOML markup.

    Returns:
        D2TXT object loaded from `toml_data`.
    """
    # Use toml.loads() because it's ~50% faster than qtoml.loads()
    toml_data = toml.loads(toml_data)
    d2txt_data = D2TXT(D2TXT.dedupe_column_names(toml_data["columns"]))
    for row in toml_data["rows"]:
        d2txt_data.append([])
        d2txt_row = d2txt_data[-1]
        for key, value in row.items():
            d2txt_row[key] = encode_txt_value(key, value)
    return d2txt_data


def main(argv: List[str]) -> None:
    """Entrypoint of the command line script."""
    arg_parser = ArgumentParser()
    arg_subparsers = arg_parser.add_subparsers(dest="command")

    arg_parser_compile = arg_subparsers.add_parser(
        "compile", help="Compile a TOML file to a tabbed TXT file"
    )
    arg_parser_compile.add_argument("tomlfile", help="TOML file to read from")
    arg_parser_compile.add_argument("txtfile", help="TXT file to write to")

    arg_parser_decompile = arg_subparsers.add_parser(
        "decompile", help="Decompile a tabbed TXT file to a TOML file"
    )
    arg_parser_decompile.add_argument("txtfile", help="TXT file to read from")
    arg_parser_decompile.add_argument("tomlfile", help="TOML file to write to")

    args = arg_parser.parse_args(argv)

    if args.command is None:
        arg_parser.print_help()
    elif args.command == "compile":
        with open(args.tomlfile, encoding="utf-8") as toml_file:
            d2txt_data = toml_to_d2txt(toml_file.read())
        d2txt_data.to_txt(args.txtfile)
    elif args.command == "decompile":
        d2txt_file = D2TXT.load_txt(args.txtfile)
        with open(args.tomlfile, mode="w", encoding="utf-8") as toml_file:
            toml_file.write(d2txt_to_toml(d2txt_file))
    else:
        raise RuntimeError(f"Unexpected command: {args.command!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
