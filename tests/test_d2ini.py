#!/usr/bin/env python

"""Unit test for d2ini.py"""


from d2ini import d2txt_to_ini, ini_to_d2txt
from d2txt import D2TXT
import unittest
import os
from os import path
from io import StringIO
from tempfile import NamedTemporaryFile
from tests.test_d2txt import TestD2TXTBase


class TestD2TXTLoadIni(TestD2TXTBase):
    """Contains tests that load D2TXT objects from INI files."""

    def test_file_object_or_path(self):
        """Tests if loading an INI from a file object or a file path produces
        the same results."""

        INI_PATH = path.join(path.dirname(path.abspath(__file__)), 'sample.ini')
        COLUMN_NAMES_EXPECTED = ['Key Name', 'key name', 'key with spaces', '# Hashed key', 'Key : with colon', 'Not ; commented key']
        ROWS_EXPECTED = [
            ['backticks', '`double backticks`', 'value with leading spaces', '  whitespace preserved  ', '`unpaired backtick', 'this value is read'],
            [None, None, None, None, None, None],
            ['keys out of order', '', None, '#hashed value', 'value with: colon', '; value with semicolon'],
            [None, None, None, None, None, None],
            ['section out of order', None, None, None, None, None],
        ]

        d2txt_from_path = ini_to_d2txt(INI_PATH)
        self.compare_D2TXT(d2txt_from_path, COLUMN_NAMES_EXPECTED, ROWS_EXPECTED)

        with open(INI_PATH) as ini_file:
            d2txt_from_file = ini_to_d2txt(ini_file)
        self.compare_D2TXT(d2txt_from_file, COLUMN_NAMES_EXPECTED, ROWS_EXPECTED)

    def test_missing_column_name(self):
        """Tests if a key that is not specified in the [Columns] section raises
        an exception."""

        ini_source = (
            '[Columns]\ncolumn 1=\n\n'
            '[1]\ncolumn 1=value\ncolumn 2=value\n\n'
        )

        ini_file = StringIO(ini_source)
        with self.assertRaises(KeyError):
            ini_to_d2txt(ini_file)

    def test_multiline_value(self):
        """Tests if a multiline value in an INI file raises an exception."""
        ini_source = (
            '[Columns]\ncolumn 1=\ncolumn 2=\n\n'
            '[1]\ncolumn 1=value\n  column 2=value\n\n'
        )

        ini_file = StringIO(ini_source)
        with self.assertRaises(ValueError):
            ini_to_d2txt(ini_file)

    def test_multiline_value_in_columns(self):
        """Tests if a multiline value in the Columns section of an INI file
        raises an exception."""
        ini_source = (
            '[Columns]\ncolumn 1=\n  column 2=\n\n'
            '[1]\ncolumn 1=value\n\n'
        )

        ini_file = StringIO(ini_source)
        with self.assertRaises(ValueError):
            ini_to_d2txt(ini_file)

    def test_key_case_preserved(self):
        """Tests if keys are case-preserved when loaded from an INI file."""
        d2txt = ini_to_d2txt(StringIO(
            '[Columns]\ncolumn name=\nColumn Name=\nCOLUMN NAME=\n\n'
            '[1]\ncolumn name=lower\nColumn Name=Caps\nCOLUMN NAME=UPPER\n\n'
        ))

        self.compare_D2TXT(
            d2txt, ['column name', 'Column Name', 'COLUMN NAME'],
            [['lower', 'Caps', 'UPPER']]
        )

    def test_surrounding_whitespace(self):
        """Tests if whitespace around INI keys and values are ignored."""
        d2txt = ini_to_d2txt(StringIO(
            '[Columns]\n  leading spaces=\ntrailing spaces   =\n\n'
            '[1]\n  leading spaces=  1\ntrailing spaces   =2  \n\n'
        ))

        self.compare_D2TXT(
            d2txt, ['leading spaces', 'trailing spaces'],
            [['1', '2']]
        )

    def test_empty_keys_and_values(self):
        """Tests if empty or omitted INI keys/values are loaded correctly."""
        d2txt = ini_to_d2txt(StringIO(
            '[Columns]\nKey with empty value=\nEmpty key\nOmitted key=\n\n'
            '[1]\nKey with empty value\nEmpty key=\n\n'
        ))

        self.compare_D2TXT(
            d2txt, ['Key with empty value', 'Empty key', 'Omitted key'],
            [[None, '', None]]
        )

    def test_backtick_pairs_removed(self):
        """Tests if INI keys and values are un-backtick-ified when loaded."""
        d2txt = ini_to_d2txt(StringIO(
            '[Columns]\n'
            '``backticks``=\n'
            '```double```=\n'
            '``=\n'
            '`  whitespace  `=\n'
            '`unpaired=\n'
            'in`ter`nal=\n\n'
            '[1]\n'
            '``backticks``=``backticks``\n'
            '```double```=```double```\n'
            '``=``\n'
            '`  whitespace  `=`  whitespace  `\n'
            '`unpaired=`unpaired\n'
            'in`ter`nal=in`ter`nal\n\n'
        ))

        self.compare_D2TXT(
            d2txt, ['`backticks`', '``double``', '',  '  whitespace  ', '`unpaired', 'in`ter`nal'],
            [['`backticks`', '``double``', '',  '  whitespace  ', '`unpaired', 'in`ter`nal']]
        )

    def test_hash_signs_allowed(self):
        """Tests if hash signs (#) in keys and values are loaded normally."""
        d2txt = ini_to_d2txt(StringIO(
            '[Columns]\n#at key start=\nin#key#middle=\n\n'
            '[1]\n#at key start=#at value start\nin#key#middle=in#value#middle\n\n'
        ))

        self.compare_D2TXT(
            d2txt, ['#at key start', 'in#key#middle'],
            [['#at value start', 'in#value#middle']]
        )

    def test_colons_allowed(self):
        """Tests if colons (:) in keys and values are loaded normally."""
        d2txt = ini_to_d2txt(StringIO(
            '[Columns]\n:at key start=\nin:key:middle=\n\n'
            '[1]\n:at key start=:at value start\nin:key:middle=in:value:middle\n\n'
        ))

        self.compare_D2TXT(
            d2txt, [':at key start', 'in:key:middle'],
            [[':at value start', 'in:value:middle']]
        )

    def test_semicolons_allowed(self):
        """Tests if semicolons (;) in keys and values are loaded appropriately.

        Semicolons (;) are allowed in keys and values, except as the first non-
        whitespace character of a line (which marks a comment). Column names
        with leading semicolons must be wrapped in backticks when loading/saving
        an INI file.
        """
        d2txt = ini_to_d2txt(StringIO(
            '[Columns]\n`;at key start`=\nin;key;middle=\n\n'
            '[1]\n`;at key start`=;at value start\nin;key;middle=in;value;middle\n\n'
            '[2]\n;at key start=comment line\n;in;key;middle=comment line\n\n'
        ))

        self.compare_D2TXT(
            d2txt, [';at key start', 'in;key;middle'],
            [[';at value start', 'in;value;middle'], [None, None]]
        )

    def test_equal_sign_unescaped(self):
        """Tests if equal signs (=) in keys (but not values) are unescaped.

        Keys cannot have equal signs, because they are used as delimiters
        between keys and values. Equal signs in column names must be escaped
        (replaced with `${eq}`) when loading/saving an INI file.
        """
        d2txt = ini_to_d2txt(StringIO(
            '[Columns]\n${eq}leading equals=\nequals${eq}in${eq}middle=\n\n'
            '[1]\n'
            '${eq}leading equals==leading equals\n'
            'equals${eq}in${eq}middle=equals=in=middle\n\n'
            '[2]\n'
            '${eq}leading equals=${eq}not escaped\n'
            'equals${eq}in${eq}middle=not${eq}escaped${eq}\n\n'
        ))

        self.compare_D2TXT(
            d2txt, ['=leading equals', 'equals=in=middle'],
            [
                ['=leading equals', 'equals=in=middle'],
                ['${eq}not escaped', 'not${eq}escaped${eq}'],
            ]
        )

    def test_bitfield_encode(self):
        """Tests if bitfields are correctly encoded when loading an INI file."""
        d2txt = ini_to_d2txt(StringIO(
            '[Columns]\naurafilter=\n\n'
            '[1]\naurafilter=FindPlayers | NotInsideTowns | IgnoreAllies\n\n'
            '[2]\naurafilter=33025\n\n'
            '[3]\naurafilter=0x1 | 0x100 | 0x400\n\n'
        ))

        self.compare_D2TXT(
            d2txt, ['aurafilter'],
            [['33025'], ['33025'], ['1281']]
        )

    def test_invalid_bitfield(self):
        """Tests if an invalid bitfield string raises an exception."""
        ini_file = StringIO(
            '[Columns]\naurafilter=\n\n'
            '[1]\naurafilter=FindPlayers | BadName | IgnoreAllies\n\n'
        )
        with self.assertRaises(ValueError):
            ini_to_d2txt(ini_file)


