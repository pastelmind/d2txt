#!/usr/bin/env python
"""Provides the D2TXT class for loading and saving Diablo 2 TXT files."""

from argparse import ArgumentParser
from collections import UserDict
import collections.abc
import csv
import enum
from itertools import chain
from itertools import islice
from itertools import zip_longest
from os import PathLike
import sys
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import NamedTuple
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


@enum.unique
class ColumnGroupType(enum.Enum):
    """Represents how the column group should be represented in TOML."""

    ARRAY = enum.auto()
    TABLE = enum.auto()


def range_1(stop: int) -> range:
    """Returns a range that starts at 1 and ends at `stop`, inclusive."""
    return range(1, stop + 1)


class ColumnGroupDefinition(NamedTuple):
    """Defines a column group."""

    type: ColumnGroupType
    alias: str
    members: Union[Tuple[str, ...], Tuple[Tuple[str, str], ...]]

    def member_names(self) -> Iterable[str]:
        """Returns an iterator of member column names."""
        if self.type == ColumnGroupType.ARRAY:
            return self.members
        if self.type == ColumnGroupType.TABLE:
            return (member_name for member_alias, member_name in self.members)
        raise ValueError(f"Invalid column group definition {self}")


def make_colgroup(
    params: Iterable[Union[int, str]],
    colgroup: str,
    columns: Union[Iterable[str], Mapping[str, str]],
) -> Iterator[Tuple[str, Union[Tuple[str, ...], Dict[str, str]]]]:
    """Generates column groups by using formatting parameters."""
    if isinstance(columns, collections.abc.Mapping):
        return (
            (colgroup.format(p), {k.format(p): v.format(p) for k, v in columns.items()})
            for p in params
        )
    return (
        (colgroup.format(p), tuple(col.format(p) for col in columns)) for p in params
    )


def initialize_column_groups(
    *colgroups: Sequence[Tuple[str, Union[Mapping[str, str], Sequence[str]]]]
) -> List[ColumnGroupDefinition]:
    """Initializes the list of column groups.

    Args:
        colgroups: Tuples of the form
            (group alias, mapping or sequence of member columns).

    Returns:
        List of unique column group definitions.
        The type of collection holding the member columns is used to deduce the
        group type and generate the `members` field accordingly.
        The list is sorted by # of member columns, from greatest to least.
    """
    return sorted(
        # Rely on preservation of insertion order of dicts Python 3.6+ to ensure
        # that column groups with equal member count maintain the same order.
        dict.fromkeys(
            # Convert mappings to tuples to make them hashable
            ColumnGroupDefinition(
                type=ColumnGroupType.TABLE, alias=alias, members=tuple(members.items())
            )
            if isinstance(members, collections.abc.Mapping)
            else ColumnGroupDefinition(
                type=ColumnGroupType.ARRAY, alias=alias, members=tuple(members)
            )
            for alias, members in colgroups
        ),
        key=lambda colgroup: len(colgroup.members),
        reverse=True,
    )


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

