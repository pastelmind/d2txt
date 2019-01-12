#!/usr/bin/env python

'''Unit test for d2txt.py'''


import unittest
from d2txt import D2TXT
import os
from os import path


class TestD2TXT(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._sample_txt_path = path.join(path.dirname(path.abspath(__file__)), 'sample.txt')
        cls._d2txt = D2TXT.load_txt(cls._sample_txt_path)

    def test1_EverythingIsLoaded(self):
        '''Tests that all rows and columns have been loaded.'''
        d2txt = self.__class__._d2txt
        column_count = len(d2txt.column_names())

        self.assertEqual(column_count, 5, '# of columns is different than expected')
        self.assertEqual(len(d2txt), 4, '# of rows is different than expected')

        for row_index, row in enumerate(d2txt):
            self.assertEqual(len(row), column_count,
                f'Row {row_index + 1} length is not equal to # of columns ({column_count})')

    def test_ColumnNameIsCaseSensitive(self):
        '''Tests that column names are case sensitive.'''
        d2txt = self.__class__._d2txt
        self.assertEqual(d2txt.column_names()[0], 'Column Name')
        self.assertEqual(d2txt.column_names()[4], 'column name')
        self.assertNotEqual(d2txt[0, 'Column Name'], d2txt[0, 'column name'])
        with self.assertRaises(KeyError):
            d2txt[0, 'column Name']

    def test_EmptyColumnName(self):
        '''Tests that empty column names are escaped appropriately'''
        d2txt = self.__class__._d2txt
        self.assertEqual(d2txt.column_names()[3], '(colD)')

    def test_DuplicateColumnNames(self):
        '''Tests that duplicate column names are escaped appropriately'''
        d2txt = self.__class__._d2txt
        self.assertEqual(d2txt.column_names()[1], 'Duplicate column name')
        self.assertEqual(d2txt.column_names()[2], 'Duplicate column name(C)')

    def test_SaveTxt(self):
        '''
        Tests that saving and loading TXT files do not modify their contents.
        '''
        d2txt = self.__class__._d2txt
        current_dir_path = path.dirname(path.abspath(__file__))

        # Save D2TXT to a temporary TXT file
        sample_saved_txt_path = path.join(current_dir_path, 'sample_temp.txt')
        d2txt.to_txt(sample_saved_txt_path)

        sample_txt = open(self.__class__._sample_txt_path)
        sample_saved_txt = open(sample_saved_txt_path)

        # Skip the first line (column names)
        next(sample_txt)
        next(sample_saved_txt)

        for row_index, sample_line in enumerate(sample_txt):
            self.assertEqual(sample_line, next(sample_saved_txt),
                f'Row ${row_index + 1} has been corrupted by saving/loading')

        # Close file objects and delete the temporary TXT file
        sample_txt.close()
        sample_saved_txt.close()
        os.remove(sample_saved_txt_path)