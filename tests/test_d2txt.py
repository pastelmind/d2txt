#!/usr/bin/env python
"""Unit test for d2txt.py"""

from io import StringIO
import os
from os import path
from tempfile import NamedTemporaryFile
from typing import Iterable, Sequence
import unittest

from d2txt import D2TXT, DuplicateColumnNameWarning


class TestD2TXTBase(unittest.TestCase):
    """Base class for D2TXT-related tests. Provides convenience methods."""

    def compare_d2txt(
        self, d2txt: D2TXT, column_names: Iterable[str], rows: Sequence[Iterable[str]],
    ):
        """Compares a D2TXT object with the given column names and rows.

        A convenience method. Compares the column names and rows of a D2TXT
        object with the given values using `self.assertEqual()`.

        Args:
            d2txt: A D2TXT object.
            column_names: An iterable of strings to compare with the column
                names in `d2txt`.
            rows: A sequence of iterables of strings. Each iterable is compared
                with each row in `d2txt`.

        Raises:
            AssertionError: The D2TXT object does not match the given values.
        """
        self.assertEqual(list(d2txt.column_names()), list(column_names))
        self.assertEqual(len(d2txt), len(rows), "Row count")
        for row_index, row in enumerate(d2txt):
            with self.subTest(row_index=row_index):
                self.assertEqual(list(row.values()), list(rows[row_index]))


