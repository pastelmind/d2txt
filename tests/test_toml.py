#!/usr/bin/env python
"""Unit test for conversion to and from TOML."""

import collections
import unittest

from d2txt import COLUMN_GROUPS
from d2txt import D2TXT
from d2txt import d2txt_to_toml
from d2txt import initialize_column_groups
from d2txt import toml_to_d2txt
from tests.test_d2txt import TestD2TXTBase


class TestD2TXTLoadToml(TestD2TXTBase):
    """Contains tests that load D2TXT objects from TOML files."""

    def test_missing_column_name(self):
        """Tests if a key that is not specified in the [Columns] section raises
        an exception."""

        toml_source = "columns=['column1']\n\n" "[[rows]]\ncolumn1=1\ncolumn2=2\n\n"

        with self.assertRaises(KeyError):
            toml_to_d2txt(toml_source)

    def test_multiline_value_in_columns(self):
        """Tests if a multiline value in the `columns` section of an TOML file
        raises an exception."""
        with self.assertRaises(ValueError):
            toml_to_d2txt(
                "columns=['''column1\nmultiline''', 'column2']\n\n"
                "[[rows]]'''column1\nmultiline'''=1\ncolumn2=2\n\n"
            )

    def test_key_case_preserved(self):
        """Tests if keys are case-preserved when loaded from an TOML file."""
        d2txt = toml_to_d2txt(
            "columns=['column', 'Column', 'COLUMN']\n\n"
            "[[rows]]\ncolumn='lower'\nColumn='Caps'\nCOLUMN='UPPER'\n\n"
        )

        self.compare_d2txt(
            d2txt, ["column", "Column", "COLUMN"], [["lower", "Caps", "UPPER"]]
        )

    def test_bitfield_encode(self):
        """Tests if bitfields are correctly encoded when loading an TOML file."""
        d2txt = toml_to_d2txt(
            "columns=['aurafilter']\n\n"
            "[[rows]]\naurafilter=[['FindPlayers', 'NotInsideTowns', 'IgnoreAllies']]\n\n"
            "[[rows]]\naurafilter=33025\n\n"
            "[[rows]]\naurafilter=[[], [0x501]]\n\n"
        )

        self.compare_d2txt(d2txt, ["aurafilter"], [[33025], [33025], [1281]])

    def test_invalid_bitfield(self):
        """Tests if an invalid bitfield string raises an exception."""
        with self.assertRaises(ValueError):
            toml_to_d2txt(
                "columns=['aurafilter']\n\n"
                "[[rows]]\naurafilter=[['FindPlayers', 'BadName']]\n\n"
            )


class TestD2TXTSaveToml(unittest.TestCase):
    """Contains tests that convert D2TXT objects to TOML files."""

    def test_none_or_empty_string_ignored(self):
        """Tests if None or '' is ignored, but other falsy values are not."""
        d2txt = D2TXT(["int 0", "float 0.0", "False", "None", "empty"])
        d2txt.extend([[0, 0.0, False, None, ""]])

        self.assertEqual(
            d2txt_to_toml(d2txt),
            "columns = [\n  'int 0',\n  'float 0.0',\n  'False',\n  'None',\n  'empty',\n]\n\n"
            "[[rows]]\n'int 0' = 0\n'float 0.0' = 0.0\nFalse = false\n\n",
        )

    def test_bitfield_decode(self):
        """Tests if bitfields are correctly decoded when saved to TOML file."""
        d2txt = D2TXT(["aurafilter"])
        d2txt.extend([["33025"], ["0"], ["65535"], ["4294901760"]])

        self.maxDiff = None  # pylint: disable=invalid-name
        self.assertEqual(
            d2txt_to_toml(d2txt),
            "columns = [\n  'aurafilter',\n]\n\n"
            "[[rows]]\naurafilter = [['FindPlayers', 'NotInsideTowns', 'IgnoreAllies']]\n\n"
            "[[rows]]\naurafilter = [[]]\n\n"
            "[[rows]]\naurafilter = "
            "[['FindPlayers', 'FindMonsters', 'FindOnlyUndead', 'FindMissiles', "
            "'FindObjects', 'FindItems', 'FindAttackable', 'NotInsideTowns', "
            "'UseLineOfSight', 'FindSelectable', 'FindCorpses', 'NotInsideTowns2', "
            "'IgnoreBoss', 'IgnoreAllies'], [0x840]]\n\n"
            "[[rows]]\naurafilter = "
            "[['IgnoreNPC', 'IgnorePrimeEvil', 'IgnoreJustHitUnits'], [0xFFF20000]]\n\n",
        )


