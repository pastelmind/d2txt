#!/usr/bin/env python

"""Unit test for d2txt.py"""


from d2txt import D2TXT, DuplicateColumnNameWarning
import unittest
import os
from os import path
from io import StringIO
from tempfile import NamedTemporaryFile


class TestD2TXT(unittest.TestCase):
    """Contains tests that create and modify a new D2TXT object."""

    def testEmptyTxt(self):
        """Tests if a new D2TXT object has zero rows."""
        d2txt = D2TXT([])
        self.assertEqual(len(d2txt), 0)
        with self.assertRaises(IndexError):
            d2txt[0]
        with self.assertRaises(IndexError):
            d2txt[0] = []

    def testColumnNameAssignment(self):
        """Tests column name assignment."""
        base_column_names = ['column 1', 'column 2', 'column 3']
        d2txt = D2TXT(base_column_names)
        self.assertEqual(list(d2txt.column_names()), base_column_names)

    def testCellReadWrite(self):
        """Tests if cells can be accessed using row indices and column names."""
        d2txt = D2TXT(['column 1', 'column 2', 'column 3'])

        d2txt.append(['foo', 'bar', 'baz'])
        self.assertEqual(d2txt[0]['column 1'], 'foo')
        self.assertEqual(d2txt[0]['column 2'], 'bar')
        self.assertEqual(d2txt[0]['column 3'], 'baz')

        d2txt[0]['column 1'] = 'alpha'
        d2txt[0]['column 2'] = 'beta'
        d2txt[0]['column 3'] = 'gamma'
        self.assertEqual(d2txt[0]['column 1'], 'alpha')
        self.assertEqual(d2txt[0]['column 2'], 'beta')
        self.assertEqual(d2txt[0]['column 3'], 'gamma')

    def testRowCastToList(self):
        """Tests if a D2TXT row can be converted to a list."""
        d2txt = D2TXT(['column 1', 'column 2', 'column 3'])

        d2txt.append(['foo', 'bar', 'baz'])
        self.assertEqual(list(d2txt[0].values()), ['foo', 'bar', 'baz'])

        d2txt[0]['column 1'] = 'alpha'
        d2txt[0]['column 2'] = 'beta'
        d2txt[0]['column 3'] = 'gamma'
        self.assertEqual(list(d2txt[0].values()), ['alpha', 'beta', 'gamma'])

    def testOutOfBoundsReadWrite(self):
        """Tests if accessing invalid rows and cells raises appropriate exceptions."""
        d2txt = D2TXT(['column 1', 'column 2', 'column 3'])
        d2txt.append(['foo', 'bar', 'baz'])
        d2txt.append(['rabbit', 'dog', 'cow'])
        d2txt.append(['one', 'two', 'six'])

        with self.assertRaises(IndexError):
            d2txt[99]
        with self.assertRaises(IndexError):
            d2txt[99] = ['mangy', 'dog', 'cow']
        with self.assertRaises(IndexError):
            d2txt[99]['column 1']
        with self.assertRaises(IndexError):
            d2txt[99]['column 1'] = 'cat'
        with self.assertRaises(KeyError):
            d2txt[0]['column 99']
        with self.assertRaises(KeyError):
            d2txt[0]['column 99'] = 'bird'

    def testColumnNameIsCaseSensitive(self):
        """Tests if column names are case-sensitive."""
        d2txt = D2TXT(['column name', 'Column Name', 'COLUMN NAME'])

        d2txt.append(['lowercase', 'capital letters', 'uppercase'])
        self.assertEqual(list(d2txt[0].values()), ['lowercase', 'capital letters', 'uppercase'])
        with self.assertRaises(KeyError):
            d2txt[0]['column NAME']

        d2txt[0]['COLUMN NAME'] = 'c'
        d2txt[0]['Column Name'] = 'b'
        d2txt[0]['column name'] = 'a'
        self.assertEqual(list(d2txt[0].values()), ['a', 'b', 'c'])
        with self.assertRaises(KeyError):
            d2txt[0]['column NAME'] = 1

    def testDuplicateColumnNames(self):
        """Tests if duplicate column names are renamed correctly."""
        with self.assertWarns(DuplicateColumnNameWarning):
            d2txt = D2TXT(['column name'] * 60)

        column_names = list(d2txt.column_names())
        self.assertEqual(column_names[1], 'column name(B)')
        self.assertEqual(column_names[2], 'column name(C)')
        self.assertEqual(column_names[24], 'column name(Y)')
        self.assertEqual(column_names[25], 'column name(Z)')
        self.assertEqual(column_names[26], 'column name(AA)')
        self.assertEqual(column_names[27], 'column name(AB)')
        self.assertEqual(column_names[51], 'column name(AZ)')
        self.assertEqual(column_names[52], 'column name(BA)')
        self.assertEqual(column_names[53], 'column name(BB)')

    def testAssignList(self):
        """Tests if D2TXT accepts direct assignment using lists."""
        d2txt = D2TXT(['column 1', 'column 2', 'column 3'])

        d2txt.extend([[]] * 3)
        d2txt[0] = []
        d2txt[1] = ['foo', 'bar']
        d2txt[2] = ['1', '2', '3', 'these', 'strings', 'are', 'ignored']

        self.assertEqual(len(d2txt), 3)
        for i in range(len(d2txt)):
            with self.subTest(i=i):
                self.assertEqual(len(d2txt[i]), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ['foo', 'bar', None])
        self.assertEqual(list(d2txt[2].values()), ['1', '2', '3'])

    def testAppendList(self):
        """Tests if D2TXT.append() accepts lists."""
        d2txt = D2TXT(['column 1', 'column 2', 'column 3'])

        # Internally uses D2TXT.insert()
        d2txt.append([])
        self.assertEqual(len(d2txt), 1)
        d2txt.append(['foo', 'bar'])
        self.assertEqual(len(d2txt), 2)
        d2txt.append(['1', '2', '3', 'these', 'strings', 'are', 'ignored'])
        self.assertEqual(len(d2txt), 3)

        for i in range(len(d2txt)):
            with self.subTest(i=i):
                self.assertEqual(len(d2txt[i]), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ['foo', 'bar', None])
        self.assertEqual(list(d2txt[2].values()), ['1', '2', '3'])

    def testExtendList(self):
        """Tests if D2TXT.extend() accepts lists."""
        d2txt = D2TXT(['column 1', 'column 2', 'column 3'])

        # Internally uses D2TXT.append(), which uses D2TXT.insert()
        d2txt.extend([[]])
        self.assertEqual(len(d2txt), 1)
        d2txt.extend([['foo', 'bar'], ['1', '2', '3', 'these', 'strings', 'are', 'ignored']])
        self.assertEqual(len(d2txt), 3)

        for i in range(len(d2txt)):
            with self.subTest(i=i):
                self.assertEqual(len(d2txt[i]), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ['foo', 'bar', None])
        self.assertEqual(list(d2txt[2].values()), ['1', '2', '3'])

    def testInsertList(self):
        """Tests if D2TXT.insert() accepts lists."""
        d2txt = D2TXT(['column 1', 'column 2', 'column 3'])

        d2txt.insert(0, [])
        self.assertEqual(len(d2txt), 1)
        d2txt.insert(0, ['foo', 'bar'])
        self.assertEqual(len(d2txt), 2)
        d2txt.insert(1, ['1', '2', '3', 'these', 'strings', 'are', 'ignored'])
        self.assertEqual(len(d2txt), 3)

        for i in range(len(d2txt)):
            with self.subTest(i=i):
                self.assertEqual(len(d2txt[i]), 3)

        self.assertEqual(list(d2txt[0].values()), ['foo', 'bar', None])
        self.assertEqual(list(d2txt[1].values()), ['1', '2', '3'])
        self.assertEqual(list(d2txt[2].values()), [None, None, None])

    def testSliceAssignList(self):
        """Tests if D2TXT accepts slice syntax assignment using lists."""
        d2txt = D2TXT(['column 1', 'column 2', 'column 3'])

        d2txt[:] = [[], ['foo', 'bar'], ['1', '2', '3', 'these', 'strings', 'are', 'ignored']]
        self.assertEqual(len(d2txt), 3)
        for i in range(len(d2txt)):
            with self.subTest(i=i):
                self.assertEqual(len(d2txt[i]), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ['foo', 'bar', None])
        self.assertEqual(list(d2txt[2].values()), ['1', '2', '3'])

        d2txt[0:2] = [['car', 'bus', 'cow'], ['one', 'two', 'three', 'four'], ['portal']]
        self.assertEqual(len(d2txt), 4)
        for i in range(len(d2txt)):
            with self.subTest(i=i):
                self.assertEqual(len(d2txt[i]), 3)

        self.assertEqual(list(d2txt[0].values()), ['car', 'bus', 'cow'])
        self.assertEqual(list(d2txt[1].values()), ['one', 'two', 'three'])
        self.assertEqual(list(d2txt[2].values()), ['portal', None, None])
        self.assertEqual(list(d2txt[3].values()), ['1', '2', '3'])

    def testAssignDict(self):
        """Tests if D2TXT accepts assignment using dictionaries."""
        d2txt = D2TXT(['column 1', 'column 2', 'column 3'])

        d2txt.append({})
        d2txt.extend([
            {'column 1': 'foo', 'column 2': 'bar'},
            {'column 1': '1', 'column 2': '2', 'column 3': '3', 'column 4': 'ignored'},
        ])
        d2txt.insert(1, {'column 1': 'a', 'column 2': 'b', 'column 3': 'c'})

        self.assertEqual(len(d2txt), 4)
        for i in range(len(d2txt)):
            with self.subTest(i=i):
                self.assertEqual(len(d2txt[i]), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ['a', 'b', 'c'])
        self.assertEqual(list(d2txt[2].values()), ['foo', 'bar', None])
        self.assertEqual(list(d2txt[3].values()), ['1', '2', '3'])


