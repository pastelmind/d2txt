#!/usr/bin/env python

"""
Add formulas in 'skpoints' of Skills.txt that limit how skill points can be
invested into each skill.

Warning: These formulas do NOT play well with PlugY's skill point reallocation
feature and may destroy all skill points!

Note: This script modifies Skills.txt.
"""

import argparse
import sys

from d2txt import D2TXT


def make_ulvl_check_formula(ulvl_per_blvl, base_ulvl=0):
    """
    Returns a formula that checks if player level is same or greater than
    ulvl_per_blvl * blvl + base_ulvl.
    """
    if ulvl_per_blvl:
        formula = f"ulvl >= {ulvl_per_blvl} * blvl"
        if base_ulvl > 0:
            formula += f" + {base_ulvl}"
        elif base_ulvl < 0:
            formula += f" - {-base_ulvl}"
    elif base_ulvl > 1:
        formula = f"ulvl >= {base_ulvl}"
    else:
        formula = ""

    return formula


def make_prereq_level_check_formulas(skill, reqskill_level):
    """
    Returns a list of formulas that check if each of the given skill's
    reqskills, if any, have a base level same or greater than reqskill_level.
    """
    if reqskill_level <= 1:
        return ""
    reqskills = [skill["reqskill1"], skill["reqskill2"], skill["reqskill3"]]
    return [f"skill('{r}'.blvl) >= {reqskill_level}" for r in filter(None, reqskills)]


def combine_skpoints_check_formula(formulas):
    """
    Returns a combined formula for the `skpoints` column that allows a skill to
    be invested in only if all of the given formulas evaluate to true.
    """
    formulas = list(filter(None, formulas))
    if not formulas:
        return ""
    if len(formulas) > 1:
        formulas = "(" + ") * (".join(formulas) + ")"
    else:
        formulas = formulas[0]
    return f"({formulas}) ? 1 : 999"


def main(argv):
    """Entrypoint of the command line script."""
    arg_parser = argparse.ArgumentParser(description=__doc__)
    arg_parser.add_argument("skills_txt", help="Path to Skills.txt")
    arg_parser.add_argument(
        "--ulvl-per-blvl",
        type=int,
        help="If provided, specifies ulvl requirement per current skill blvl",
    )
    arg_parser.add_argument(
        "--use-reqlevel-as-base",
        action="store_true",
        help="If set, use reqlevel in Skills.txt as the base ulvl requirement",
    )
    arg_parser.add_argument(
        "--reqskill-level",
        type=int,
        help="If provided, specifies minimum blvl of all reqskills as a requirement",
    )

    args = arg_parser.parse_args(argv)

    skills_txt = D2TXT.load_txt(args.skills_txt)
    num_skills_updated = 0

    for skill in skills_txt:
        # Skip skills not owned by player classes
        if not skill["charclass"]:
            continue

        formulas = []

        if args.ulvl_per_blvl:
            base_ulvl = 0
            if args.use_reqlevel_as_base:
                reqlevel = int(skill["reqlevel"])
                if reqlevel > 1:
                    base_ulvl = reqlevel
            formulas.append(make_ulvl_check_formula(args.ulvl_per_blvl, base_ulvl))

        if args.reqskill_level:
            formulas += make_prereq_level_check_formulas(skill, args.reqskill_level)

        skill["skpoints"] = combine_skpoints_check_formula(formulas)
        num_skills_updated += 1

    skills_txt.to_txt(args.skills_txt)
    print(f"{num_skills_updated} skill(s) updated in {args.skills_txt}")


if __name__ == "__main__":
    main(sys.argv[1:])
