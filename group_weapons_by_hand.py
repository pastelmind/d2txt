#!/usr/bin/env python

'''Assign 1hwp/2hwp to all weapons based on their 1/2-handedness.'''

from d2txt import D2TXT


weapons_txt = D2TXT()

WEAPONS_TXT_PATH = '../../../Downloads/D2/PlugY-test/data/global/excel/Weapons.txt'
weapons_txt.load_txt(WEAPONS_TXT_PATH)

for weapon_entry in weapons_txt:
    if not (weapon_entry['type'] and weapon_entry['code']):
        continue
    if weapon_entry['2handed']:
        weapon_entry['type2'] = '2hwp'
    else:
        weapon_entry['type2'] = '1hwp'

weapons_txt.to_txt(WEAPONS_TXT_PATH)