# List of column group definitions
# pylint: disable=line-too-long
# fmt: off
COLUMN_GROUPS = initialize_column_groups(
    # Armor.txt, Misc.txt, Weapons.txt
    ("__AC", {"min": "MinAC", "max": "MaxAC"}),
    *make_colgroup(range_1(3), "__Stat{}", {"stat": "stat{}", "calc": "calc{}"}),
    ("__Damage", {"min": "MinDam", "max": "MaxDam"}),
    ("__2HandDam", {"min": "2HandMinDam", "max": "2HandMaxDam"}),
    ("__MisDam", {"min": "MinMisDam", "max": "MaxMisDam"}),
    ("__Stack", {"min": "MinStack", "max": "MaxStack"}),
    *make_colgroup(
        _VENDORS,
        "__{}MinMax",
        {"Min": "{}Min", "Max": "{}Max", "MagicMin": "{}MagicMin", "MagicMax": "{}MagicMax", "MagicLvl": "{}MagicLvl"},
    ),
    ("__Code", {"normal": "NormCode", "uber": "UberCode", "ultra": "UltraCode"}),
    ("__wClass", {"1hand": "wClass", "2hand": "2HandedWClass"}),
    ("__Inv", {"width": "InvWidth", "height": "InvHeight"}),
    ("__Upgrades", {"nightmare": "NightmareUpgrade", "hell": "HellUpgrade"}),
    # AutoMagic.txt, MagicPrefix.txt, MagicSuffix.txt
    *make_colgroup(range_1(3), "__Mod{}", {"prop": "Mod{}Code", "param": "Mod{}Param", "min": "Mod{}Min", "max": "Mod{}Max"}),
    ("--IType1-7", tuple(f"IType{i}" for i in range_1(7))),
    ("--EType1-3", tuple(f"EType{i}" for i in range_1(3))),
    ("--EType1-5", tuple(f"EType{i}" for i in range_1(5))),  # For MagicPrefix.txt
    ("__Cost", {"divide": "Divide", "multiply": "Multiply", "add": "Add"}),
    # CharStats.txt
    *make_colgroup(range_1(10), "__Item{}", {"code": "Item{}", "loc": "Item{}Loc", "count": "Item{}Count"}),
    # CubeMain.txt
    *make_colgroup(range_1(5), "__Mod{}", {"mod": "mod {}", "chance": "mod {} chance", "param": "mod {} param", "min": "mod {} min", "max": "mod {} max"}),
    *make_colgroup(range_1(5), "__B_Mod{}", {"mod": "b mod {}", "chance": "b mod {} chance", "param": "b mod {} param", "min": "b mod {} min", "max": "b mod {} max"}),
    *make_colgroup(range_1(5), "__C_Mod{}", {"mod": "c mod {}", "chance": "c mod {} chance", "param": "c mod {} param", "min": "c mod {} min", "max": "c mod {} max"}),
    # Gems.txt
    *make_colgroup(range_1(3), "__WeaponMod{}", {"prop": "WeaponMod{}Code", "param": "WeaponMod{}Param", "min": "WeaponMod{}Min", "max": "WeaponMod{}Max"}),
    *make_colgroup(range_1(3), "__HelmMod{}", {"prop": "HelmMod{}Code", "param": "HelmMod{}Param", "min": "HelmMod{}Min", "max": "HelmMod{}Max"}),
    *make_colgroup(range_1(3), "__ShieldMod{}", {"prop": "ShieldMod{}Code", "param": "ShieldMod{}Param", "min": "ShieldMod{}Min", "max": "ShieldMod{}Max"}),
    # Hireling.txt
    ("__Name", {"first": "NameFirst", "last": "NameLast"}),
    *make_colgroup(["HP", "Str", "Dex", "AR", "Resist"], "__{}", {"base": "{}", "/lvl": "{}/Lvl"}),
    ("__Defense", {"base": "Defense", "/lvl": "Def/Lvl"}),
    ("__Damage", {"min": "Dmg-Min", "max": "Dmg-Max", "/lvl": "Dmg/Lvl"}),
    *make_colgroup(
        range_1(6),
        "__Skill{}",
        {"name": "Skill{}", "mode": "Mode{}", "chance": "Chance{}", "chance/lvl": "ChancePerLvl{}", "level": "Level{}", "level/lvl": "LvlPerLvl{}"},
    ),
    # Inventory.txt
    ("__Inv", {"left": "InvLeft", "right": "InvRight", "top": "InvTop", "bottom": "InvBottom"}),
    ("__Grid", {"left": "GridLeft", "right": "GridRight", "top": "GridTop", "bottom": "GridBottom", "x": "GridX", "y": "GridY"}),
    ("__GridBox", {"width": "GridBoxWidth", "height": "GridBoxHeight"}),
    *make_colgroup(
        ("Inv", "rArm", "Torso", "lArm", "Head", "Neck", "rHand", "lHand", "Belt", "Feet", "Gloves"),
        "__{}",
        {"left": "{}Left", "right": "{}Right", "top": "{}Top", "bottom": "{}Bottom", "width": "{}Width", "height": "{}Height"},
    ),
    *make_colgroup(
        ["rArm", "Torso", "lArm", "Head", "Neck", "rHand", "lHand", "Belt", "Feet", "Gloves"],
        "--{}LeftRightTopBottomWidthHeight",
        ["{}Left", "{}Right", "{}Top", "{}Bottom", "{}Width", "{}Height"]
    ),
    # ItemTypes.txt
    ("--BodyLoc1-2", ("BodyLoc1", "BodyLoc2")),
    ("--MaxSock1-25-40", ("MaxSock1", "MaxSock25", "MaxSock40")),
    # Levels.txt
    *make_colgroup(["", "(N)", "(H)"], "--SizeXY{}", ["SizeX{}", "SizeY{}"]),
    ("--OffsetXY", ("OffsetX", "OffsetY")),
    *make_colgroup(range(8), "--VizAndWarp{}", ["Vis{}", "Warp{}"]),
    ("--MonLvl-123", ("MonLvl1", "MonLvl2", "MonLvl3")),
    ("--MonLvlEx-123", ("MonLvl1Ex", "MonLvl2Ex", "MonLvl3Ex")),
    ("--MonDen-RNH", ("MonDen", "MonDen(N)", "MonDen(H)")),
    *make_colgroup(["", "(N)", "(H)"], "--MonUMinMax{}", ["MonUMin{}", "MonUMax{}"]),
    *make_colgroup(range(8), "--ObjGrpAndPrb{}", ["ObjGrp{}", "ObjPrb{}"]),
    # LvlMaze.txt
    ("--Rooms-RNH", ("Rooms", "Rooms(N)", "Rooms(H)")),
    # ("--SizeXY", ("SizeX", "SizeY")),  # Also in Levels.txt
    # LvlPrest.txt
    # ("--SizeXY", ("SizeX", "SizeY")),  # Also in Levels.txt
    # Missiles.txt
    ("__pDoFunc", {"srv": "pSrvDoFunc", "clt": "pCltDoFunc"}),
    ("__pHitFunc", {"srv": "pSrvHitFunc", "clt": "pCltHitFunc"}),
    *make_colgroup(range_1(3), "__SubMissile{}", {"srv": "SubMissile{}", "clt": "CltSubMissile{}"}),
    *make_colgroup(range_1(4), "__HitSubMissile{}", {"srv": "HitSubMissile{}", "clt": "CltHitSubMissile{}"}),
    *make_colgroup(range_1(5), "__Param{}", {"param": "Param{}", "desc": "*param{} desc"}),
    *make_colgroup(range_1(5), "__CltParam{}", {"clt": "CltParam{}", "desc": "*client param{} desc"}),
    *make_colgroup(range_1(3), "__SrvHitParam{}", {"param": "sHitPar{}", "desc": "*server hit param{} desc"}),
    *make_colgroup(range_1(3), "__CltHitParam{}", {"param": "cHitPar{}", "desc": "*client hit param{} desc"}),
    *make_colgroup(range_1(2), "__DamageParam{}", {"param": "dParam{}", "desc": "*damage param{} desc"}),
    ("--MinDamage0-5", ("MinDamage", "MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5")),
    ("--MaxDamage0-5", ("MaxDamage", "MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5")),
    ("--MinE0-5", ("EMin", "MinELev1", "MinELev2", "MinELev3", "MinELev4", "MinELev5")),
    ("--MaxE0-5", ("EMax", "MaxELev1", "MaxELev2", "MaxELev3", "MaxELev4", "MaxELev5")),
    ("--ELen0-3", ("ELen", "ELevLen1", "ELevLen2", "ELevLen3")),
    ("--RedGreenBlue", ("Red", "Green", "Blue")),
    # MonProp.txt
    *make_colgroup(range_1(6), "--MinMax{}", ["Min{}", "Max{}"]),
    *make_colgroup(range_1(6), "--MinMax{} (N)", ["Min{} (N)", "Max{} (N)"]),
    *make_colgroup(range_1(6), "--MinMax{} (H)", ["Min{} (H)", "Max{} (H)"]),
    # MonStats.txt
    ("__Spawn", {"place": "PlaceSpawn", "x": "SpawnX", "y": "SpawnY", "mode": "SpawnMode"}),
    ("__Party", {"min": "PartyMin", "max": "PartyMax"}),
    ("__Grp", {"min": "MinGrp", "max": "MaxGrp"}),
    *make_colgroup(["Level", "Drain", "ColdEffect", "ToBlock", "AC", "Exp"], "--{}-RNH", ["{}", "{}(N)", "{}(H)"]),
    ("__AI_R", {"delay": "AIDel", "dist": "AIDist", **{f"p{i}": f"aip{i}" for i in range_1(8)}}),
    ("__AI_N", {"delay": "AIDel(N)", "dist": "AIDist(N)", **{f"p{i}": f"aip{i}(N)" for i in range_1(8)}}),
    ("__AI_H", {"delay": "AIDel(H)", "dist": "AIDist(H)", **{f"p{i}": f"aip{i}(H)" for i in range_1(8)}}),
    *make_colgroup(range_1(8), "__Skill{}", {"name": "Skill{}", "mode": "Sk{}Mode", "level": "Sk{}Lvl"}),
    ("__Res_R", {"phys": "ResDm", "mag": "ResMa", "fire": "ResFi", "ltng": "ResLi", "cold": "ResCo", "pois": "ResPo"}),
    ("__Res_N", {"phys": "ResDm(N)", "mag": "ResMa(N)", "fire": "ResFi(N)", "ltng": "ResLi(N)", "cold": "ResCo(N)", "pois": "ResPo(N)"}),
    ("__Res_H", {"phys": "ResDm(H)", "mag": "ResMa(H)", "fire": "ResFi(H)", "ltng": "ResLi(H)", "cold": "ResCo(H)", "pois": "ResPo(H)"}),
    ("__HP_R", {"min": "MinHP", "max": "MaxHP"}),
    ("__HP_N", {"min": "MinHP(N)", "max": "MaxHP(N)"}),
    ("__HP_H", {"min": "MinHP(H)", "max": "MaxHP(H)"}),
    *make_colgroup(["A1", "A2", "S1"], "__{}_R", {"MinD": "{}MinD", "MaxD": "{}MaxD", "TH": "{}TH"}),
    *make_colgroup(["A1", "A2", "S1"], "__{}_N", {"MinD": "{}MinD(N)", "MaxD": "{}MaxD(N)", "TH": "{}TH(N)"}),
    *make_colgroup(["A1", "A2", "S1"], "__{}_H", {"MinD": "{}MinD(H)", "MaxD": "{}MaxD(H)", "TH": "{}TH(H)"}),
    *make_colgroup(range_1(3), "__El{}", {"mode": "El{}Mode", "type": "El{}Type"}),
    *make_colgroup(range_1(3), "__El{}_R", {"Pct": "El{}Pct", "MinD": "El{}MinD", "MaxD": "El{}MaxD", "Dur": "El{}Dur"}),
    *make_colgroup(range_1(3), "__El{}_N", {"Pct": "El{}Pct(N)", "MinD": "El{}MinD(N)", "MaxD": "El{}MaxD(N)", "Dur": "El{}Dur(N)"}),
    *make_colgroup(range_1(3), "__El{}_H", {"Pct": "El{}Pct(H)", "MinD": "El{}MinD(H)", "MaxD": "El{}MaxD(H)", "Dur": "El{}Dur(H)"}),
    ("--TreasureClass-R", [f"TreasureClass{i}" for i in range_1(4)]),
    ("--TreasureClass-N", [f"TreasureClass{i}(N)" for i in range_1(4)]),
    ("--TreasureClass-H", [f"TreasureClass{i}(H)" for i in range_1(4)]),
    # MonStats2.txt
    # ("--SizeXY", ("SizeX", "SizeY")),  # Also in Levels.txt
    ("--Light-RGB", ("Light-R", "Light-G", "Light-B")),
    ("--uTrans-RNH", ("uTrans", "uTrans(N)", "uTrans(H)")),
    *make_colgroup(("HD", "TR", "LG", "RA", "LA", "RH", "SH"), "__{}", {"on": "{}", "v": "{}v"}),
    *make_colgroup(("DT", "NU", "WL", "GH", "BL", "DD", "KB", "SQ", "RN"), "__{}", {"m": "m{}", "d": "d{}"}),
    *make_colgroup(("A1", "A2", "SC", "S3", "S4"), "__{}", {"m": "m{}", "d": "d{}", "mv": "{}mv"}),
    *make_colgroup(("S1", "S2"), "__{}", {"on": "{}", "v": "{}v", "m": "m{}", "d": "d{}", "mv": "{}mv"}),
    ("__ht", {"left": "Left", "top": "Top", "width": "Width", "height": "Height"}),
    # Objects.txt
    ("__nTgt", {"fx": "nTgtFX", "fy": "nTgtFY", "bx": "nTgtBX", "by": "nTgtBY"}),
    *make_colgroup(["Offset", "Space"], "--XY{}", ["X{}", "Y{}"]),
    *make_colgroup(
        ("Selectable", "FrameCnt", "FrameDelta", "CycleAnim", "Lit", "BlocksLight", "HasCollision", "Start", "OrderFlag", "Mode", "Parm"),
        "__{}",
        {mode: f"{{}}{index}" for index, mode in enumerate(["NU", "OP", "ON", "S1", "S2", "S3", "S4", "S5"])},
    ),
    ("__Selectable", {"NU": "Selectable0", "OP": "Selectable1"}),
    ("__FrameCnt", {"NU": "FrameCnt0", "OP": "FrameCnt1"}),
    ("__Box", {"left": "Left", "top": "Top", "width": "Width", "height": "Height"}),
    # Overlay.txt
    # ("--XYOffset", ("xOffset", "yOffset")),  # Also in Objects.txt
    # ("--RedGreenBlue", ("Red", "Green", "Blue")),  # Also in Missiles.txt
    # Runes.txt
    ("--IType1-6", tuple(f"IType{i}" for i in range_1(6))),
    # ("--EType1-3", tuple(f"IType{i}" for i in range_1(3))),  # Also in AutoMagic.txt
    ("--Rune1-6", tuple(f"Rune{i}" for i in range_1(6))),
    *make_colgroup(range_1(7), "__T1_{}", {"prop": "T1Code{}", "param": "T1Param{}", "min": "T1Min{}", "max": "T1Max{}"}),
    # Sets.txt
    *make_colgroup(range(2, 6), "__P{}A", {"prop": "pCode{}A", "param": "pParam{}A", "min": "pMin{}A", "max": "pMax{}A"}),
    *make_colgroup(range(2, 6), "__P{}B", {"prop": "pCode{}B", "param": "pParam{}B", "min": "pMin{}B", "max": "pMax{}B"}),
    *make_colgroup(range_1(8), "__F{}", {"prop": "fCode{}", "param": "fParam{}", "min": "fMin{}", "max": "fMax{}"}),
    # SetItems.txt
    # *make_colgroup(range_1(9), "__Prop{}", {"prop": "Prop{}", "param": "Par{}", "min": "Min{}", "max": "Max{}"}),  # Also in UniqueItems.txt
    *make_colgroup(range_1(5), "__aProp{}A", {"prop": "aProp{}A", "param": "aPar{}A", "min": "aMin{}A", "max": "aMax{}A"}),
    *make_colgroup(range_1(5), "__aProp{}B", {"prop": "aProp{}B", "param": "aPar{}B", "min": "aMin{}B", "max": "aMax{}B"}),
    # Skills.txt
    ("__StartFunc", {"srv": "SrvStFunc", "clt": "CltStFunc"}),
    ("__DoFunc", {"srv": "SrvDoFunc", "clt": "CltDoFunc"}),
    *make_colgroup(["", "A", "B", "C"], "__Missile{}", {"srv": "SrvMissile{}", "clt": "CltMissile{}"}),
    ("__MissileD", {"clt": "CltMissileD"}),  # No matching server-side missile field, but added for consistency's sake
    *make_colgroup(range_1(6), "__AuraStat{}", {"stat": "AuraStat{}", "calc": "AuraStatCalc{}"}),
    *make_colgroup(range_1(6), "__PassiveStat{}", {"stat": "PassiveStat{}", "calc": "PassiveCalc{}"}),
    *make_colgroup(range_1(3), "__AuraEvent{}", {"event": "AuraEvent{}", "func": "AuraEventFunc{}"}),
    ("__AuraTargetEvent", {"event": "AuraTgtEvent", "func": "AuraTgtEventFunc"}),
    ("__PassiveEvent", {"event": "PassiveEvent", "func": "PassiveEventFunc"}),
    *make_colgroup(range_1(8), "__Param{}", {"param": "Param{}", "desc": "*Param{} Description"}),
    ("--MinDam0-5", ("MinDam", "MinLevDam1", "MinLevDam2", "MinLevDam3", "MinLevDam4", "MinLevDam5")),
    ("--MaxDam0-5", ("MaxDam", "MaxLevDam1", "MaxLevDam2", "MaxLevDam3", "MaxLevDam4", "MaxLevDam5")),
    ("--EMin0-5", ("EMin", "EMinLev1", "EMinLev2", "EMinLev3", "EMinLev4", "EMinLev5")),
    ("--EMax0-5", ("EMax", "EMaxLev1", "EMaxLev2", "EMaxLev3", "EMaxLev4", "EMaxLev5")),
    # ("--ELen0-3", ("ELen", "ELevLen1", "ELevLen2", "ELevLen3")),  # Also in Skills.txt
    ("__Cost", {"multiply": "cost mult", "add": "cost add"}),
    # SkillDesc.txt
    ("__SkillPage", {"page": "SkillPage", "row": "SkillRow", "column": "SkillColumn"}),
    # States.txt
    # ("--Light-RGB", ("Light-R", "Light-G", "Light-B")),  # Also in MonStats2.txt
    # SuperUniques.txt
    # ("--MinMaxGrp", ("MinGrp", "MaxGrp")),  # Also in MonStats.txt
    # ("--uTrans-RNH", ("uTrans", "uTrans(N)", "uTrans(H)")),  # Also in MonStats2.txt
    # TreasureClassEx.txt
    *make_colgroup(range_1(10), "__Item{}", {"code": "Item{}", "prob": "Prob{}"}),
    # UniqueItems.txt
    *make_colgroup(range_1(12), "__Prop{}", {"prop": "Prop{}", "param": "Par{}", "min": "Min{}", "max": "Max{}"}),
    # ("__Cost", {"multiply": "cost mult", "add": "cost add"}),  # Also in Skills.txt
)
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


