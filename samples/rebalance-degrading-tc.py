#!/usr/bin/env python

"""
Rebalances "degrading" treasureclasses by setting each TC's chance to degrade
equal to the sum of all `ProbN` fields of the degraded TC.

For example, if TC 1 has `Prob3=TC 2`, this script sets `Prob3` equal to the sum
of all `ProbN` fields of TC 2. This makes each `ProbN` field in TC 2 have equal
weight as those in TC 1.

Note: This script modifies TreasureClassEx.txt.
"""


import sys
from os import path

sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), "..")))

from d2txt import D2TXT
import re


class DuplicateKeyError(Exception):
    pass


def make_tc_dict(tcex_txt):
    """Returns a dictionary of rows in TreasureClassEx.txt keyed by name."""
    tc_dict = {}
    for tc in tcex_txt:
        name = tc["Treasure Class"]
        if name in tc_dict:
            raise DuplicateKeyError(name)
        tc_dict[name] = tc
    return tc_dict


TC_PROB_COLUMNS = {f"Item{i}": f"Prob{i}" for i in range(1, 11)}


def sum_probs(tc):
    """Returns the sum of all `ProbN` fields in the given treasureclass row."""
    total_probs = 0
    for item_col, prob_col in TC_PROB_COLUMNS.items():
        if not tc[item_col]:
            continue
        total_probs += int(tc[prob_col])
    return total_probs


def match_in_patterns(text, patterns):
    """Tests if a string matches any regex pattern in the given list."""
    return any(pattern.search(text) for pattern in patterns)


if __name__ == "__main__":
    import argparse

    arg_parser = argparse.ArgumentParser(description=__doc__)
    arg_parser.add_argument("tcex_txt", help="Path to TreasureClassEx.txt")
    arg_parser.add_argument(
        "pattern", nargs="+", help="Regex for names of treasureclasses to rebalance"
    )
    arg_parser.add_argument(
        "-i", "--ignore-case", action="store_true", help="Use case-insensitive matching"
    )

    args = arg_parser.parse_args()

    tcex_txt = D2TXT.load_txt(args.tcex_txt)
    tc_dict = make_tc_dict(tcex_txt)

    re_flags = 0
    if args.ignore_case:
        re_flags = re.IGNORECASE

    tc_patterns = []
    for pattern_index, pattern_str in enumerate(args.pattern):
        print(f"Pattern {pattern_index + 1}: {repr(pattern_str)}")
        tc_patterns.append(re.compile(pattern_str, flags=re_flags))

    num_matched_tcs = 0
    num_rebalanced_tcs = 0
    for tc in tcex_txt:
        name = tc["Treasure Class"]
        if not match_in_patterns(name, tc_patterns):
            continue

        num_matched_tcs += 1

        # Rebalance treasureclasses from top to bottom. Since a treasureclass
        # can only refer to other TCs above its row, we assume that all previous
        # TCs have already been rebalanced.
        for item_col, prob_col in TC_PROB_COLUMNS.items():
            item_name = tc[item_col]
            if not item_name:
                continue
            if item_name in tc_dict and match_in_patterns(item_name, tc_patterns):
                tc[prob_col] = sum_probs(tc_dict[item_name])
                num_rebalanced_tcs += 1

    tcex_txt.to_txt(args.tcex_txt)
    print(
        f"{num_matched_tcs} treasureclass(es) matched, {num_rebalanced_tcs} treasureclass(es) rebalanced."
    )

