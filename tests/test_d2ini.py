#!/usr/bin/env python

"""Unit test for d2ini.py"""


from d2ini import d2txt_to_ini, ini_to_d2txt
from d2txt import D2TXT
import unittest
import os
from os import path
from io import StringIO
from tempfile import NamedTemporaryFile


class TestD2TXTLoadIni(unittest.TestCase):
    """Contains tests that load a D2TXT object from an INI file."""

    def test_LoadIniFromObjectAndPath(self):
        """Tests if loading an INI from a file object or a file path produces
        the same results."""

        ini_path = path.join(path.dirname(path.abspath(__file__)), 'sample.ini')
        txt_expected = [
            ['Key Name', 'key name', 'key with spaces', '# Hashed key', 'Key : with colon', 'Not ; commented key'],
            ['backticks', '`double backticks`', 'value with leading spaces', '  whitespace preserved  ', '`unpaired backtick', 'this value is read'],
            [None, None, None, None, None, None],
            ['keys out of order', '', None, '#hashed value', 'value with: colon', '; value with semicolon'],
            [None, None, None, None, None, None],
            ['section out of order', None, None, None, None, None],
        ]

        d2txt_from_path = ini_to_d2txt(ini_path)
        with open(ini_path) as ini_file:
            d2txt_from_file = ini_to_d2txt(ini_file)

        self.assertEqual(len(d2txt_from_path), len(txt_expected) - 1, 'Row count')
        self.assertEqual(list(d2txt_from_path.column_names()), txt_expected[0], 'Column mismatch')
        for row_index, row in enumerate(d2txt_from_path):
            with self.subTest(row_index=row_index):
                self.assertEqual(list(row.values()), txt_expected[row_index + 1])

        self.assertEqual(len(d2txt_from_file), len(txt_expected) - 1, 'Row count')
        self.assertEqual(list(d2txt_from_file.column_names()), txt_expected[0], 'Column mismatch')
        for row_index, row in enumerate(d2txt_from_file):
            with self.subTest(row_index=row_index):
                self.assertEqual(list(row.values()), txt_expected[row_index + 1])

    def test_CheckIfMissingKeyRaisesError(self):
        """Tests if a key that is not specified in the [Columns] section raises
        an exception."""

        ini_source = (
            '[Columns]\ncolumn 1=\n\n'
            '[1]\ncolumn 1=value\ncolumn 2=value\n\n'
        )

        ini_file = StringIO(ini_source)
        with self.assertRaises(KeyError):
            ini_to_d2txt(ini_file)

    def test_CheckIfMultilineValueRaisesError(self):
        """Tests if a multiline value in an INI file raises an exception."""
        ini_source = (
            '[Columns]\ncolumn 1=\ncolumn 2=\n\n'
            '[1]\ncolumn 1=value\n  column 2=value\n\n'
        )

        ini_file = StringIO(ini_source)
        with self.assertRaises(ValueError):
            ini_to_d2txt(ini_file)

    def test_CheckIfMultilineValueInColumnsSectionRaisesError(self):
        """Tests if a multiline value in the Columns section of an INI file
        raises an exception."""
        ini_source = (
            '[Columns]\ncolumn 1=\n  column 2=\n\n'
            '[1]\ncolumn 1=value\n\n'
        )

        ini_file = StringIO(ini_source)
        with self.assertRaises(ValueError):
            ini_to_d2txt(ini_file)


class TestD2TXTSaveIni(unittest.TestCase):
    """Contains tests that convert a D2TXT object to an INI file."""

    @classmethod
    def setUpClass(cls):
        with NamedTemporaryFile(delete=False) as temp_ini:
            cls.temp_ini_path = temp_ini.name

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.temp_ini_path)

    def test_SaveToFileObject(self):
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