def get_matched_colgroups(column_names: Iterable[str]) -> List[ColumnGroupDefinition]:
    """Return a list of column groups that match the given column names.

    Args:
        Iterable of column name strings to compare with column group definitions
        in `COLUMN_GROUPS`. Column names are compared case-insensitively.

    Returns:
        List of applicable column group definitions. Each definition's member
        column names are cased correctly to match those in `column_names`
        without calling str.casefold().
    """
    casefold_to_normal = {name.casefold(): name for name in column_names}
    matched_colgroups = []

    for group in COLUMN_GROUPS:
        if group.type == ColumnGroupType.ARRAY:
            names_cf = tuple(map(str.casefold, group.members))
            new_members = (casefold_to_normal[name_cf] for name_cf in names_cf)
        elif group.type == ColumnGroupType.TABLE:
            members_alias_cf = tuple(
                (member_alias, name.casefold()) for member_alias, name in group.members
            )
            names_cf = (name_cf for _, name_cf in members_alias_cf)
            new_members = (
                (member_alias, casefold_to_normal[name_cf])
                for member_alias, name_cf in members_alias_cf
            )
        else:
            raise ValueError(f"Invalid column group definition {group}")

        # Precondition: new_members is a generator, names_cf is a usable iterable
        try:
            new_members = tuple(new_members)
        except KeyError:
            continue
        matched_colgroups.append(group._replace(members=new_members))
        # Remove matched member columns in order to avoid overlapping groups.
        # Example: --MinMaxDam and --MinDam0-5
        for name_cf in names_cf:
            del casefold_to_normal[name_cf]

    return matched_colgroups


