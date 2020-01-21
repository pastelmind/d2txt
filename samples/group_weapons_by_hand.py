#!/usr/bin/env python

"""
Assigns item codes to `type2` of all weapons based on the number of hands required.

Note: This script modifies Weapons.txt.
"""

import argparse
import sys

from d2txt import D2TXT


def check_item_code(item_code):
    """Checks if item_code is a valid item code. Used to validate argparse options."""
    if not item_code:
        return ""

    error_msg = None
    if len(item_code) < 3:
        error_msg = f"Item code must be 3-4 characters; '{item_code}' is too short"
    elif len(item_code) > 4:
        error_msg = f"Item code must be 3-4 characters; '{item_code}' is too long"
    elif " " in item_code:
        error_msg = "Item code must not contain whitespace"
    elif item_code == "xxx":
        error_msg = f"{item_code} is not allowed"

    if error_msg:
        raise argparse.ArgumentTypeError(error_msg)
    return item_code


def main(argv):
    """Entrypoint of the command line script."""
    arg_parser = argparse.ArgumentParser(description=__doc__)

    arg_parser.add_argument("weapons_txt", help="Path to Weapons.txt")
    arg_parser.add_argument(
        "--1h",
        type=check_item_code,
        help="If provided, item code to assign to 1-hand weapons",
    )
    arg_parser.add_argument(
        "--2h",
        type=check_item_code,
        help="If provided, item code to assign to 2-hand weapons",
    )
    arg_parser.add_argument(
        "--both",
        type=check_item_code,
        help="If provided, item code to assign to 1-or-2-hand weapons",
    )

    args = vars(arg_parser.parse_args(argv))

    weapons_txt = D2TXT.load_txt(args["weapons_txt"])

    num_1h = num_2h = num_both = 0

    for row_index, weapon in enumerate(weapons_txt):
        if not (weapon["type"] and weapon["code"]):
            continue

        if weapon["type2"]:
            print(
                f"Warning: Row {row_index + 1} is skipped -- "
                f'{weapon["name"]} already has \'type2\' assigned.'
            )
            continue

        if weapon["1or2handed"]:
            item_code = args["both"]
            num_both += 1
        elif weapon["2handed"]:
            item_code = args["2h"]
            num_2h += 1
        else:
            item_code = args["1h"]
            num_1h += 1

        if item_code:
            weapon["type2"] = item_code

    weapons_txt.to_txt(args["weapons_txt"])

    if args["1h"]:
        print(f'\'{args["1h"]}\' has been assigned to {num_1h} 1-hand weapon(s)')
    if args["2h"]:
        print(f'\'{args["2h"]}\' has been assigned to {num_2h} 2-hand weapon(s)')
    if args["both"]:
        print(
            f'\'{args["both"]}\' has been assigned to {num_both} 1-or-2-hand weapon(s)'
        )


if __name__ == "__main__":
    main(sys.argv[1:])