# A dummy class that hides abstract test cases from the module-level namespace
# to prevent `unittest` from discovering and running them.
# Original idea from https://stackoverflow.com/a/25695512/9943202
class AbstractTestCases:
    # An ABC test case inherited by other test cases in the "LoadIniAndCheck" family.
    class TestD2TXTLoadIniAndCompareContents(unittest.TestCase):
        """Loads D2TXT from an INI file and tests if its contents match the
        expected values."""

        # A string representing the contents of the INI file to test.
        # Must be redefined by concrete test cases that inherit this class.
        ini_source = NotImplementedError('ini_source')

        # A list-of-lists representation of the expected contents of the D2TXT
        # object loaded from `ini_source`, with the column names in the first
        # child list.
        # Must be redefined by concrete test cases that inherit this class.
        txt_expected = NotImplementedError('txt_expected')

        def test_LoadFileAndCheckContents(self):
            """Loads D2TXT from an INI file and tests if its contents match the
            expected values."""
            txt_expected = self.__class__.txt_expected
            with StringIO(self.__class__.ini_source) as ini_file:
                d2txt = ini_to_d2txt(ini_file)

            self.assertEqual(len(d2txt), len(txt_expected) - 1, 'Row count')
            self.assertEqual(list(d2txt.column_names()), txt_expected[0], 'Column mismatch')
            for row_index, row in enumerate(d2txt):
                with self.subTest(row_index=row_index):
                    self.assertEqual(list(row.values()), txt_expected[row_index + 1])

    # An ABC test case inherited by other test cases in the "SaveIniAndCheck" family.
    class TestD2TXTSaveIniAndCompareContents(unittest.TestCase):
        """Saves D2TXT to an INI file and tests if it matches the expected
        contents."""

        # A list-of-lists representation of the D2TXT object to save to an INI
        # file object, with the column names in the first child list.
        # Must be redefined by concrete test cases that inherit this class.
        txt_source = NotImplementedError('txt_source')

        # A string representing the expected contents of the INI file saved.
        # Must be redefined by concrete test cases that inherit this class.
        ini_expected = NotImplementedError('ini_expected')

        def test_SaveFileAndCheckContents(self):
            """Saves D2TXT to an INI file and tests if it matches the expected
            contents."""
            d2txt = D2TXT(self.__class__.txt_source[0])
            d2txt.extend(self.__class__.txt_source[1:])

            ini_file = StringIO()
            d2txt_to_ini(d2txt, ini_file)

            self.assertEqual(ini_file.getvalue(), self.__class__.ini_expected)


class TestD2TXTLoadIniAndCheckKeyIsCaseSensitive(AbstractTestCases.TestD2TXTLoadIniAndCompareContents):
    """Tests if keys are treated case sensitively when loading an INI file."""

    ini_source = (
        '[Columns]\ncolumn name=\nColumn Name=\nCOLUMN NAME=\n\n'
        '[1]\ncolumn name=lowercase\nColumn Name=Capitalized\nCOLUMN NAME=UPPERCASE\n\n'
    )
    txt_expected = [
        ['column name', 'Column Name', 'COLUMN NAME'],
        ['lowercase', 'Capitalized', 'UPPERCASE'],
    ]

class TestD2TXTLoadIniAndCheckIfWhitespaceIsStripped(AbstractTestCases.TestD2TXTLoadIniAndCompareContents):
    """Tests if leading/trailing whitespace is stripped from keys and values
    when loading an INI file."""

    ini_source = (
        '[Columns]\n  leading spaces=\ntrailing spaces   =\n\n'
        '[1]\n  leading spaces=  1\ntrailing spaces   =2\n\n'
    )
    txt_expected = [
        ['leading spaces', 'trailing spaces'],
        ['1', '2'],
    ]

class TestD2TXTLoadIniAndCheckEmptyOrOmittedKeys(AbstractTestCases.TestD2TXTLoadIniAndCompareContents):
    """Tests if empty keys, empty values, or omitted keys are set to None or an
    empty string when loading an INI file."""

    ini_source = (
        '[Columns]\nKey with empty value=\nEmpty key\nOmitted key=\n\n'
        '[1]\nKey with empty value\nEmpty key=\n\n'
    )
    txt_expected = [
        ['Key with empty value', 'Empty key', 'Omitted key'],
        [None, '', None],
    ]

class TestD2TXTLoadIniAndCheckIfUnbacktickfied(AbstractTestCases.TestD2TXTLoadIniAndCompareContents):
    """Tests if keys and values surrounded in backticks are unbacktickified when
    loading an INI file."""

    ini_source = (
        '[Columns]\n``=\n`  whitespace preserved  `=\n``backticks``=\n```double backticks```=\n`unpaired backtick=\ninternal `backticks`=\n\n'
        '[1]\n'
        '``=``\n'
        '`  whitespace preserved  `=`  whitespace preserved  `\n'
        '``backticks``=``backticks``\n'
        '```double backticks```=```double backticks```\n'
        '`unpaired backtick=`unpaired backtick\n'
        'internal `backticks`=internal `backticks`\n\n'
    )
    txt_expected = [
        ['', '  whitespace preserved  ', '`backticks`', '``double backticks``', '`unpaired backtick', 'internal `backticks`'],
        ['', '  whitespace preserved  ', '`backticks`', '``double backticks``', '`unpaired backtick', 'internal `backticks`'],
    ]

