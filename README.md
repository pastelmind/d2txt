# d2txt

d2txt is a command line program that converts tabbed text (*.TXT) files used by [Diablo 2] into TOML files and back. It is intended to be a [mod-making][mod] tool.

d2txt requires Python 3.6 or higher.

To install d2txt, run the following command in your terminal:

```
pip install d2txt
```

## Command Line Interface

d2txt can "decompile" Diablo 2's tabbed TXT files to [TOML] files, and compile
them back to TXT files. TOML files are easier to view in code editors, generates
more readable diffs, and play nice with version control systems like Git.

Call the script using the command line:

```
d2txt decompile <txt_path> <toml_path> [<txt_path> <toml_path>...]
d2txt compile <toml_path> <txt_path> [<txt_path> <toml_path>...]
```

You can specify multiple files as arguments to (de)compile all of them at once.
This is significantly faster than calling the script for each file.

Diff logs for TXT files are horrendous. See example:

```diff
--- a/data/global/excel/skills.txt
+++ b/data/global/excel/skills.txt
@@ -67,7 +67,7 @@
 Teeth	67	nec	teeth		8												teeth																																																												necromancer_bone_cast														19	17					teeth	teeth	bonecast										1	1		none												SC	SC	xx																	1						necromancer_bone_cast			1	20													1						1	7	6	1	1										"min(ln12,24)"	# missiles	par3	activation frame					2	number of missiles	1	additional missiles/level	0	Acivation frame of teeth									15	damage synergy	1								7															mag	4	2	2	3	4	5	8	2	3	4	5	6	(skill('Bone Wall'.blvl)+skill('Bone Prison'.blvl)+skill('Bone Spear'.blvl)+skill('Bone Spirit'.blvl))*par8								256	1000
-Bone Armor	68	nec	bone armor		18																	bonearmor				bonearmor	(ln12 + (skill('Bone Wall'.blvl) + skill('Bone Prison'.blvl)) * par8)*256	bonearmormax	(ln12 + (skill('Bone Wall'.blvl) + skill('Bone Prison'.blvl)) * par8)*256									absorbdamage	22																																						necromancer_bonearmor																																1	3		none												SC	SC	xx																	1						necromancer_bonearmor			1	20																			1	8	11	1	1	1																	20	damage absorbed	10	additional absorbed/level											15	absorb synergy	1								8																																				256	1000
+Bone Armor	68	nec	bone armor		18																	bonearmor				bonearmor	(ln12 + (skill('Bone Wall'.blvl) + skill('Bone Prison'.blvl)) * par8)*256	bonearmormax	(ln12 + (skill('Bone Wall'.blvl) + skill('Bone Prison'.blvl)) * par8)*256									absorbdamage	22																																						necromancer_bonearmor																																1	3		none												SC	SC	xx																	1						necromancer_bonearmor			1	20																			1	8	11	1	1	1		1	100														20	damage absorbed	10	additional absorbed/level											15	absorb synergy	1								8																																				256	1000
 Skeleton Mastery	69	nec	skeleton mastery																																											skel_mastery																																																															1	0		none												SC	SC	xx																										1	20					Raise Skeleton														0	8	0	0	1						1												8	additional hit points/level	2	additional damage per level	5	hp% per level for revive	10	dmg% per level for revive									1								8																																				256	1000
```

TOML files make your diff logs readable:

```diff
--- a/toml/skills.toml
+++ b/toml/skills.toml
@@ -3729,6 +3729,8 @@
 lvlmana = 1
 interrupt = 1
 InTown = 1
+periodic = 1
+perdelay = 100
 Param1 = 20
 '*Param1 Description' = 'damage absorbed'
 Param2 = 10
```

### Column Groups

When decompiling TXT files, d2txt groups related columns into **column groups**.
For example, the columns named `MinDam`, `MinLevDam1`, `MinLevDam2`,
`MinLevDam3`, `MinLevDam4`, and `MinLevDam5` in Skills.txt are joined into a
single key named `--MinDam0-5`:

```toml
--MinDam0-5 = [100, 10, 15, 20, 25, 30]
# Equivalent to:
MinDam = 100
MinLevDam1 = 10
MinLevDam2 = 15
MinLevDam3 = 20
MinLevDam4 = 25
MinLevDam5 = 30
```

### Notes

