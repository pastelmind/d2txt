#!/usr/bin/env python

"""Reads ItemTypes.txt, Weapons.txt and prints graphs of the item type hierarchy."""

import argparse
import sys

import colorama
from colorama import Fore

from d2txt import D2TXT

colorama.init()


class ITypeNode:
    """Represents a node in an itype tree."""

    # pylint: disable= too-few-public-methods

    def __init__(self, code):
        self.code = code
        self.children = []
        self.parents = []

    def ancestor_codes(self):
        """Returns a list of all ancestor itype codes, including this itype."""
        codes = [self.code]
        for parent_node in self.parents:
            codes += parent_node.ancestor_codes()
        return codes


def parse_itypes(item_types_txt):
    """
    Reads each item type in ItemTypes.txt and builds a dictionary of ITypeNode
    objects keyed by itype code.
    """

    itype_nodes = {}
    parent_codes = {}

    for item_type in item_types_txt:
        code = item_type["Code"]
        if not code:
            continue
        if code in itype_nodes:
            raise KeyError(f"Duplicate itype code '{code}' found")

        node = itype_nodes[code] = ITypeNode(code)
        parent_code_list = parent_codes[code] = []
        if item_type["Equiv1"]:
            parent_code_list.append(item_type["Equiv1"])
        if item_type["Equiv2"]:
            parent_code_list.append(item_type["Equiv2"])

    # Link parents and children
    for code, node in itype_nodes.items():
        for p_code in parent_codes[code]:
            parent_node = itype_nodes[p_code]
            parent_node.children.append(node)
            node.parents.append(parent_node)

    return itype_nodes


def classify_itypes_by_hand(itype_nodes, weapons_txt):
    """
    Reads Weapons.txt and classifies item types into 3 groups:
    1-hand only, 2-hand only, and mixed.
    Weapons that can be both 1- and 2-hand are classified as 2-hand weapons.
    Item types not used by weapons are ignored.

    Returns:
        A tuple of 3 sets containing itype codes, in order:
        - Item types that contain only 1-hand weapons
        - Item types that contain only 2-hand weapons
        - Item types that have both 1- and 2-hand weapons
    """

    one_handers = set()
    two_handers = set()

    for weapon in weapons_txt:
        code = weapon["code"]
        if not code:
            continue

        if weapon["2handed"]:
            target_group = two_handers
        else:
            target_group = one_handers

        itype_codes = []
        if weapon["type"]:
            itype_codes += itype_nodes[weapon["type"]].ancestor_codes()
        if weapon["type2"]:
            itype_codes += itype_nodes[weapon["type2"]].ancestor_codes()

        target_group.update(itype_codes)

    mixed_types = one_handers & two_handers
    one_handers -= mixed_types
    two_handers -= mixed_types

    return one_handers, two_handers, mixed_types


def print_itype_tree(node, one_handers=None, two_handers=None, current_depth=0):
    """
    Prints a tree of itypes, starting at the given node as root.
    If one_handers and/or two_handers is specified, any itype code present in
    either collection is highlighted and marked with arrows.
    """
    if not node:
        return

    output_str = " " * (4 * current_depth) + node.code

    if one_handers and node.code in one_handers:
        output_str = Fore.GREEN + output_str + " <-- 1h" + Fore.RESET
    elif two_handers and node.code in two_handers:
        output_str = Fore.CYAN + output_str + " <-- 2h" + Fore.RESET

    print(output_str)

    for child in node.children:
        print_itype_tree(child, one_handers, two_handers, current_depth + 1)


def main(argv):
    """Entrypoint of the command line script."""
    arg_parser = argparse.ArgumentParser(__doc__)
    arg_parser.add_argument("itemtypes_txt", help="Path to ItemTypes.txt")
    arg_parser.add_argument("weapons_txt", help="Path to Weapons.txt")

    args = arg_parser.parse_args(argv)

    item_types_txt = D2TXT.load_txt(args.itemtypes_txt)
    weapons_txt = D2TXT.load_txt(args.weapons_txt)

    itype_nodes = parse_itypes(item_types_txt)

    one_handers, two_handers, mixed_types = classify_itypes_by_hand(
        itype_nodes, weapons_txt
    )
    print("One-handers: " + ", ".join(one_handers))
    print("Two-handers: " + ", ".join(two_handers))
    print("Mixed bags : " + ", ".join(mixed_types))
    print("-" * 80)

    for node in itype_nodes.values():
        if not node.parents:
            print_itype_tree(node, one_handers=one_handers, two_handers=two_handers)


if __name__ == "__main__":
    main(sys.argv[1:])
