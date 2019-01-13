#!/usr/bin/env python

from d2txt import D2TXT
from colorama import init, Fore

init()



def walk_item_types(itype_code, item_types_txt):
    if not itype_code:
        return []
    itypes_found = [itype_code]
    for item_type in item_types_txt:
        if item_type['Code'] == itype_code:
            ancestor_itypes_1 = walk_item_types(item_type['Equiv1'], item_types_txt)
            ancestor_itypes_2 = walk_item_types(item_type['Equiv2'], item_types_txt)
            itypes_found += ancestor_itypes_1 + ancestor_itypes_2
    return itypes_found


item_types_txt = D2TXT()
weapons_txt = D2TXT()

TXT_DIR_PATH = '../../../Downloads/D2/PlugY-test/data/global/excel/'
item_types_txt.load_txt(TXT_DIR_PATH + 'ItemTypes.txt')
weapons_txt.load_txt(TXT_DIR_PATH + '/Weapons.txt')


one_handers = set()
two_handers = set()

for weapon in weapons_txt:
    name = weapon['name']
    code = weapon['code']
    if not code:
        continue
    type1 = weapon['type']
    type2 = weapon['type2']

    if weapon['2handed']:
        target_group = two_handers
    else:
        target_group = one_handers

    ancestor_itypes = walk_item_types(type1, item_types_txt) + walk_item_types(type2, item_types_txt)
    for itype in ancestor_itypes:
        target_group.add(itype)

mixed_types = one_handers & two_handers
one_handers -= mixed_types
two_handers -= mixed_types

print('One-handers: ' + ','.join(one_handers))
print('Two-handers: ' + ','.join(two_handers))
print('Mixed bags : ' + ','.join(mixed_types))


# Build type tree

itype_nodes = {}
for itype_entry in item_types_txt:
    code = itype_entry['Code']
    if not code:
        continue
    if code in itype_nodes:
        raise KeyError(f'Duplicate itype code {code} found')
    itype_node = {'code': code, 'subtypes': [], 'parents': []}
    itype_equivs = [itype_entry['Equiv1'], itype_entry['Equiv2']]
    itype_node['parents'] = [equiv for equiv in itype_equivs if equiv]
    itype_nodes[code] = itype_node

descendant_itypes = set()
for code, itype_node in itype_nodes.items():
    if itype_node['parents']:
        descendant_itypes.add(code)
        for parent_code in itype_node['parents']:
            parent_node = itype_nodes[parent_code]
            parent_node['subtypes'].append(itype_node)

for descendant_code in descendant_itypes:
    del itype_nodes[descendant_code]


def print_itype_tree(itype_node, current_depth=0):
    if not itype_node:
        return
    output_str = ' ' * (4 * current_depth) + itype_node['code']
    if itype_node['code'] in one_handers:
        output_str = Fore.GREEN + output_str + ' <-- 1h' + Fore.RESET
    elif itype_node['code'] in two_handers:
        output_str = Fore.CYAN + output_str + ' <-- 2h' + Fore.RESET
    print(output_str)
    for child_type in itype_node['subtypes']:
        print_itype_tree(child_type, current_depth + 1)

for root_node in itype_nodes.values():
    print_itype_tree(root_node)