def get_sorted_columns_and_groups(
    columns: Sequence[str], colgroups: Iterable[ColumnGroupDefinition]
) -> List[Union[ColumnGroupDefinition, str]]:
    """Builds a sorted list of column names and column groups.

    Args:
        columns: Sequence of column names.
        colgroups: Iterable of usable column group definitions.

    Returns:
        Sorted list containing column names and column group definitions.
    """
    column_to_index = {name: index for index, name in enumerate(columns)}
    # Build an iterable of tuples of (index, column name or colgroup).
    # Each colgroup is given the same index as its firstmost member column.
    indices_and_colgroups = (
        (min(column_to_index[name] for name in group.member_names()), group)
        for group in colgroups
    )
    # Place colgroups before normal columns to take advantage of stable sort,
    # which ensures that a column group always comes before any of its members.
    combined = chain(indices_and_colgroups, enumerate(columns))
    return [t[1] for t in sorted(combined, key=lambda t: t[0])]


def pack_colgroup_array(
    toml_row: Mapping[str, Union[int, str, None]], column_group: ColumnGroupDefinition
) -> Union[List[int], List[str], None]:
    """Tries to pack member column values for `column_group` into a list.

    Args:
        toml_row: Mapping to read the column values from.
        column_group: Column group to pack the data for. Must be an array type.

    Returns:
        On success, returns a list of integers, or a list of strings.
        On failure, returns None.
    """
    member_values = tuple(map(toml_row.get, column_group.member_names()))
    if all(value is None for value in member_values):
        return None
    if all(isinstance(value, int) for value in member_values):
        return member_values
    if sum(1 for value in member_values if value is not None) > 1:
        # Currently, TOML does not support arrays of mixed types. Therefore
        # convert all values to strings.
        return ["" if value is None else str(value) for value in member_values]
    return None