class TestD2TXTLoadFileFromSources(unittest.TestCase):
    """Tests if D2TXT can be load a file using several sources."""

    sample_txt_path = path.join(path.dirname(path.abspath(__file__)), 'sample.txt')

    # Represents the expected structure of D2TXT loaded from sample.txt
    sample_txt_expected = [
        ['column name', 'duplicate name', 'duplicate name(C)', '', 'COLUMN NAME'],
        ['lowercase column name', 'next cell is empty', '', 'empty column name', 'UPPERCASE COLUMN NAME'],
        ['next row is empty', '   leading spaces', 'trailing spaces   ', '    surrounded by spaces  ', '"double quotes"'],
        ['', '', '', '', '0'],
        ['this row and the next has not enough cells', None, None, None, None],
        [None, None, None, None, None],
    ]

    def test_LoadFileFromPath(self):
        """Tests if D2TXT can load a file using a file path, and its contents
        are preserved."""
        sample_txt_expected = self.__class__.sample_txt_expected
        with self.assertWarns(DuplicateColumnNameWarning):
            d2txt = D2TXT.load_txt(self.__class__.sample_txt_path)

        self.assertEqual(len(d2txt), len(sample_txt_expected) - 1, 'Row count')
        self.assertEqual(tuple(d2txt.column_names()), tuple(sample_txt_expected[0]), 'Column mismatch')
        for row_index, row in enumerate(d2txt):
            with self.subTest(row_index=row_index):
                self.assertEqual(list(row.values()), sample_txt_expected[row_index + 1])

    def test_LoadFileFromObject(self):
        """Tests if D2TXT can load a file using a file object, and its contents
        are preserved."""
        sample_txt_expected = self.__class__.sample_txt_expected
        # newline='' is required to make csv.reader work correctly
        with self.assertWarns(DuplicateColumnNameWarning):
            with open(self.__class__.sample_txt_path, newline='') as sample_txt:
                d2txt = D2TXT.load_txt(sample_txt)

        self.assertEqual(len(d2txt), len(sample_txt_expected) - 1, 'Row count')
        self.assertEqual(tuple(d2txt.column_names()), tuple(sample_txt_expected[0]), 'Column mismatch')
        for row_index, row in enumerate(d2txt):
            with self.subTest(row_index=row_index):
                self.assertEqual(list(row.values()), sample_txt_expected[row_index + 1])

    def test_DuplicateColumnNamesAreRenamed(self):
        """Tests if duplicate column names are renamed when loading a TXT file.
        """
        txtfile = StringIO()
        txtfile.write(
            'column name\tcolumn name 2\tcolumn name 2\tcolumn name\tcolumn name\tcolumn name 2\r\n'
            'foo\tbar\tbar\tfoo\tfoo\tbar\r\n'
        )
        txtfile.seek(0)

        with self.assertWarns(DuplicateColumnNameWarning):
            d2txt = D2TXT.load_txt(txtfile)

        expected_column_names = ['column name', 'column name 2', 'column name 2(C)', 'column name(D)', 'column name(E)', 'column name 2(F)']
        self.assertEqual(list(d2txt.column_names()), expected_column_names)