class TestD2TXT(unittest.TestCase):
    """Contains tests that create and modify a new D2TXT object."""

    def test_empty_txt(self):
        """Tests if a new D2TXT object has zero rows."""
        d2txt = D2TXT([])
        self.assertEqual(len(d2txt), 0)
        with self.assertRaises(IndexError):
            d2txt[0]  # pylint:disable=pointless-statement
        with self.assertRaises(IndexError):
            d2txt[0] = []

    def test_column_assignment(self):
        """Tests column name assignment."""
        base_column_names = ["column 1", "column 2", "column 3"]
        d2txt = D2TXT(base_column_names)
        self.assertEqual(list(d2txt.column_names()), base_column_names)

    def test_cell_access(self):
        """Tests if cells can be accessed using row indices and column names."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])

        d2txt.append(["foo", "bar", "baz"])
        self.assertEqual(d2txt[0]["column 1"], "foo")
        self.assertEqual(d2txt[0]["column 2"], "bar")
        self.assertEqual(d2txt[0]["column 3"], "baz")

        d2txt[0]["column 1"] = "alpha"
        d2txt[0]["column 2"] = "beta"
        d2txt[0]["column 3"] = "gamma"
        self.assertEqual(d2txt[0]["column 1"], "alpha")
        self.assertEqual(d2txt[0]["column 2"], "beta")
        self.assertEqual(d2txt[0]["column 3"], "gamma")

    def test_convert_row_to_list(self):
        """Tests if a D2TXT row can be converted to a list."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])

        d2txt.append(["foo", "bar", "baz"])
        self.assertEqual(list(d2txt[0].values()), ["foo", "bar", "baz"])

        d2txt[0]["column 1"] = "alpha"
        d2txt[0]["column 2"] = "beta"
        d2txt[0]["column 3"] = "gamma"
        self.assertEqual(list(d2txt[0].values()), ["alpha", "beta", "gamma"])

    def test_invalid_row_and_cell(self):
        """Tests if accessing invalid rows and cells raises appropriate exceptions."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])
        d2txt.append(["foo", "bar", "baz"])
        d2txt.append(["rabbit", "dog", "cow"])
        d2txt.append(["one", "two", "six"])

        with self.assertRaises(IndexError):
            d2txt[99]  # pylint:disable=pointless-statement
        with self.assertRaises(IndexError):
            d2txt[99] = ["mangy", "dog", "cow"]
        with self.assertRaises(IndexError):
            d2txt[99]["column 1"]  # pylint:disable=pointless-statement
        with self.assertRaises(IndexError):
            d2txt[99]["column 1"] = "cat"
        with self.assertRaises(KeyError):
            d2txt[0]["column 99"]  # pylint:disable=pointless-statement
        with self.assertRaises(KeyError):
            d2txt[0]["column 99"] = "bird"

    def test_column_name_case_sensitivity(self):
        """Tests if column names are case-sensitive."""
        d2txt = D2TXT(["column name", "Column Name", "COLUMN NAME"])

        d2txt.append(["lowercase", "capital letters", "uppercase"])
        self.assertEqual(
            list(d2txt[0].values()), ["lowercase", "capital letters", "uppercase"],
        )
        with self.assertRaises(KeyError):
            d2txt[0]["column NAME"]  # pylint:disable=pointless-statement

        d2txt[0]["COLUMN NAME"] = "c"
        d2txt[0]["Column Name"] = "b"
        d2txt[0]["column name"] = "a"
        self.assertEqual(list(d2txt[0].values()), ["a", "b", "c"])
        with self.assertRaises(KeyError):
            d2txt[0]["column NAME"] = 1

    def test_duplicate_column_renaming(self):
        """Tests if duplicate column names are renamed correctly."""
        with self.assertWarns(DuplicateColumnNameWarning):
            d2txt = D2TXT(["column name"] * 60)

        column_names = list(d2txt.column_names())
        self.assertEqual(column_names[1], "column name(B)")
        self.assertEqual(column_names[2], "column name(C)")
        self.assertEqual(column_names[24], "column name(Y)")
        self.assertEqual(column_names[25], "column name(Z)")
        self.assertEqual(column_names[26], "column name(AA)")
        self.assertEqual(column_names[27], "column name(AB)")
        self.assertEqual(column_names[51], "column name(AZ)")
        self.assertEqual(column_names[52], "column name(BA)")
        self.assertEqual(column_names[53], "column name(BB)")

    def test_assign_list(self):
        """Tests if D2TXT accepts direct assignment using lists."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])

        d2txt.extend([[]] * 3)
        d2txt[0] = []
        d2txt[1] = ["foo", "bar"]
        d2txt[2] = ["1", "2", "3", "these", "strings", "are", "ignored"]

        self.assertEqual(len(d2txt), 3)
        for i, row in enumerate(d2txt):
            with self.subTest(i=i):
                self.assertEqual(len(row), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ["foo", "bar", None])
        self.assertEqual(list(d2txt[2].values()), ["1", "2", "3"])

    def test_append_list(self):
        """Tests if D2TXT.append() accepts lists."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])

        # Internally uses D2TXT.insert()
        d2txt.append([])
        self.assertEqual(len(d2txt), 1)
        d2txt.append(["foo", "bar"])
        self.assertEqual(len(d2txt), 2)
        d2txt.append(["1", "2", "3", "these", "strings", "are", "ignored"])
        self.assertEqual(len(d2txt), 3)

        for i, row in enumerate(d2txt):
            with self.subTest(i=i):
                self.assertEqual(len(row), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ["foo", "bar", None])
        self.assertEqual(list(d2txt[2].values()), ["1", "2", "3"])

    def test_extend_list(self):
        """Tests if D2TXT.extend() accepts lists."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])

        # Internally uses D2TXT.append(), which uses D2TXT.insert()
        d2txt.extend([[]])
        self.assertEqual(len(d2txt), 1)
        d2txt.extend(
            [["foo", "bar"], ["1", "2", "3", "these", "strings", "are", "ignored"],]
        )
        self.assertEqual(len(d2txt), 3)

        for i, row in enumerate(d2txt):
            with self.subTest(i=i):
                self.assertEqual(len(row), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ["foo", "bar", None])
        self.assertEqual(list(d2txt[2].values()), ["1", "2", "3"])

    def test_insert_list(self):
        """Tests if D2TXT.insert() accepts lists."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])

        d2txt.insert(0, [])
        self.assertEqual(len(d2txt), 1)
        d2txt.insert(0, ["foo", "bar"])
        self.assertEqual(len(d2txt), 2)
        d2txt.insert(1, ["1", "2", "3", "these", "strings", "are", "ignored"])
        self.assertEqual(len(d2txt), 3)

        for i, row in enumerate(d2txt):
            with self.subTest(i=i):
                self.assertEqual(len(row), 3)

        self.assertEqual(list(d2txt[0].values()), ["foo", "bar", None])
        self.assertEqual(list(d2txt[1].values()), ["1", "2", "3"])
        self.assertEqual(list(d2txt[2].values()), [None, None, None])

    def test_slice_syntax(self):
        """Tests if D2TXT accepts slice syntax assignment using lists."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])

        d2txt[:] = [
            [],
            ["foo", "bar"],
            ["1", "2", "3", "these", "strings", "are", "ignored"],
        ]
        self.assertEqual(len(d2txt), 3)
        for i, row in enumerate(d2txt):
            with self.subTest(i=i):
                self.assertEqual(len(row), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ["foo", "bar", None])
        self.assertEqual(list(d2txt[2].values()), ["1", "2", "3"])

        d2txt[0:2] = [
            ["car", "bus", "cow"],
            ["one", "two", "three", "four"],
            ["portal"],
        ]
        self.assertEqual(len(d2txt), 4)
        for i, row in enumerate(d2txt):
            with self.subTest(i=i):
                self.assertEqual(len(row), 3)

        self.assertEqual(list(d2txt[0].values()), ["car", "bus", "cow"])
        self.assertEqual(list(d2txt[1].values()), ["one", "two", "three"])
        self.assertEqual(list(d2txt[2].values()), ["portal", None, None])
        self.assertEqual(list(d2txt[3].values()), ["1", "2", "3"])

    def test_assign_dict(self):
        """Tests if D2TXT accepts assignment using dictionaries."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])

        d2txt.append({})
        d2txt.extend(
            [
                {"column 1": "foo", "column 2": "bar"},
                {
                    "column 1": "1",
                    "column 2": "2",
                    "column 3": "3",
                    "column 4": "ignored",
                },
            ]
        )
        d2txt.insert(1, {"column 1": "a", "column 2": "b", "column 3": "c"})

        self.assertEqual(len(d2txt), 4)
        for i, row in enumerate(d2txt):
            with self.subTest(i=i):
                self.assertEqual(len(row), 3)

        self.assertEqual(list(d2txt[0].values()), [None, None, None])
        self.assertEqual(list(d2txt[1].values()), ["a", "b", "c"])
        self.assertEqual(list(d2txt[2].values()), ["foo", "bar", None])
        self.assertEqual(list(d2txt[3].values()), ["1", "2", "3"])


class TestD2TXTLoadFile(TestD2TXTBase):
    """Contains tests that load D2TXT objects from TXT files."""

    def test_load_path(self):
        """Tests if D2TXT can load a file using a file path, and its contents
        are preserved."""
        file_path = path.join(path.dirname(path.abspath(__file__)), "sample.txt")
        with self.assertWarns(DuplicateColumnNameWarning):
            d2txt = D2TXT.load_txt(file_path)

        self.compare_d2txt(
            d2txt,
            ["column name", "duplicate name", "duplicate name(C)", "", "COLUMN NAME",],
            [
                [
                    "lowercase column name",
                    "next cell is empty",
                    "",
                    "empty column name",
                    "UPPERCASE COLUMN NAME",
                ],
                [
                    "next row is empty",
                    "   leading spaces",
                    "trailing spaces   ",
                    "    surrounded by spaces  ",
                    '"double quotes"',
                ],
                ["", "", "", "", "0"],
                ["this row and the next has not enough cells", None, None, None, None],
                [None, None, None, None, None],
            ],
        )

    def test_load_file_object(self):
        """Tests if D2TXT can load a TXT file from a file object."""
        d2txt = D2TXT.load_txt(
            StringIO(
                "column 1\tcolumn 2\tcolumn 3\r\n"
                "value 1\tvalue 2\tvalue 3\r\n"
                "foo\tbar\tbaz\r\n",
                newline="",  # Required to make csv.reader work correctly
            )
        )
        self.compare_d2txt(
            d2txt,
            ["column 1", "column 2", "column 3"],
            [["value 1", "value 2", "value 3"], ["foo", "bar", "baz"]],
        )

    def test_duplicate_column_names(self):
        """Tests if duplicate column names are renamed when loading a TXT file.
        """
        with self.assertWarns(DuplicateColumnNameWarning):
            d2txt = D2TXT.load_txt(
                StringIO(
                    "column name\tcolumn name 2\tcolumn name 2\t"
                    "column name\tcolumn name\tcolumn name 2\r\n"
                    "foo\tbar\tbar\tfoo\tfoo\tbar\r\n",
                    newline="",  # Required to make csv.reader work correctly
                )
            )

        expected_column_names = [
            "column name",
            "column name 2",
            "column name 2(C)",
            "column name(D)",
            "column name(E)",
            "column name 2(F)",
        ]
        self.assertEqual(list(d2txt.column_names()), expected_column_names)

    def test_column_name_case_preserving(self):
        """Tests if column names are case-preserved when loading a TXT file."""
        d2txt = D2TXT.load_txt(
            StringIO(
                "column name\tColumn Name\tCOLUMN NAME\r\n"
                "lowercase\tCapitalized\tUPPERCASE\r\n",
                newline="",  # Required to make csv.reader work correctly
            )
        )
        self.compare_d2txt(
            d2txt,
            ["column name", "Column Name", "COLUMN NAME"],
            [["lowercase", "Capitalized", "UPPERCASE"]],
        )

    def test_column_name_whitespace(self):
        """Tests if whitespace in columns are preserved when loading a TXT file.
        """
        d2txt = D2TXT.load_txt(
            StringIO(
                "   column 1\tcolumn 2    \t  column 3  \t\t  \r\n"
                "3 before\t4 after\t2 both\tempty\tspaces only\r\n",
                newline="",  # Required to make csv.reader work correctly
            )
        )
        self.compare_d2txt(
            d2txt,
            ["   column 1", "column 2    ", "  column 3  ", "", "  "],
            [["3 before", "4 after", "2 both", "empty", "spaces only"]],
        )

    def test_empty_cell(self):
        """Tests if D2TXT correctly loads empty cells and rows in a TXT file."""
        d2txt = D2TXT.load_txt(
            StringIO(
                "column 1\tcolumn 2\tcolumn 3\r\nempty\t\t\r\n\t\t\r\n",
                newline="",  # Required to make csv.reader work correctly
            )
        )
        self.compare_d2txt(
            d2txt,
            ["column 1", "column 2", "column 3"],
            [["empty", "", ""], ["", "", ""]],
        )

    def test_cell_whitespace(self):
        """Tests if whitespace in cells are preserved when loading a TXT file.
        """
        d2txt = D2TXT.load_txt(
            StringIO(
                "column 1\tcolumn 2\tcolumn 3\r\n"
                "  2 leading spaces\t3 trailing spaces   \t     \r\n",
                newline="",  # Required to make csv.reader work correctly
            )
        )
        self.compare_d2txt(
            d2txt,
            ["column 1", "column 2", "column 3"],
            [["  2 leading spaces", "3 trailing spaces   ", "     "]],
        )

    def test_surrounding_quotes(self):
        """Tests if surrounding quotes are preserved when loading a TXT file."""
        d2txt = D2TXT.load_txt(
            StringIO(
                "'single quotes'\t\"double quotes\"\t`backticks`\r\n"
                "'single quotes'\t\"double quotes\"\t`backticks`\r\n",
                newline="",  # Required to make csv.reader work correctly
            )
        )
        self.compare_d2txt(
            d2txt,
            ["'single quotes'", '"double quotes"', "`backticks`"],
            [["'single quotes'", '"double quotes"', "`backticks`"]],
        )

    def test_missing_cells(self):
        """Tests if missing cells corrected parsed when loading a TXT file."""
        d2txt = D2TXT.load_txt(
            StringIO(
                "column 1\tcolumn 2\tcolumn 3\r\n1 tab\t\r\nno tabs\r\n\r\n",
                newline="",  # Required to make csv.reader work correctly
            )
        )
        self.compare_d2txt(
            d2txt,
            ["column 1", "column 2", "column 3"],
            [["1 tab", "", None], ["no tabs", None, None], [None, None, None]],
        )


class TestD2TXTSaveFile(unittest.TestCase):
    """Contains tests that save D2TXT objects to TXT files."""

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

    def test_save_to_path(self):
        """Tests if D2TXT can be saved to a file path."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])
        d2txt.extend([["value 1", "value 2", "value 3"], ["foo", "bar", "baz"]])

        d2txt.to_txt(type(self).save_txt_path)
        # newline='' is required to make csv.writer work correctly
        with open(type(self).save_txt_path, newline="") as save_txt:
            saved_contents = save_txt.read()

        self.assertEqual(
            saved_contents,
            "column 1\tcolumn 2\tcolumn 3\r\n"
            "value 1\tvalue 2\tvalue 3\r\n"
            "foo\tbar\tbaz\r\n",
        )

    def test_save_to_file_object(self):
        """Tests if D2TXT can be saved to a file object."""
        d2txt = D2TXT(["column 1", "column 2", "column 3"])
        d2txt.extend([["value 1", "value 2", "value 3"], ["foo", "bar", "baz"]])

        # newline='' is required to make csv.writer work correctly
        txtfile = StringIO(newline="")
        d2txt.to_txt(txtfile)
        self.assertEqual(
            txtfile.getvalue(),
            "column 1\tcolumn 2\tcolumn 3\r\n"
            "value 1\tvalue 2\tvalue 3\r\n"
            "foo\tbar\tbaz\r\n",
        )

    def test_column_name_case_preserving(self):
        """Tests if column names are case-preserved when saved to a TXT file."""
        d2txt = D2TXT(["column name", "Column Name", "COLUMN NAME"])
        d2txt.extend([["lowercase", "Capitalized", "UPPERCASE"]])

        # newline='' is required to make csv.writer work correctly
        txtfile = StringIO(newline="")
        d2txt.to_txt(txtfile)
        self.assertEqual(
            txtfile.getvalue(),
            "column name\tColumn Name\tCOLUMN NAME\r\n"
            "lowercase\tCapitalized\tUPPERCASE\r\n",
        )

    def test_column_name_whitespace(self):
        """Tests if whitespace in columns are preserved when saved to a file."""
        d2txt = D2TXT(["   column 1", "column 2    ", "  column 3  ", "", "  "])
        d2txt.extend([["3 before", "4 after", "2 both", "empty", "spaces only"]])

        # newline='' is required to make csv.writer work correctly
        txtfile = StringIO(newline="")
        d2txt.to_txt(txtfile)
        self.assertEqual(
            txtfile.getvalue(),
            "   column 1\tcolumn 2    \t  column 3  \t\t  \r\n"
            "3 before\t4 after\t2 both\tempty\tspaces only\r\n",
        )

    def test_falsy_cell(self):
        """Tests if falsy values in cells are preserved when saved to a file.

        Tested values include None, integer 0, float 0.0, and False.
        """
        d2txt = D2TXT(["column 1", "column 2", "column 3"])
        d2txt.extend(
            [
                ["empty", "", ""],
                ["", "", ""],
                ["None", None, None],
                [None, None, None],
                ["integer 0", 0, 0],
                [0, 0, 0],
                ["float 0.0", 0.0, 0.0],
                [0.0, 0.0, 0.0],
                ["False", False, False],
                [False, False, False],
                ["truncated row"],
                [],
            ]
        )

        # newline='' is required to make csv.writer work correctly
        txtfile = StringIO(newline="")
        d2txt.to_txt(txtfile)
        self.assertEqual(
            txtfile.getvalue(),
            "column 1\tcolumn 2\tcolumn 3\r\n"
            "empty\t\t\r\n"
            "\t\t\r\n"
            "None\t\t\r\n"
            "\t\t\r\n"
            "integer 0\t0\t0\r\n"
            "0\t0\t0\r\n"
            "float 0.0\t0.0\t0.0\r\n"
            "0.0\t0.0\t0.0\r\n"
            "False\tFalse\tFalse\r\n"
            "False\tFalse\tFalse\r\n"
            "truncated row\t\t\r\n"
            "\t\t\r\n",
        )

    def test_cell_whitespace(self):
        """Tests if whitespace in cells are preserved when saved to a TXT file.
        """
        d2txt = D2TXT(["column 1", "column 2", "column 3"])
        d2txt.extend([["  2 leading spaces", "3 trailing spaces   ", "     "]])

        # newline='' is required to make csv.writer work correctly
        txtfile = StringIO(newline="")
        d2txt.to_txt(txtfile)
        self.assertEqual(
            txtfile.getvalue(),
            "column 1\tcolumn 2\tcolumn 3\r\n"
            "  2 leading spaces\t3 trailing spaces   \t     \r\n",
        )

    def test_surrounding_quotes(self):
        """Tests if surrounding quotes are preserved when saved to a TXT file.
        """
        d2txt = D2TXT(["'single quotes'", '"double quotes"', "`backticks`"])
        d2txt.extend([["'single quotes'", '"double quotes"', "`backticks`"]])

        # newline='' is required to make csv.writer work correctly
        txtfile = StringIO(newline="")
        d2txt.to_txt(txtfile)
        self.assertEqual(
            txtfile.getvalue(),
            "'single quotes'\t\"double quotes\"\t`backticks`\r\n"
            "'single quotes'\t\"double quotes\"\t`backticks`\r\n",
        )