def pack_colgroup_table(
    toml_row: Mapping[str, Union[int, str, None]], column_group: ColumnGroupDefinition
) -> Union[UserDict, None]:
    """Tries to pack member column values for `column_group` into a UserDict.

    Args:
        toml_row: Mapping to read the column values from.
        column_group: Column group to pack the data for. Must be an array type.

    Returns:
        On success, returns a UserDict that maps member aliases to values.
        On failure, returns None.
    """
    member_values = UserDict()
    for member_alias, column_name in column_group.members:
        value = toml_row.get(column_name)
        if value is not None:
            member_values[member_alias] = value
    return member_values if member_values else None


def make_toml_row(
    txt_row: Mapping[str, Any],
    colgroups: Iterable[ColumnGroupDefinition],
    columns_with_colgroups: Iterable[Union[ColumnGroupDefinition, str]],
) -> Dict[str, Any]:
    """Convert a D2TXT row object to a mapping that can be converted to TOML."""
    # Black magic to avoid creating more than one dictionary per row
    toml_row = {}

    # Fill the row dict with colgroups, as well as columns that have value.
    for name_or_colgroup in columns_with_colgroups:
        if isinstance(name_or_colgroup, ColumnGroupDefinition):
            # Column groups are pre-assigned in their correct positions
            # Rely on preservation of insertion order of dicts Python 3.6+
            toml_row[name_or_colgroup.alias] = None
        else:
            value = txt_row[name_or_colgroup]
            if not (value is None or value == ""):
                toml_row[name_or_colgroup] = decode_txt_value(name_or_colgroup, value)

    # Replace member columns if they can be packed into column groups
    for column_group in colgroups:
        if column_group.type == ColumnGroupType.ARRAY:
            packed_values = pack_colgroup_array(toml_row, column_group)
        elif column_group.type == ColumnGroupType.TABLE:
            packed_values = pack_colgroup_table(toml_row, column_group)
        else:
            # Should be unreachable
            raise ValueError(f"Invalid column group definition {column_group}")

        if packed_values is None:
            del toml_row[column_group.alias]
        else:
            toml_row[column_group.alias] = packed_values
            for name in column_group.member_names():
                toml_row.pop(name, None)

    return toml_row