- Each decompiled TOML file contains a list named `columns`, as well as a table
  named `column_groups` at the top of the file. Do not touch these, as they are
  used by `d2txt` to compile the TOML back to a TXT file.
- d2txt warns if a TXT file contains duplicate column names (e.g. the unused
  `mindam` and `maxdam` columns in **`Armor.txt`**). You must remove or rename
  such columns.
- While Diablo 2 treats column names in a case-insensitive manner, d2txt treats
  them case-sensitively. Since this is how Python and TOML handles strings,
  there are no plans to fix them.

## API Usage

d2txt can also be used programmatically to modify TXT files.

Use the `d2txt.D2TXT` class to read and write to tabbed *.TXT files.

To read a TXT file, use `D2TXT.load_txt()`:

```python
from d2txt import D2TXT

skills_txt = D2TXT.load_txt('./data/global/excel/Skills.txt')
```

A D2TXT object can be treated like a [sequence] of rows. Each row is a
collection of cells, which can be accessed by column name or index:

```python
# Fire Ball is in Row 49 of Skills.txt. Since Row 1 is the header row, and list
# indexes in Python begin at zero, Fire Ball would be at index 49 - 2 = 47.
fire_ball = skills_txt[47]

# Better way to find Fire Ball (will raise StopIteration if none is found)
# Not: If you want to do this a lot, consider building a dict() for fast lookups
fire_ball = next(s for s in skills_txt if s['skill'] == 'Fire Ball')

# Directly read and write each cell
print(skills_txt[47]['EType'])      # prints "fire"
print(fire_ball['EType'])           # prints "fire"

skills_txt[47]['EType'] = 'ltng'    # Change damage element to lightning
fire_ball['EType'] = 'ltng'         # Same as above

# To "erase" a cell, set it to '', 0, or any falsy value.
skills_txt[47]['EType'] = ''

# Let's double Fire Ball's mana cost.
# Each cell value is initially a string, but you can assign other values.
fire_ball['mana'] = int(fire_ball['mana']) * 2
fire_ball['lvlmana'] = int(fire_ball['lvlmana']) * 2

# Let's triple Fire Ball's damage.
fire_ball['EMin'] = int(fire_ball['EMin']) * 3
fire_ball['EMax'] = int(fire_ball['EMax']) * 3

for i in range(1, 6):
    # Uses Python 3.6 f-strings
    fire_ball[f'EMinLev{i}'] = int(fire_ball[f'EMinLev{i}']) * 3
    fire_ball[f'EMaxLev{i}'] = int(fire_ball[f'EMaxLev{i}']) * 3
```

*Note: Column names are case sensitive.*

To save the modified TXT file:

```python
# This will overwrite Skills.txt. You can save it to another file if you wish.
D2TXT.to_txt('./data/global/excel/Skills.txt')
```

For more examples, check out the scripts in the `/samples/` directory.

### Notes

- You cannot add, rename, or remove columns with D2TXT. This is an intentional
  design choice that makes D2TXT faster than [`csv.DictReader`].

[TOML]: https://github.com/toml-lang/toml
[`csv.DictReader`]: https://docs.python.org/3/library/csv.html#csv.DictReader
[mod]: https://en.wikipedia.org/wiki/Mod_(video_gaming)
[Diablo 2]: http://blizzard.com/diablo2/
[sequence]: https://docs.python.org/3/glossary.html#term-sequence

## Development

To develop d2txt, you will want a good Python editor. I recommend [Visual Studio Code] with the [Microsoft Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python).

To develop d2txt, clone this repository and create a [virtual environment]. Then run the following command to install development dependencies:

```sh
# For Windows
python -m pip install -r requirements-dev.txt
# For non-Windows
pip install -r requirements-dev.txt
```

To run tests within VS Code, you must install d2txt in "development" mode:

```sh
# For Windows
flit install --pth-file
# For non-Windows
flit install
```

d2txt uses the following tools for development.

* [Flit] to build source distributions and wheels.
* [Tox] to run tests.
* [Black] and [isort] to format code.
* [Pylint] to check code.

[Black]: https://github.com/psf/black
[Flit]: https://flit.readthedocs.io/
[isort]: https://timothycrosley.github.io/isort/
[Pylint]: https://www.pylint.org/
[Tox]: https://tox.readthedocs.io/
[virtual environment]: https://packaging.python.org/tutorials/installing-packages/#creating-virtual-environments
[Visual Studio Code]: https://code.visualstudio.com/