class TestD2TXTLoadIniAndCheckIfHashSignsAllowed(AbstractTestCases.TestD2TXTLoadIniAndCompareContents):
    """Tests if hash signs are treated as normal characters when loading an INI
    file."""

    ini_source = (
        '[Columns]\n#hash in key start=\nhashes#in#key#middle=\n\n'
        '[1]\n#hash in key start=#hash in value start\nhashes#in#key#middle=hashes#in#value#middle\n\n'
    )
    txt_expected = [
        ['#hash in key start', 'hashes#in#key#middle'],
        ['#hash in value start', 'hashes#in#value#middle'],
    ]

class TestD2TXTLoadIniAndCheckIfColonsAllowed(AbstractTestCases.TestD2TXTLoadIniAndCompareContents):
    """Tests if colons are treated as normal characters when loading an INI
    file."""

    ini_source = (
        '[Columns]\n:colon in key start=\ncolons:in:key:middle=\n\n'
        '[1]\n:colon in key start=:colon in value start\ncolons:in:key:middle=colons:in:value:middle\n\n'
    )
    txt_expected = [
        [':colon in key start', 'colons:in:key:middle'],
        [':colon in value start', 'colons:in:value:middle'],
    ]

class TestD2TXTLoadIniAndCheckIfSemicolonsAllowed(AbstractTestCases.TestD2TXTLoadIniAndCompareContents):
    """Tests if semicolons are correctly interpreted when loading an INI file.

    Semicolons (;) are allowed in keys and values, except as the first
    non-whitespace character of a line (which marks a comment)."""

    ini_source = (
        '[Columns]\n`;semicolon in key start`=\nsemicolon;in;key;middle=\n\n'
        '[1]\n`;semicolon in key start`=;semicolon in value start\nsemicolon;in;key;middle=semicolon;in;value;middle\n\n'
        '[2]\n;`;semicolon in key start`=;commented line\n;semicolon;in;key;middle=commented line\n\n'
    )
    txt_expected = [
        [';semicolon in key start', 'semicolon;in;key;middle'],
        [';semicolon in value start', 'semicolon;in;value;middle'],
        [None, None],
    ]

class TestD2TXTLoadIniAndCheckIfEqualSignsAreUnescaped(AbstractTestCases.TestD2TXTLoadIniAndCompareContents):
    """Tests if equal signs (=) in keys (but not values) are unescaped."""

    ini_source = (
        '[Columns]\n${eq}leading equals=\nequals${eq}in${eq}middle=\n\n'
        '[1]\n'
        '${eq}leading equals==leading equals\n'
        'equals${eq}in${eq}middle=equals=in=middle\n\n'
        '[2]\n'
        '${eq}leading equals=${eq}leading equals\n'
        'equals${eq}in${eq}middle=equals${eq}in${eq}middle\n\n'
    )
    txt_expected = [
        ['=leading equals', 'equals=in=middle'],
        ['=leading equals', 'equals=in=middle'],
        ['${eq}leading equals', 'equals${eq}in${eq}middle'],
    ]

class TestD2TXTLoadIniAndCheckBitFieldEncoded(AbstractTestCases.TestD2TXTLoadIniAndCompareContents):
    """Tests if bitfields are correctly encoded when loading an INI file."""

    ini_source = (
        '[Columns]\naurafilter=\n\n'
        '[1]\naurafilter=FindPlayers | NotInsideTowns | IgnoreAllies\n\n'
        '[2]\naurafilter=33025\n\n'
        '[3]\naurafilter=0x1 | 0x100 | 0x400\n\n'
    )
    txt_expected = [['aurafilter'], ['33025'], ['33025'], ['1281']]

    def test_InvalidBitFieldRaiseError(self):
        """Tests if an invalid bitfield string raises an error."""
        ini_source = (
            '[Columns]\naurafilter=\n\n'
            '[1]\naurafilter=FindPlayers | BadName | IgnoreAllies\n\n'
        )

        ini_file = StringIO(ini_source)
        with self.assertRaises(ValueError):
            ini_to_d2txt(ini_file)


class TestD2TXTSaveIniAndCheckIfWhitespaceBacktickified(AbstractTestCases.TestD2TXTSaveIniAndCompareContents):
    """Tests if columns and cells with leading/trailing whitespace are
    surrounded with backticks when saved to an INI file."""

    txt_source = [
        ['   leading spaces', 'trailing spaces  ', '  surrounding spaces  ', ' '],
        ['   leading spaces', 'trailing spaces  ', '  surrounding spaces  ', ' '],
    ]
    ini_expected = (
        '[Columns]\n`   leading spaces`\n`trailing spaces  `\n`  surrounding spaces  `\n` `\n\n'
        '[1]\n'
        '`   leading spaces` = `   leading spaces`\n'
        '`trailing spaces  ` = `trailing spaces  `\n'
        '`  surrounding spaces  ` = `  surrounding spaces  `\n'
        '` ` = ` `\n\n'
    )

