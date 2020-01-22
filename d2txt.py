#!/usr/bin/env python
"""Provides the D2TXT class for loading and saving Diablo 2 TXT files."""

from argparse import ArgumentParser
import collections.abc
import csv
from itertools import islice
from os import PathLike
import sys
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import TextIO
from typing import Tuple
from typing import Union

import qtoml
import toml


class DuplicateColumnNameError(Exception):
    """Raised when a duplicate column name is found in a TXT file.

    Column names are considered duplicates when they are exactly the same.
    Column names that differ only in casing (e.g. `mycolumn` and `MyColumn`) do
    not cause this exception.

    Attributes:
        name: Duplicate column name.
        index: Index of the duplicate column. This *should* be the greater of
            the two indices of the duplicate columns (though not guaranteed).
        filename: Name of the TXT file, if available.
    """

    def __init__(self, name: str, index: int, filename: Optional[str] = None) -> None:
        super().__init__(name, index, filename)
        self.name = name
        self.index = index
        self.filename = filename


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
            column_names: Iterable of unique strings. Column names are
                case-sensitive.

        Raises:
            DuplicateColumnNameError: If a duplicate column name is found.
        """
        self._column_names = self.__class__._make_column_names(column_names)
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

        Raises:
            DuplicateColumnNameError: If a duplicate column name is found.
        """
        try:
            txtfile_fd = open(txtfile, encoding="cp949")
        except TypeError:
            pass
        else:
            with txtfile_fd:
                return cls.load_txt(txtfile_fd)

        txt_reader = csv.reader(
            txtfile, dialect="excel-tab", quoting=csv.QUOTE_NONE, quotechar=None
        )

        try:
            d2txt = cls(next(txt_reader))
        except DuplicateColumnNameError as err:
            raise DuplicateColumnNameError(
                name=err.name, index=err.index, filename=getattr(txtfile, "name", None)
            ) from None
        d2txt.extend(txt_reader)
        return d2txt

    def to_txt(self, txtfile: Union[str, PathLike, TextIO]) -> None:
        """Writes the contents of this object to a TXT file.

        Args:
            txtfile: A path string or writable text file object.
        """
        try:
            txtfile_fd = open(txtfile, mode="w", newline="", encoding="cp949")
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
    def _make_column_names(column_names: Iterable[str]) -> List[str]:
        """Extracts a list of strings taken from `column_names`.

        Args:
            column_names: Iterable of unique strings. Column names are
                case-sensitive.

        Raises:
            DuplicateColumnNameError: If a duplicate column name is found.
                The `name` and `index` attributes are set, but `filename` is not.
        """
        # Build a list rather than yielding each name, as using a generator can
        # obfuscate the warning message when nested inside another generator.
        deduped_column_names = []
        column_names_seen = set()

        for column_index, name in enumerate(column_names):
            if name in column_names_seen:
                raise DuplicateColumnNameError(name=name, index=column_index)
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


def range_1(stop: int) -> range:
    """Returns a range that starts at 1 and ends at `stop`, inclusive."""
    return range(1, stop + 1)


def make_colgroup(
    seq: Iterable[Union[int, str]], colgroup: str, columns: Iterable[str]
) -> Dict[str, List[str]]:
    """Generates a parametrized column group using a sequence of values."""
    return {
        colgroup.format(param): [col.format(param) for col in columns] for param in seq
    }


# Vendor names used in column names of Armor.txt, Misc.txt, Weapons.txt
_VENDORS = [
    "Akara",
    "Alkor",
    "Asheara",
    "Cain",
    "Charsi",
    "Drehya",
    "Drognan",
    "Elzix",
    "Fara",
    "Gheed",
    "Halbu",
    "Hralti",
    "Jamella",
    "Larzuk",
    "Lysander",
    "Malah",
    "Ormus",
]

# Columns with one variation per difficulty in MonStats.txt
_DIFFICULTY_BASED_COLUMNS = [
    "Level",
    "AIDel",
    "AIDist",
    "aip1",
    "aip2",
    "aip3",
    "aip4",
    "aip5",
    "aip6",
    "aip7",
    "aip8",
    "Drain",
    "ColdEffect",
    "ResDm",
    "ResMa",
    "ResFi",
    "ResLi",
    "ResCo",
    "ResPo",
    "ToBlock",
    "AC",
    "Exp",
    "A1MinD",
    "A1MaxD",
    "A1TH",
    "A2MinD",
    "A2MaxD",
    "A2TH",
    "S1MinD",
    "S1MaxD",
    "S1TH",
    "El1Pct",
    "El1MinD",
    "El1MaxD",
    "El1Dur",
    "El2Pct",
    "El2MinD",
    "El2MaxD",
    "El2Dur",
    "El3Pct",
    "El3MinD",
    "El3MaxD",
    "El3Dur",
    "MinHP",
    "MaxHP",
]