# A dummy class that hides abstract test cases from the module-level namespace
# to prevent `unittest` from discovering and running them.
# Original idea from https://stackoverflow.com/a/25695512/9943202
class AbstractTestCases:
    # An ABC test case inherited by other test cases in the "LoadFile" family.
    class TestD2TXTLoadFileAndCompareContents(unittest.TestCase):
        """Loads D2TXT from a file object and tests if it matches the expected
        contents."""

        # A string representing the contents of the TXT file to test.
        # Must be redefined by concrete test cases that inherit this class.
        load_contents = NotImplementedError('load_contents')

        # A list-of-lists representation of the expected contents of the D2TXT
        # object loaded from `load_contents`, with the column names in the first
        # child list.
        # Must be redefined by concrete test cases that inherit this class.
        load_expected = NotImplementedError('load_expected')

        def test_LoadFileAndCheckContents(self):
            """Loads D2TXT from a file containing `load_contents` and tests if it
            matches `load_expected`."""
            load_expected = self.__class__.load_expected
            # newline='' is required to make csv.reader work correctly
            with StringIO(self.__class__.load_contents, newline='') as txtfile:
                d2txt = D2TXT.load_txt(txtfile)

            self.assertEqual(len(d2txt), len(load_expected) - 1, 'Row count')
            self.assertEqual(tuple(d2txt.column_names()), tuple(load_expected[0]), 'Column mismatch')
            for row_index, row in enumerate(d2txt):
                with self.subTest(row_index=row_index):
                    self.assertEqual(list(row.values()), load_expected[row_index + 1])


    # An ABC test case inherited by other test cases in the "SaveFile" family.
    class TestD2TXTSaveFileAndCompareContents(unittest.TestCase):
        """Saves D2TXT to a file object and tests if its content matches the
        expected value."""

        # A list-of-lists representation of the D2TXT object to save to a TXT
        # file object, with the column names in the first child list.
        # Must be redefined by concrete test cases that inherit this class.
        save_source = NotImplementedError('save_source')

        # A string representing the expected contents of the TXT file saved.
        # Must be redefined by concrete test cases that inherit this class.
        save_expected = NotImplementedError('save_expected')

        def test_SaveFileAndCheckContents(self):
            """Saves D2TXT to a file containing and tests if its content matches
            `save_expected`."""
            d2txt = D2TXT(self.__class__.save_source[0])
            d2txt.extend(self.__class__.save_source[1:])

            # newline='' is required to make csv.writer work correctly
            save_txt = StringIO(newline='')
            d2txt.to_txt(save_txt)

            self.assertEqual(save_txt.getvalue(), self.__class__.save_expected)


