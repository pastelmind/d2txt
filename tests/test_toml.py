#!/usr/bin/env python
"""Unit test for conversion to and from TOML."""

import os
from tempfile import NamedTemporaryFile
import unittest

from d2txt import D2TXT
from d2txt import d2txt_to_toml
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

    @classmethod
    def setUpClass(cls):
        with NamedTemporaryFile(delete=False) as temp_toml:
            cls.temp_toml_path = temp_toml.name

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.temp_toml_path)

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
        """Tests if bitfields are corrected decoded when saved to TOML file."""
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