# Mapping of group alias => list of column names
# pylint: disable=line-too-long
# fmt: off
COLUMN_GROUPS = {
    # Armor.txt, Misc.txt, Weapons.txt
    **make_colgroup(range_1(3), "--StatAndCalc{}", ["stat{}", "calc{}"]),
    "--MinMaxDam": ["MinDam", "MaxDam"],
    "--2HandMinMaxDam": ["2HandMinDam", "2HandMaxDam"],
    "--MinMaxMisDam": ["MinMisDam", "MaxMisDam"],
    "--MinMaxStack": ["MinStack", "MaxStack"],
    **make_colgroup(_VENDORS, "--{}MinMax", ["{}Min", "{}Max"]),
    **make_colgroup(_VENDORS, "--{}MagicMinMax", ["{}MagicMin", "{}MagicMax"]),
    "--NormUberUltraCode": ["NormCode", "UberCode", "UltraCode"],
    "--wClass1And2Handed": ["wClass", "2HandedWClass"],
    "--InvWidthHeight": ["InvWidth", "InvHeight"],
    "--NightmareAndHellUpgrades": ["NightmareUpgrade", "HellUpgrade"],
    # AutoMagic.txt, MagicPrefix.txt, MagicSuffix.txt
    **make_colgroup(range_1(3), "--Mod{}MinMax", ["Mod{}Min", "Mod{}Max"]),
    # Missiles.txt
    "--pSrvCltDoFunc": ["pSrvDoFunc", "pCltDoFunc"],
    "--pSrvCltHitFunc": ["pSrvHitFunc", "pCltHitFunc"],
    **make_colgroup(range_1(3), "--SrvCltSubMissile{}", ["SubMissile{}", "CltSubMissile{}"]),
    **make_colgroup(range_1(4), "--SrvCltHitSubMissile{}", ["HitSubMissile{}", "CltHitSubMissile{}"]),
    **make_colgroup(range_1(5), "--ParamAndDesc{}", ["Param{}", "*param{} desc"]),
    **make_colgroup(range_1(5), "--CltParamAndDesc{}", ["CltParam{}", "*client param{} desc"]),
    **make_colgroup(range_1(3), "--sHitParAndDesc{}", ["sHitPar{}", "*server hit param{} desc"]),
    **make_colgroup(range_1(3), "--cHitParAndDesc{}", ["cHitPar{}", "*client hit param{} desc"]),
    **make_colgroup(range_1(2), "--dParamAndDesc{}", ["dParam{}", "*damage param{} desc"]),
    "--MinDamage0-5": ["MinDamage", "MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5"],
    "--MaxDamage0-5": ["MaxDamage", "MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5"],
    "--MinE0-5": ["EMin", "MinELev1", "MinELev2", "MinELev3", "MinELev4", "MinELev5"],
    "--MaxE0-5": ["EMax", "MaxELev1", "MaxELev2", "MaxELev3", "MaxELev4", "MaxELev5"],
    "--ELen0-3": ["ELen", "ELevLen1", "ELevLen2", "ELevLen3"],
    "--RedGreenBlue": ["Red", "Green", "Blue"],
    # MonStats.txt
    "--MinMaxGrp": ["MinGrp", "MaxGrp"],
    **make_colgroup(_DIFFICULTY_BASED_COLUMNS, "--{}-RNH", ["{}", "{}(N)", "{}(H)"]),
    # Skills.txt
    "--SrvCltStFunc": ["SrvStFunc", "CltStFunc"],
    "--SrvCltDoFunc": ["SrvDoFunc", "CltDoFunc"],
    "--SrvCltMissile": ["SrvMissile", "CltMissile"],
    **make_colgroup(["", "A", "B", "C"], "--SrvCltMissile{}", ["SrvMissile{}", "CltMissile{}"]),
    **make_colgroup(range_1(6), "--AuraStatAndCalc{}", ["AuraStat{}", "AuraStatCalc{}"]),
    **make_colgroup(range_1(6), "--PassiveStatAndCalc{}", ["PassiveStat{}", "PassiveCalc{}"]),
    **make_colgroup(range_1(3), "--AuraEventAndFunc{}", ["AuraEvent{}", "AuraEventFunc{}"]),
    "--AuraTgtEventAndFunc": ["AuraTgtEvent", "AuraTgtEventFunc"],
    "--PassiveEventAndFunc": ["PassiveEvent", "PassiveEventFunc"],
    **make_colgroup(range_1(8), "--ParamAndDescription{}", ["Param{}", "*Param{} Description"]),
    "--MinDam0-5": ["MinDamage", "MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5"],
    "--MaxDam0-5": ["MaxDamage", "MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5"],
    "--EMin0-5": ["EMin", "EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5"],
    "--EMax0-5": ["EMax", "EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5"],
    # "--ELen0-3": ["ELen", "ELevLen1", "ELevLen2", "ELevLen3"],  # Also in Skills.txt
    "--CostMultAdd": ["cost mult", "cost add"],
    # SkillDesc.txt
    "--SkillPageRowColumn": ["SkillPage", "SkillRow", "SkillColumn"],
    # TreasureClassEx.txt
    **make_colgroup(range_1(10), "ProbAndItem{}", ["Prob{}", "Item{}"]),
}
# fmt: on
# pylint: enable=line-too-long


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
    d2txt_data = D2TXT(toml_data["columns"])
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
        raise ValueError(f"Unexpected command: {args.command!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