class TestD2TXTSaveIniAndCheckIfEmptyColumnNameBacktickified(AbstractTestCases.TestD2TXTSaveIniAndCompareContents):
    """Tests if an empty column name is surrounded with backticks when saved to
    an INI file."""

    txt_source = [[''], ['1']]
    ini_expected = '[Columns]\n``\n\n[1]\n`` = 1\n\n'

class TestD2TXTSaveIniAndCheckIfBackticksAreBacktickified(AbstractTestCases.TestD2TXTSaveIniAndCompareContents):
    """Tests if columns and cells with surrounding backticks (but not unpaired
    or internal backticks) are surrounded with backticks when saved to an INI
    file."""

    txt_source = [
        ['`backticks`', '``double backticks``', '`unpaired backtick', 'internal `backticks`'],
        ['`backticks`', '``double backticks``', '`unpaired backtick', 'internal `backticks`'],
    ]
    ini_expected = (
        '[Columns]\n``backticks``\n```double backticks```\n`unpaired backtick\ninternal `backticks`\n\n'
        '[1]\n'
        '``backticks`` = ``backticks``\n'
        '```double backticks``` = ```double backticks```\n'
        '`unpaired backtick = `unpaired backtick\n'
        'internal `backticks` = internal `backticks`\n\n'
    )

class TestD2TXTSaveIniAndCheckIfColumnNameWithLeadingSemicolonIsBacktickified(AbstractTestCases.TestD2TXTSaveIniAndCompareContents):
    """Tests if columns names with leading semicolons are surrounded with
    backticks (to prevent being treated as comments) when saved to an INI file.
    """

    txt_source = [
        [';leading semicolon', 'semicolons;in;middle'],
        [';leading semicolon', 'semicolons;in;middle'],
    ]
    ini_expected = (
        '[Columns]\n`;leading semicolon`\nsemicolons;in;middle\n\n'
        '[1]\n'
        '`;leading semicolon` = ;leading semicolon\n'
        'semicolons;in;middle = semicolons;in;middle\n\n'
    )

class TestD2TXTSaveIniAndCheckIfEqualSignsAreEscaped(AbstractTestCases.TestD2TXTSaveIniAndCompareContents):
    """Tests if equal signs (=) in column names (but not values) are escaped."""

    txt_source = [['=leading equals', 'equals=in=middle'], ['=leading equals', 'equals=in=middle']]
    ini_expected = (
        '[Columns]\n${eq}leading equals\nequals${eq}in${eq}middle\n\n'
        '[1]\n'
        '${eq}leading equals = =leading equals\n'
        'equals${eq}in${eq}middle = equals=in=middle\n\n'
    )

class TestD2TXTSaveIniAndCheckIfFalsyValuesIgnored(AbstractTestCases.TestD2TXTSaveIniAndCompareContents):
    """Tests if falsy values are ignored when saving to an INI file."""

    txt_source = [
        ['int 0', 'float 0.0', 'False', 'None'],
        [0, 0.0, False, None],
    ]
    ini_expected = (
        '[Columns]\nint 0\nfloat 0.0\nFalse\nNone\n\n'
        '[1]\n\n'
    )

class TestD2TXTLoadIniAndCheckBitFieldDecoded(AbstractTestCases.TestD2TXTSaveIniAndCompareContents):
    """Tests if bitfields are correctly decoded when saved to an INI file."""

    txt_source = [['aurafilter'], ['33025'], ['0'], ['65535'], ['4294901760']]
    ini_expected = (
        '[Columns]\naurafilter\n\n'
        '[1]\naurafilter = FindPlayers | NotInsideTowns | IgnoreAllies\n\n'
        '[2]\naurafilter = 0\n\n'
        '[3]\naurafilter = FindPlayers | FindMonsters | FindOnlyUndead | FindMissiles | FindObjects | FindItems | 0x40 | FindAttackable | NotInsideTowns | UseLineOfSight | FindSelectable | 0x800 | FindCorpses | NotInsideTowns2 | IgnoreBoss | IgnoreAllies\n\n'
        '[4]\naurafilter = IgnoreNPC | Unknown20000 | IgnorePrimeEvil | IgnoreJustHitUnits | 0x100000 | 0x200000 | 0x400000 | 0x800000 | 0x1000000 | 0x2000000 | 0x4000000 | 0x8000000 | 0x10000000 | 0x20000000 | 0x40000000 | 0x80000000\n\n'
    )