class TestD2TXTLoadFileNormal(AbstractTestCases.TestD2TXTLoadFileAndCompareContents):
    """Tests if D2TXT loads a normal TXT file correctly."""

    load_contents = (
        'column 1\tcolumn 2\tcolumn 3\r\n'
        'value 1\tvalue 2\tvalue 3\r\n'
        'foo\tbar\tbaz\r\n'
    )
    load_expected = [
        ['column 1', 'column 2', 'column 3'],
        ['value 1', 'value 2', 'value 3'],
        ['foo', 'bar', 'baz'],
    ]

class TestD2TXTLoadFileAndCheckIfColumnIsCaseSensitive(AbstractTestCases.TestD2TXTLoadFileAndCompareContents):
    """Tests if D2TXT treats column names as case sensitive when loading a TXT file."""

    load_contents = (
        'column name\tColumn Name\tCOLUMN NAME\r\n'
        'lowercase\tCapitalized\tUPPERCASE\r\n'
    )
    load_expected = [
        ['column name', 'Column Name', 'COLUMN NAME'],
        ['lowercase', 'Capitalized', 'UPPERCASE'],
    ]

class TestD2TXTLoadFileAndCheckIfColumnNameWhitespaceIsPreserved(AbstractTestCases.TestD2TXTLoadFileAndCompareContents):
    """Tests if D2TXT can correctly load from a TXT file column names that have
    leading/trailing whitespaces, is empty, or has only whitespace."""

    load_contents = (
        '   column 1\tcolumn 2    \t  column 3  \t\t  \r\n'
        '3 leading spaces\t4 trailing spaces\t2 surrounding spaces\tempty\t2 spaces only\r\n'
    )
    load_expected = [
        ['   column 1', 'column 2    ', '  column 3  ', '', '  '],
        ['3 leading spaces', '4 trailing spaces', '2 surrounding spaces', 'empty', '2 spaces only'],
    ]

