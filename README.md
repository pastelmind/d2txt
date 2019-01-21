# D2TXT README

D2TXT is a set of Python scripts that can be used to make [mods][mod] for
[Diablo 2]. It consists of two modules: `d2txt.py` and `d2ini.py`.

D2TXT requires Python 3.

## d2txt.py

This module provides the `D2TXT` class, which can be used to read and write to
tabbed *.TXT files used by Diablo 2.

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

## d2ini.py

This script converts tabbed TXT files to and from INI files. INI files are
easier to view in code editors, generate better diffs, and play nice with
version control systems such as Git.

Call the script using the command line:

```
./d2txt.py decompile <txt_path> <ini_path>
./d2txt.py compile <ini_path> <txt_path>
```

Diff logs for TXT files are horrendous:

```diff
--- a/data/global/excel/skills.txt
+++ b/data/global/excel/skills.txt
@@ -67,7 +67,7 @@
 Teeth	67	nec	teeth		8												teeth																																																												necromancer_bone_cast														19	17					teeth	teeth	bonecast										1	1		none												SC	SC	xx																	1						necromancer_bone_cast			1	20													1						1	7	6	1	1										"min(ln12,24)"	# missiles	par3	activation frame					2	number of missiles	1	additional missiles/level	0	Acivation frame of teeth									15	damage synergy	1								7															mag	4	2	2	3	4	5	8	2	3	4	5	6	(skill('Bone Wall'.blvl)+skill('Bone Prison'.blvl)+skill('Bone Spear'.blvl)+skill('Bone Spirit'.blvl))*par8								256	1000
-Bone Armor	68	nec	bone armor		18																	bonearmor				bonearmor	(ln12 + (skill('Bone Wall'.blvl) + skill('Bone Prison'.blvl)) * par8)*256	bonearmormax	(ln12 + (skill('Bone Wall'.blvl) + skill('Bone Prison'.blvl)) * par8)*256									absorbdamage	22																																						necromancer_bonearmor																																1	3		none												SC	SC	xx																	1						necromancer_bonearmor			1	20																			1	8	11	1	1	1																	20	damage absorbed	10	additional absorbed/level											15	absorb synergy	1								8																																				256	1000
+Bone Armor	68	nec	bone armor		18																	bonearmor				bonearmor	(ln12 + (skill('Bone Wall'.blvl) + skill('Bone Prison'.blvl)) * par8)*256	bonearmormax	(ln12 + (skill('Bone Wall'.blvl) + skill('Bone Prison'.blvl)) * par8)*256									absorbdamage	22																																						necromancer_bonearmor																																1	3		none												SC	SC	xx																	1						necromancer_bonearmor			1	20																			1	8	11	1	1	1		1	100														20	damage absorbed	10	additional absorbed/level											15	absorb synergy	1								8																																				256	1000
 Skeleton Mastery	69	nec	skeleton mastery																																											skel_mastery																																																															1	0		none												SC	SC	xx																										1	20					Raise Skeleton														0	8	0	0	1						1												8	additional hit points/level	2	additional damage per level	5	hp% per level for revive	10	dmg% per level for revive									1								8																																				256	1000
```

INI files make your diff logs readable:

```diff
--- a/ini/skills.ini
+++ b/ini/skills.ini
@@ -3729,6 +3729,8 @@
 lvlmana=1
 interrupt=1
 InTown=1
+periodic=1
+perdelay=100
 Param1=20
 *Param1 Description=damage absorbed
 Param2=10
```

### Notes

- Don't touch the first section (`[Columns]`) in the INI file. It is used to
  restore the order of columns when converting from INI to TXT.
- If you have empty or duplicate column names in your TXT file, they will be
  automatically renamed to ensure that the script works correctly.
- Don't use backticks (`` ` ``) in your TXT files, as they are used to preserve
  cells that contain leading or trailing spaces.


[mod]: https://en.wikipedia.org/wiki/Mod_(video_gaming)
[Diablo 2]: http://blizzard.com/diablo2/
[sequence]: https://docs.python.org/3/glossary.html#term-sequence