class TestD2TXTColumnGroups(TestD2TXTBase):
    """Contains tests for packing & unpacking column groups."""

    def setUp(self):
        self.old_column_groups = list(COLUMN_GROUPS)
        COLUMN_GROUPS.clear()

    def tearDown(self):
        COLUMN_GROUPS[:] = self.old_column_groups

    def test_array_group_pack(self):
        """Tests if columns belonging to an array group are properly packed."""
        COLUMN_GROUPS.extend(
            initialize_column_groups(
                ("--ArrayGroup", ("column 2", "column 1", "COLUMN 4"))
            )
        )
        d2txt = D2TXT(["column 1", "column 2", "column 3", "column 4"])
        d2txt.extend([["foo", "bar", 225, 45]])

        self.assertEqual(
            d2txt_to_toml(d2txt),
            "columns = [\n"
            "  'column 1',\n  'column 2',\n  'column 3',\n  'column 4',\n"
            "]\n\n"
            "[column_groups]\n"
            "--ArrayGroup = ['column 2', 'column 1', 'column 4']\n\n"
            "[[rows]]\n"
            "--ArrayGroup = ['bar', 'foo', '45']\n"
            "'column 3' = 225\n\n",
        )

    def test_array_group_unpack(self):
        """Tests if columns belonging to an array group are properly unpacked."""
        COLUMN_GROUPS.extend(
            initialize_column_groups(
                ("--ArrayGroup", ("column 2", "column 1", "COLUMN 4"))
            )
        )
        d2txt = toml_to_d2txt(
            "columns = [\n"
            "  'column 1',\n  'column 2',\n  'column 3',\n  'column 4',\n"
            "]\n\n"
            "[column_groups]\n"
            "--ArrayGroup = ['column 2', 'column 1', 'column 4']\n\n"
            "[[rows]]\n"
            "--ArrayGroup = ['bar', 'foo', '45']\n"
            "'column 3' = 225\n\n",
        )

        self.compare_d2txt(
            d2txt,
            ["column 1", "column 2", "column 3", "column 4"],
            [["foo", "bar", 225, "45"]],
        )

    def test_table_group_pack(self):
        """Tests if columns belonging to a table group are properly packed."""
        COLUMN_GROUPS.extend(
            initialize_column_groups(
                (
                    "__TableGroup",
                    {"col2": "column 2", "col 1": "column 1", "col4": "COLUMN 4"},
                )
            )
        )
        d2txt = D2TXT(["column 1", "column 2", "column 3", "column 4"])
        d2txt.extend([["foo", "bar", 225, 45]])

        self.assertEqual(
            d2txt_to_toml(d2txt),
            "columns = [\n"
            "  'column 1',\n  'column 2',\n  'column 3',\n  'column 4',\n"
            "]\n\n"
            "[column_groups]\n"
            "__TableGroup = { col2 = 'column 2', 'col 1' = 'column 1', col4 = 'column 4' }\n\n"
            "[[rows]]\n"
            "__TableGroup = { col2 = 'bar', 'col 1' = 'foo', col4 = 45 }\n"
            "'column 3' = 225\n\n",
        )

    def test_table_group_unpack(self):
        """Tests if columns belonging to a table group are properly unpacked."""
        COLUMN_GROUPS.extend(
            initialize_column_groups(
                (
                    "__TableGroup",
                    {"col2": "column 2", "col 1": "column 1", "col4": "COLUMN 4"},
                )
            )
        )
        d2txt = toml_to_d2txt(
            "columns = [\n"
            "  'column 1',\n  'column 2',\n  'column 3',\n  'column 4',\n"
            "]\n\n"
            "[column_groups]\n"
            "__TableGroup = { col2 = 'column 2', 'col 1' = 'column 1', col4 = 'column 4' }\n\n"
            "[[rows]]\n"
            "__TableGroup = { col2 = 'bar', 'col 1' = 'foo', col4 = 45 }\n"
            "'column 3' = 225\n\n"
        )

        self.compare_d2txt(
            d2txt,
            ["column 1", "column 2", "column 3", "column 4"],
            [["foo", "bar", 225, 45]],
        )

    def test_nested_group_pack(self):
        """Tests if columns in multilevel groups are properly packed."""
        COLUMN_GROUPS.extend(
            initialize_column_groups(
                [
                    "--ArrayOfTables",
                    [
                        {"min": "RedMin", "max": "RedMax"},
                        {"min": "BlueMin", "max": "BlueMax"},
                    ],
                ],
                ["__TableOfArrays", {"weight": ["Weight1", "Weight2", "Weight3"]}],
            )
        )
        d2txt = D2TXT(
            [
                "RedMin",
                "BlueMin",
                "RedMax",
                "BlueMax",
                "Weight2",
                "Weight3",
                "Weight1",
                "Misc",
            ]
        )
        d2txt.extend([[10, 20, "unknown", 100, 0, 500, 1000, 4]])

        self.assertEqual(
            d2txt_to_toml(d2txt),
            "columns = [\n"
            "  'RedMin',\n  'BlueMin',\n  'RedMax',\n  'BlueMax',\n"
            "  'Weight2',\n  'Weight3',\n  'Weight1',\n  'Misc',\n"
            "]\n\n"
            "[column_groups]\n"
            "--ArrayOfTables = ["
            "{ min = 'RedMin', max = 'RedMax' }, { min = 'BlueMin', max = 'BlueMax' }"
            "]\n"
            "__TableOfArrays = { weight = ['Weight1', 'Weight2', 'Weight3'] }\n\n"
            "[[rows]]\n"
            "--ArrayOfTables = [{ min = 10, max = 'unknown' }, { min = 20, max = 100 }]\n"
            "__TableOfArrays = { weight = [1000, 0, 500] }\n"
            "Misc = 4\n\n",
        )

    def test_nested_group_unpack(self):
        """Tests if columns in multilevel groups are properly unpacked."""
        COLUMN_GROUPS.extend(
            initialize_column_groups(
                [
                    "--ArrayOfTables",
                    [
                        {"min": "RedMin", "max": "RedMax"},
                        {"min": "BlueMin", "max": "BlueMax"},
                    ],
                ],
                ["__TableOfArrays", {"weight": ["Weight1", "Weight2", "Weight3"]}],
            )
        )
        d2txt = toml_to_d2txt(
            "columns = [\n"
            "  'RedMin',\n  'BlueMin',\n  'RedMax',\n  'BlueMax',\n"
            "  'Weight2',\n  'Weight3',\n  'Weight1',\n  'Misc',\n"
            "]\n\n"
            "[column_groups]\n"
            "--ArrayOfTables = ["
            "{ min = 'RedMin', max = 'RedMax' }, { min = 'BlueMin', max = 'BlueMax' }"
            "]\n"
            "__TableOfArrays = { weight = ['Weight1', 'Weight2', 'Weight3'] }\n\n"
            "[[rows]]\n"
            "--ArrayOfTables = [{ min = 10, max = 'unknown' }, { min = 20, max = 100 }]\n"
            "__TableOfArrays = { weight = [1000, 0, 500] }\n"
            "Misc = 4\n\n"
        )

        self.compare_d2txt(
            d2txt,
            [
                "RedMin",
                "BlueMin",
                "RedMax",
                "BlueMax",
                "Weight2",
                "Weight3",
                "Weight1",
                "Misc",
            ],
            [[10, 20, "unknown", 100, 0, 500, 1000, 4]],
        )


