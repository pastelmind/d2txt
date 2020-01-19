#!/usr/bin/env python
"""Provides the D2TXT class for loading and saving Diablo 2 TXT files."""

import collections.abc
import csv
from itertools import islice
from typing import Any
from typing import Union
from warnings import warn

import qtoml
import toml


class DuplicateColumnNameWarning(Warning):
    """A warning issued when a duplicate column name is encountered and has been
    renamed."""


def _column_index_to_symbol(column_index):
    """Converts a 0-indexed column index to an Excel-style column symbol string
    (A, B, ..., Z, AA, AB, ...)."""
    column_symbol = ''
    while column_index >= 0:
        modulo = column_index % 26
        column_symbol = chr(modulo + ord('A')) + column_symbol
        column_index = (column_index - modulo) // 26 - 1
    return column_symbol


class D2TXTRow(collections.abc.Mapping):
    """
    Represents a single row in a tabbed txt file.
    """

    def __init__(self, d2txt, row):
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

    def __getitem__(self, key):
        return self._row[self._d2txt.column_index(key)]

    def __iter__(self):
        return iter(self._d2txt.column_names())

    def __len__(self):
        return len(self._row)

    def __setitem__(self, key, value):
        self._row[self._d2txt.column_index(key)] = value


class D2TXTColumnNameView(collections.abc.Sequence):
    """A read-only view of the list of column names in a D2TXT object."""

    def __init__(self, column_names):
        self._column_names = column_names

    def __getitem__(self, index):
        return self._column_names[index]

    def __len__(self):
        return len(self._column_names)

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self._column_names!r}>'


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
        self._column_indices = {
            name: index for index, name in enumerate(self._column_names)
        }
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
            self._rows[index] = [D2TXTRow(self, row) for row in value]
        else:
            self._rows[index] = D2TXTRow(self, value)

    def __delitem__(self, index):
        """Deletes a row at the given index, or multiple rows if slice syntax
        is used."""
        del self._rows[index]

    def insert(self, index, value):
        self._rows.insert(index, D2TXTRow(self, value))

    def column_names(self):
        """Returns a read-only view of the list of column names."""
        return D2TXTColumnNameView(self._column_names)

    def column_index(self, column_name):
        """Returns the index of the column with the given name. Raises KeyError
        if no match is found.

        Args:
            column_name: Column name string.
        """
        return self._column_indices[column_name]

    @classmethod
    def load_txt(cls, txtfile):
        """Creates a D2TXT object from a tabbed TXT file.

        Args:
            txtfile: A path string or readable file object
        """
        if isinstance(txtfile, str):
            with open(txtfile) as txtfile_obj:
                return cls.load_txt(txtfile_obj)

        txt_reader = csv.reader(
            txtfile, dialect='excel-tab', quoting=csv.QUOTE_NONE, quotechar=None
        )

        # Manually dedupe column names to ensure that warnings point to correct
        # lines in the source code
        d2txt = cls(cls.dedupe_column_names(next(txt_reader)))
        d2txt.extend(txt_reader)
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

        txt_writer = csv.writer(
            txtfile, dialect='excel-tab', quoting=csv.QUOTE_NONE, quotechar=None
        )
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
                new_name = f'{name}({_column_index_to_symbol(column_index)})'
                while new_name in column_names_seen:
                    new_name += f'({_column_index_to_symbol(column_index)})'
                warn(
                    f'Column name {name!r} replaced with {new_name!r}',
                    DuplicateColumnNameWarning, stacklevel=3
                )
                name = new_name
            column_names_seen.add(name)
            deduped_column_names.append(name)

        return deduped_column_names


def _int_or_str(value: str) -> Union[str, int]:
    """Attempts to convert a string to integer.

    Args:
        value: String to convert.

    Returns:
        Integer if the conversion is successful. On failure, returns the
        original string.
    """
    try:
        return int(value)
    except ValueError:
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
            'rows': [
                {
                    key: _int_or_str(value)
                    for key, value in row.items()
                    if not (value is None or value == '')
                }
                for row in d2txt
            ],
        }
    )
    toml_encoder = qtoml.encoder.TOMLEncoder()
    toml_columns = (
        'columns = [\n'
        + ''.join(
            f'  {toml_encoder.dump_value(key)},\n'
            for key in d2txt.column_names()
        )
        + ']\n\n'
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
    d2txt_data = D2TXT(D2TXT.dedupe_column_names(toml_data['columns']))
    for row in toml_data['rows']:
        d2txt_data.append([])
        d2txt_row = d2txt_data[-1]
        for key, value in row.items():
            d2txt_row[key] = value
    return d2txt_data