class TestD2TXTLoadFileAndCheckIfEmptyCellsAreLoaded(AbstractTestCases.TestD2TXTLoadFileAndCompareContents):
    """Tests if D2TXT can correctly load empty cells and rows in a TXT file."""

    load_contents = 'column 1\tcolumn 2\tcolumn 3\r\nempty\t\t\r\n\t\t\r\n'
    load_expected = [
        ['column 1', 'column 2', 'column 3'],
        ['empty', '', ''],
        ['', '', ''],
    ]

class TestD2TXTLoadFileAndCheckIfCellWhitespaceIsPreserved(AbstractTestCases.TestD2TXTLoadFileAndCompareContents):
    """Tests if D2TXT can correctly load whitespace in column names and cells in
    a TXT file."""

    load_contents = (
        'column 1\tcolumn 2\tcolumn 3\r\n'
        '  2 leading spaces\t3 trailing spaces   \t     \r\n'
    )
    load_expected = [
        ['column 1', 'column 2', 'column 3'],
        ['  2 leading spaces', '3 trailing spaces   ', '     '],
    ]

class TestD2TXTLoadFileAndCheckIfSurroundingQuotesArePreserved(AbstractTestCases.TestD2TXTLoadFileAndCompareContents):
    """Tests if D2TXT can correctly load single, double, and backtick-quoted
    column names and cell values in a TXT file."""

    load_contents = (
        '\'single quoted column\'\t"double quoted column"\t`backticked column`\r\n'
        '\'single quoted value\'\t"double quoted value"\t`backticked value`\r\n'
    )
    load_expected = [
        ['\'single quoted column\'', '"double quoted column"', '`backticked column`'],
        ['\'single quoted value\'', '"double quoted value"', '`backticked value`'],
    ]

class TestD2TXTLoadFileAndCheckIfMissingCellsAreLoaded(AbstractTestCases.TestD2TXTLoadFileAndCompareContents):
    """Tests if D2TXT can correctly load missing cells (caused by missing tabs)
    in a TXT file."""

    load_contents = 'column 1\tcolumn 2\tcolumn 3\r\n1 tab\t\r\nno tabs\r\n\r\n'
    load_expected = [
        ['column 1', 'column 2', 'column 3'],
        ['1 tab', '', None],
        ['no tabs', None, None],
        [None, None, None],
    ]


class TestD2TXTSaveFileToSources(unittest.TestCase):
    """Tests if D2TXT can be saved to a file using several sources."""

    # Represents the source structure of D2TXT to be saved
    save_source = [
        ['column 1', 'column 2', 'column 3'],
        ['value 1', 'value 2', 'value 3'],
        ['foo', 'bar', 'baz'],
    ]
    # Expected contents of D2TXT written to a TXT file
    save_expected = (
        'column 1\tcolumn 2\tcolumn 3\r\n'
        'value 1\tvalue 2\tvalue 3\r\n'
        'foo\tbar\tbaz\r\n'
    )

    @classmethod
    def setUpClass(cls):
        # Create a temporary file and retrieve its path
        # The file must be closed immediately to access it by path on Windows
        with NamedTemporaryFile(delete=False) as save_txt:
            cls.save_txt_path = save_txt.name

    @classmethod
    def tearDownClass(cls):
        # Delete the temporary file
        os.remove(cls.save_txt_path)

    def setUp(self):
        self.d2txt = D2TXT(self.__class__.save_source[0])
        self.d2txt.extend(self.__class__.save_source[1:])

    def test_SaveFileToPath(self):
        """Tests if D2TXT can save a file using a file path, and its contents
        are preserved."""
        self.d2txt.to_txt(self.__class__.save_txt_path)

        with open(self.__class__.save_txt_path, newline='') as save_txt:
            save_contents = save_txt.read()

        self.assertEqual(save_contents, self.__class__.save_expected)

    def test_SaveFileToObject(self):
        """Tests if D2TXT can save a file using a file object, and its contents
        are preserved."""
        # newline='' is required to make csv.writer work correctly
        save_txt = StringIO(newline='')
        self.d2txt.to_txt(save_txt)

        self.assertEqual(save_txt.getvalue(), self.__class__.save_expected)