def d2txt_to_toml(d2txt: D2TXT) -> str:
    """Converts a D2TXT object to TOML markup.

    Args:
        d2txt: D2TXT object to convert.

    Returns:
        String containing TOML markup.
    """
    columns = d2txt.column_names()
    colgroups = get_matched_colgroups(columns)
    columns_with_colgroups = get_sorted_columns_and_groups(columns, colgroups)

    toml_rows = [make_toml_row(row, colgroups, columns_with_colgroups) for row in d2txt]

    # Use qtoml.dumps(), because toml does not properly escape backslashes.
    # Possibly related issues:
    #   https://github.com/uiri/toml/issues/261
    #   https://github.com/uiri/toml/issues/201
    toml_encoder = qtoml.encoder.TOMLEncoder()
    # UserDict trick described in https://github.com/pastelmind/d2txt/issues/15
    # This forces qtoml to encode UserDict as inline tables
    toml_encoder.st[UserDict] = toml_encoder.dump_itable

    toml_header = (
        "columns = [\n"
        + "".join(f"  {toml_encoder.dump_value(key)},\n" for key in columns)
        + "]\n\n"
    )

    toml_body_data = {}
    if colgroups:
        toml_body_data["column_groups"] = toml_column_groups = {}
        for column_group in columns_with_colgroups:
            if not isinstance(column_group, ColumnGroupDefinition):
                continue
            elif column_group.type == ColumnGroupType.ARRAY:
                column_group_value = column_group.members
            elif column_group.type == ColumnGroupType.TABLE:
                column_group_value = UserDict(column_group.members)
            else:
                # Should be unreachable
                raise ValueError(f"Invalid column group definition {column_group}")
            toml_column_groups[column_group.alias] = column_group_value
    toml_body_data["rows"] = toml_rows

    toml_body = toml_encoder.dump_sections(toml_body_data, [], False)
    return toml_header + toml_body


