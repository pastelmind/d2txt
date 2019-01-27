#!/usr/bin/env python

"""Provides the D2TXT class for loading and saving Diablo 2 TXT files."""


import csv
import collections.abc
from itertools import islice
from warnings import warn


class DuplicateColumnNameWarning(Warning):
    """A warning issued when a duplicate column name is encountered and has been
    renamed."""
    pass


def _column_index_to_str(column_index):
    """Converts a 1-indexed column number to an Excel-style column name string
    (A, B, ...)."""
    column_name = ''
    while column_index > 0:
        modulo = (column_index - 1) % 26
        column_name = chr(modulo + ord('A')) + column_name
        column_index = (column_index - modulo) // 26
    return column_name


class D2TXTRow(collections.abc.Mapping):
    """
    Represents a single row in a tabbed txt file.
    """

    def __init__(self, row, column_names):
        """Creates a row object for D2TXT.

        Args:
            row: Iterable of values to fill the row with.
            column_names: Iterable of column name strings.
        """
        self._column_names = list(column_names)
        num_columns = len(self._column_names)
        self._row = list(islice(row, num_columns))
        self._row += [None] * (num_columns - len(self._row))

    def __getitem__(self, key):
        try:
            index = self._column_names.index(key)
        except ValueError:
            raise KeyError(key) from None
        return self._row[index]

    def __iter__(self):
        return iter(self._column_names)

    def __len__(self):
        return len(self._row)

    def __setitem__(self, key, value):
        try:
            index = self._column_names.index(key)
        except ValueError:
            raise KeyError(key) from None
        self._row[index] = value


class D2TXT(collections.abc.MutableSequence):
    """
    Represents a tab-separated TXT file used in Diablo 2.
    """

    def __init__(self, column_names):
        """Create a D2TXT object.

        Args:
            column_names: An iterable of column name strings. Duplicate column
                names are automatically renamed.
        """
        self._column_names = self.__class__.dedupe_column_names(column_names)
        self._rows = []

    # def col(self, column_name):
    #     pass

    def __getitem__(self, index):
        """Returns a row at the given index, or a `list` of rows if slice syntax
        is used."""
        return self._rows[index]

    def __len__(self):
        return len(self._rows)

    def __setitem__(self, index, value):
        """Sets a row at the given index to `value`. If slice syntax is used,
        replaces the rows with each item in `value`."""
        if isinstance(index, slice):
            self._rows[index] = [D2TXTRow(row, self._column_names) for row in value]
        else:
            self._rows[index] = D2TXTRow(value, self._column_names)

    def __delitem__(self, index):
        """Deletes a row at the given index, or multiple rows if slice syntax
        is used."""
        del self._rows[index]

    def insert(self, index, value):
        self._rows.insert(index, D2TXTRow(value, self._column_names))


    def column_names(self):
        """Returns an iterator of column names in order."""
        return iter(self._column_names)


    @classmethod
    def load_txt(cls, txtfile):
        """Creates a D2TXT object from a tabbed TXT file.

        Args:
            txtfile: A path string or readable file object
        """
        if isinstance(txtfile, str):
            with open(txtfile) as txtfile_obj:
                return cls.load_txt(txtfile_obj)

        txt_reader = csv.reader(txtfile, dialect='excel-tab',
            quoting=csv.QUOTE_NONE, quotechar=None)

        # Manually dedupe column names to ensure that warnings point to correct
        # lines in the source code
        d2txt = cls(cls.dedupe_column_names(next(txt_reader)))
        d2txt._rows = [D2TXTRow(row, d2txt._column_names) for row in txt_reader]
        return d2txt


    def to_txt(self, txtfile):
        """Writes the contents of this object to a TXT file.

        Args:
            txtfile: A path string or writable file object
        """
        if isinstance(txtfile, str):
            with open(txtfile, mode='w', newline='') as txtfile_obj:
                self.to_txt(txtfile_obj)
                return

        txt_writer = csv.writer(txtfile, dialect='excel-tab',
            quoting=csv.QUOTE_NONE, quotechar=None)
        txt_writer.writerow(self._column_names)
        txt_writer.writerows(row.values() for row in self._rows)


    @staticmethod
    def dedupe_column_names(column_names):
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
                new_name = f'{name}({_column_index_to_str(column_index + 1)})'
                while new_name in column_names_seen:
                    new_name += f'({_column_index_to_str(column_index + 1)})'
                warn(f'Column name {name!r} replaced with {new_name!r}',
                    DuplicateColumnNameWarning, stacklevel=3)
                name = new_name
            column_names_seen.add(name)
            deduped_column_names.append(name)

        return deduped_column_names