class TestD2TXTSaveFileAndCheckIfColumnIsCaseSensitive(AbstractTestCases.TestD2TXTSaveFileAndCompareContents):
    """Tests if D2TXT treats column names as case sensitive when saving a TXT file."""

    save_source = [
        ['column name', 'Column Name', 'COLUMN NAME'],
        ['lowercase', 'Capitalized', 'UPPERCASE'],
    ]
    save_expected = (
        'column name\tColumn Name\tCOLUMN NAME\r\n'
        'lowercase\tCapitalized\tUPPERCASE\r\n'
    )

class TestD2TXTSaveFileAndCheckIfColumnNameWhitespaceIsPreserved(AbstractTestCases.TestD2TXTSaveFileAndCompareContents):
    """Tests if D2TXT can correctly save to a TXT file column names that have
    leading/trailing whitespaces, is empty, or has only whitespace."""

    save_source = [
        ['   column 1', 'column 2    ', '  column 3  ', '', '  '],
        ['3 leading spaces', '4 trailing spaces', '2 surrounding spaces', 'empty', '2 spaces only'],
    ]
    save_expected = (
        '   column 1\tcolumn 2    \t  column 3  \t\t  \r\n'
        '3 leading spaces\t4 trailing spaces\t2 surrounding spaces\tempty\t2 spaces only\r\n'
    )

class TestD2TXTSaveFileAndCheckIfFalsyCellsArePreserved(AbstractTestCases.TestD2TXTSaveFileAndCompareContents):
    """Tests if D2TXT can correctly save cells and rows that are empty (''),
    contain None, integer 0, float 0.0, or False to a TXT file."""

    save_source = [
        ['column 1', 'column 2', 'column 3'],
        ['empty', '', ''],
        ['', '', ''],
        ['None', None, None],
        [None, None, None],
        ['integer 0', 0, 0],
        [0, 0, 0],
        ['float 0.0', 0.0, 0.0],
        [0.0, 0.0, 0.0],
        ['False', False, False],
        [False, False, False],
        ['truncated row'],
        []
    ]
    save_expected = (
        'column 1\tcolumn 2\tcolumn 3\r\n'
        'empty\t\t\r\n'
        '\t\t\r\n'
        'None\t\t\r\n'
        '\t\t\r\n'
        'integer 0\t0\t0\r\n'
        '0\t0\t0\r\n'
        'float 0.0\t0.0\t0.0\r\n'
        '0.0\t0.0\t0.0\r\n'
        'False\tFalse\tFalse\r\n'
        'False\tFalse\tFalse\r\n'
        'truncated row\t\t\r\n'
        '\t\t\r\n'
    )

class TestD2TXTSaveFileAndCheckIfCellWhitespaceIsPreserved(AbstractTestCases.TestD2TXTSaveFileAndCompareContents):
    """Tests if D2TXT can correctly save whitespace in column names and cells to
    a TXT file."""

    save_source = [
        ['column 1', 'column 2', 'column 3'],
        ['  2 leading spaces', '3 trailing spaces   ', '     '],
    ]
    save_expected = (
        'column 1\tcolumn 2\tcolumn 3\r\n'
        '  2 leading spaces\t3 trailing spaces   \t     \r\n'
    )

class TestD2TXTSaveFileAndCheckIfSurroundingQuotesArePreserved(AbstractTestCases.TestD2TXTSaveFileAndCompareContents):
    """Tests if D2TXT can correctly save single, double, and backtick-quoted
    column names and cell values to a TXT file."""

    save_source = [
        ['\'single quoted column\'', '"double quoted column"', '`backticked column`'],
        ['\'single quoted value\'', '"double quoted value"', '`backticked value`'],
    ]
    save_expected = (
        '\'single quoted column\'\t"double quoted column"\t`backticked column`\r\n'
        '\'single quoted value\'\t"double quoted value"\t`backticked value`\r\n'
    )