def decode_toml_row(
    d2txt_row: D2TXTRow,
    toml_row: Mapping[str, Any],
    column_groups: Mapping[str, Union[Mapping[str, str], Sequence[str]]],
) -> Dict[str, Union[int, str]]:
    """Decodes a TOML row to a normal dictionary."""
    for key, value in toml_row.items():
        try:
            members = column_groups[key]
        except KeyError:
            d2txt_row[key] = encode_txt_value(key, value)
        else:
            # Unpack column groups
            if isinstance(members, collections.abc.Mapping):
                for m_alias, name in members.items():
                    d2txt_row[name] = value[m_alias]
            else:
                for index, name in enumerate(members):
                    d2txt_row[name] = value[index]


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
    column_groups = toml_data.get("column_groups", {})

    for row in toml_data["rows"]:
        d2txt_data.append([])
        decode_toml_row(d2txt_data[-1], row, column_groups)

    return d2txt_data


def grouper(iterable: Iterable, n: int, fillvalue: Any = None) -> Iterator[tuple]:
    """Collect data into fixed-length chunks or blocks.

    Based on the `grouper()` recipe at
        https://docs.python.org/3/library/itertools.html#itertools-recipes
    """
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    # pylint: disable=invalid-name
    args = [iter(iterable)] * n
    # pylint: enable=invalid-name
    return zip_longest(*args, fillvalue=fillvalue)