class TestD2TXTSaveIni(unittest.TestCase):
    """Contains tests that convert D2TXT objects to INI files."""

    @classmethod
    def setUpClass(cls):
        with NamedTemporaryFile(delete=False) as temp_ini:
            cls.temp_ini_path = temp_ini.name

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.temp_ini_path)

    def test_save_to_file_object(self):
        """Tests if saving to a file object and a file path produce the same
        results."""

        txt_source = [
            ['id', 'Name', 'Full Name'],
            ['0', 'John', 'John Doe'],
            ['1', 'Mary', 'Mary Gold'],
            ['2', 'Foo', 'Foo Bar'],
        ]
        ini_expected = (
            '[Columns]\nid\nName\nFull Name\n\n'
            '[1]\nid = 0\nName = John\nFull Name = John Doe\n\n'
            '[2]\nid = 1\nName = Mary\nFull Name = Mary Gold\n\n'
            '[3]\nid = 2\nName = Foo\nFull Name = Foo Bar\n\n'
        )

        d2txt = D2TXT(txt_source[0])
        d2txt.extend(txt_source[1:])

        temp_ini_file = StringIO()
        temp_ini_path = self.__class__.temp_ini_path

        d2txt_to_ini(d2txt, temp_ini_file)
        d2txt_to_ini(d2txt, temp_ini_path)

        self.assertEqual(temp_ini_file.getvalue(), ini_expected)
        with open(temp_ini_path) as temp_ini:
            self.assertEqual(temp_ini.read(), ini_expected)

    def test_surrounding_whitespace(self):
        """Tests if whitespace around columns and values are backtickified."""
        d2txt = D2TXT(['   before', 'after  ', '  around  ', ' '])
        d2txt.extend([['   before', 'after  ', '  around  ', ' ']])

        ini_file = StringIO()
        d2txt_to_ini(d2txt, ini_file)
        self.assertEqual(
            ini_file.getvalue(),
            '[Columns]\n`   before`\n`after  `\n`  around  `\n` `\n\n'
            '[1]\n'
            '`   before` = `   before`\n'
            '`after  ` = `after  `\n'
            '`  around  ` = `  around  `\n'
            '` ` = ` `\n\n'
        )

    def test_empty_column_name(self):
        """Tests if an empty column name is backtickified when saved to INI."""
        d2txt = D2TXT([''])
        d2txt.extend([['1']])

        ini_file = StringIO()
        d2txt_to_ini(d2txt, ini_file)
        self.assertEqual(
            ini_file.getvalue(),
            '[Columns]\n``\n\n[1]\n`` = 1\n\n'
        )

    def test_surrounding_backticks(self):
        """Tests if backtickified columns and values are backtickified again.

        Columns and values with unpaired or internal backticks are not
        backtickified.
        """
        d2txt = D2TXT(['`backticks`', '``double``', '`unpaired', 'in`ter`nal'])
        d2txt.extend([['`backticks`', '``double``', '`unpaired', 'in`ter`nal']])

        ini_file = StringIO()
        d2txt_to_ini(d2txt, ini_file)
        self.assertEqual(
            ini_file.getvalue(),
            '[Columns]\n``backticks``\n```double```\n`unpaired\nin`ter`nal\n\n'
            '[1]\n'
            '``backticks`` = ``backticks``\n'
            '```double``` = ```double```\n'
            '`unpaired = `unpaired\n'
            'in`ter`nal = in`ter`nal\n\n'
        )

    def test_column_name_leading_semicolon(self):
        """Tests if a column with a leading semicolon is backtickfied.

        This prevents the column name from being interpreted as a comment.
        """
        d2txt = D2TXT([';at key start', 'in;key;middle'])
        d2txt.extend([[';at value start', 'in;value;middle']])

        ini_file = StringIO()
        d2txt_to_ini(d2txt, ini_file)
        self.assertEqual(
            ini_file.getvalue(),
            '[Columns]\n`;at key start`\nin;key;middle\n\n'
            '[1]\n'
            '`;at key start` = ;at value start\n'
            'in;key;middle = in;value;middle\n\n'
        )

    def test_equal_sign_escaped(self):
        """Tests if equal signs (=) in column names (not values) are escaped."""
        d2txt = D2TXT(['=at key start', 'in=key=middle'])
        d2txt.extend([['=at value start', 'in=value=middle']])

        ini_file = StringIO()
        d2txt_to_ini(d2txt, ini_file)
        self.assertEqual(
            ini_file.getvalue(),
            '[Columns]\n${eq}at key start\nin${eq}key${eq}middle\n\n'
            '[1]\n'
            '${eq}at key start = =at value start\n'
            'in${eq}key${eq}middle = in=value=middle\n\n'
        )

    def test_falsy_value_ignored(self):
        """Tests if falsy values are ignored when saving to an INI file."""
        d2txt = D2TXT(['int 0', 'float 0.0', 'False', 'None'])
        d2txt.extend([[0, 0.0, False, None]])

        ini_file = StringIO()
        d2txt_to_ini(d2txt, ini_file)
        self.assertEqual(
            ini_file.getvalue(),
            '[Columns]\nint 0\nfloat 0.0\nFalse\nNone\n\n[1]\n\n'
        )

    def test_bitfield_decode(self):
        """Tests if bitfields are corrected decoded when saved to INI file."""
        d2txt = D2TXT(['aurafilter'])
        d2txt.extend([['33025'], ['0'], ['65535'], ['4294901760']])

        ini_file = StringIO()
        d2txt_to_ini(d2txt, ini_file)
        self.assertEqual(
            ini_file.getvalue(),
            '[Columns]\naurafilter\n\n'
            '[1]\naurafilter = FindPlayers | NotInsideTowns | IgnoreAllies\n\n'
            '[2]\naurafilter = 0\n\n'
            '[3]\naurafilter = FindPlayers | FindMonsters | FindOnlyUndead | FindMissiles | FindObjects | FindItems | 0x40 | FindAttackable | NotInsideTowns | UseLineOfSight | FindSelectable | 0x800 | FindCorpses | NotInsideTowns2 | IgnoreBoss | IgnoreAllies\n\n'
            '[4]\naurafilter = IgnoreNPC | Unknown20000 | IgnorePrimeEvil | IgnoreJustHitUnits | 0x100000 | 0x200000 | 0x400000 | 0x800000 | 0x1000000 | 0x2000000 | 0x4000000 | 0x8000000 | 0x10000000 | 0x20000000 | 0x40000000 | 0x80000000\n\n'
        )