class TestD2TXTColumnGroupValidators(unittest.TestCase):
    """Contains validators for column group definitions in COLUMN_GROUPS."""

    def test_alias_format(self):
        """Tests if column group aliases have consistent names."""
        for group in COLUMN_GROUPS:
            if isinstance(group.schema, collections.abc.Mapping):
                self.assertRegex(group.alias, r"^__\w")
            else:
                self.assertRegex(group.alias, r"^--\w")

    def test_column_group_non_empty(self):
        """Tests if column groups have at least two member columns."""
        for group in COLUMN_GROUPS:
            # Make an exception for CltMissileD in Skills.txt
            if group.alias == "__MissileD":
                continue
            self.assertGreaterEqual(
                sum(1 for _ in group.member_names()),
                2,
                f"Column group {group!r} does not have enough member columns",
            )

    def test_column_group_sorted(self):
        """Tests if column groups are properly sorted by # of member columns."""
        groups = iter(COLUMN_GROUPS)
        group1 = next(groups)
        for group2 in groups:
            self.assertGreaterEqual(
                sum(1 for _ in group1.member_names()),
                sum(1 for _ in group2.member_names()),
                f"Column group {group1!r} appears before {group2!r}.",
            )
            group2 = group1

    def test_column_group_unique_columns(self):
        """Tests if column groups do not have duplicate member columns."""
        for colgroup in COLUMN_GROUPS:
            with self.subTest(colgroup=colgroup):
                member_names = tuple(map(str.casefold, colgroup.member_names()))
                self.assertEqual(
                    len(member_names),
                    len(set(member_names)),
                    "Member column names in a column group must be unique",
                )

    def test_column_group_unique(self):
        """Tests if column group definitions have unique sets of column names."""
        self.longMessage = False  # pylint:disable=invalid-name
        member_columns_seen = {}
        for colgroup in COLUMN_GROUPS:
            with self.subTest(colgroup=colgroup):
                member_columns_cf = frozenset(
                    map(str.casefold, colgroup.member_names())
                )
                self.assertNotIn(
                    member_columns_cf,
                    member_columns_seen,
                    f"Is shadowed by {member_columns_seen.get(member_columns_cf)!r}",
                )
                member_columns_seen[member_columns_cf] = colgroup