def main(argv: List[str]) -> None:
    """Entrypoint of the command line script."""
    arg_parser = ArgumentParser()
    arg_subparsers = arg_parser.add_subparsers(dest="command")

    arg_parser_compile = arg_subparsers.add_parser(
        "compile", help="Compile a TOML file to a tabbed TXT file"
    )
    arg_parser_compile.add_argument(
        "source_target",
        help="Pair of source file (TOML) and target file (TXT)",
        metavar="source target",
        nargs="+",
    )

    arg_parser_decompile = arg_subparsers.add_parser(
        "decompile", help="Decompile a tabbed TXT file to a TOML file"
    )
    arg_parser_decompile.add_argument(
        "source_target",
        help="Pair of source file (TXT) and target file (TOML)",
        metavar="source target",
        nargs="+",
    )

    args = arg_parser.parse_args(argv)

    if args.command is None:
        arg_parser.print_help()
    elif args.command == "compile":
        for source, target in grouper(args.source_target, 2):
            if not source:
                raise ValueError(f"Invalid source file {source!r}")
            if not target:
                raise ValueError(f"Missing target for source {source!r}")
            with open(source, encoding="utf-8") as toml_file:
                d2txt_data = toml_to_d2txt(toml_file.read())
            d2txt_data.to_txt(target)
    elif args.command == "decompile":
        for source, target in grouper(args.source_target, 2):
            if not source:
                raise ValueError(f"Invalid source file {source!r}")
            if not target:
                raise ValueError(f"Missing target for source {source!r}")
            d2txt_file = D2TXT.load_txt(source)
            with open(target, mode="w", encoding="utf-8") as toml_file:
                toml_file.write(d2txt_to_toml(d2txt_file))
    else:
        raise ValueError(f"Unexpected command: {args.command!r}")


if __name__ == "__main__":
    main(sys.argv[1:])
