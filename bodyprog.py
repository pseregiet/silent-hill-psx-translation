#!/usr/bin/env python3

import sys
import struct
import json
import re
import ctypes
from collections import namedtuple
from common import *

_offset = 0x80024B60
BodyProg = OverlayInfo(0x000cf, 2635, "bodyprog")

# Memory occupied by the strings. We can place our strings anywhere in these
# regions as we will patch out the pointers.
data_banks = [
    # pointer     size
    [ 0x800261E0, 0x34   ],
    [ 0x80027DF8, 0x3A   ],
    [ 0x800262AC, 0x4A   ],
    [ 0x80027F14, 0x7E   ],
    [ 0x8002667C, 0x175C ],
]

misc_ptr_tables = {
    # pointer  count
    0x80026214: 0x8,
    #0x80027E34: 0x8,
    0x80027F94: 0x7,
}

inventory_options = {}

main_menu = {
    "main_pos": 0x800254EC,
    "main_txt": 0x800A9A8C,
    "diff_pos": 0x8002551C,
    "diff_txt": 0x800A9AA0,
}

def patch_item_name_pos(bodyprog: memoryview, val):
    code_ptr = [0x80051E64, 0x80051E78, 0x80051ED8]
    code_base = 0x24040000 # addiu $a0, $zero, val
    code = code_base | val
    for ptr in code_ptr:
        patch_u32(bodyprog, code, ptr - _offset)

def read_main_menu(bodyprog: memoryview):
    pos_table_ptr = main_menu["main_pos"]
    txt_table_ptr = main_menu["main_txt"]
    main_menu_entries = {}
    for i in range(4):
        posval = read_u8(bodyprog, pos_table_ptr + (i*1) - _offset)
        txtptr = read_uint32_le(bodyprog, txt_table_ptr + (i*4) - _offset) - _offset
        txt = nice_encode(read_c_string(bodyprog, txtptr))
        main_menu_entries[i] = { "txt": txt, "x": posval }
    main_menu["main_menu_entries"] = main_menu_entries

    pos_table_ptr = main_menu["diff_pos"]
    txt_table_ptr = main_menu["diff_txt"]
    diff_menu_entries = {}
    for i in range(3):
        posval = read_u8(bodyprog, pos_table_ptr + (i*1) - _offset)
        txtptr = read_uint32_le(bodyprog, txt_table_ptr + (i*4) - _offset) - _offset
        txt = nice_encode(read_c_string(bodyprog, txtptr))
        diff_menu_entries[i] = { "txt": txt, "x": posval }
    main_menu["diff_menu_entries"] = diff_menu_entries


def read_inventory_options(bodyprog: memoryview):
    txt_table_ptr = 0x80027E34
    pos_table_ptr = 0x80027DD8
    data = {}
    for i in range(8):
        posval = read_uint32_le(bodyprog, pos_table_ptr + (i*4) - _offset)
        txtptr = read_uint32_le(bodyprog, txt_table_ptr + (i*4) - _offset) - _offset
        txt = nice_encode(read_c_string(bodyprog, txtptr))
        x = (posval>>0 ) & 0xFFFF
        y = (posval>>16) & 0xFFFF
        data[i] = {
            "txt": txt,
            "x": ctypes.c_int16(x).value,
            "y": ctypes.c_int16(y).value,
        }
    return data


def patch_main_menu(bodyprog: memoryview):
    def work(count, pos_table_ptr, txt_table_ptr, new_data, old_data):
        for i in range(count):
            x = old_data[i]["x"]
            oldtxt = game_encode(old_data[i]["txt"])
            oldlen = accumulate_widths(oldtxt)

            dataline = new_data[str(i)]
            print(dataline["txt"])
            news = game_encode(dataline["txt"])
            newlen = accumulate_widths(news)

            x = int(x - ((oldlen - newlen)/2))

            txt_ptr = find_room_for_blob(news)
            patch_pointer(bodyprog, txt_ptr, txt_table_ptr - _offset + (i*4))
            patch_blob(bodyprog, news, txt_ptr - _offset)
            patch_u8(bodyprog, ctypes.c_uint8(x).value, pos_table_ptr + (i*1) - _offset)

    with open("./dump/main_menu_strings.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(data)
    work(4, main_menu["main_pos"], main_menu["main_txt"], data["main_menu"], main_menu["main_menu_entries"])
    work(3, main_menu["diff_pos"], main_menu["diff_txt"], data["diff_menu"], main_menu["diff_menu_entries"])


# Read some values before we patch anything
def init_patcher(bodyprog: memoryview):
    global inventory_options
    inventory_options = read_inventory_options(bodyprog)
    read_main_menu(bodyprog)

def find_room_for_blob(blob):
    blen = len(blob)
    for bank in data_banks:
        if bank[1] >= blen:
            bank[1] -= blen
            ret = bank[0]
            bank[0] += blen
            return ret
    raise MemoryError(f"No more memory for blob: {blob}")


# These are small strings that do not use a pointer table.
# Instead they use a direct pointer in the code, which requires patching
# The specific instructions.
def patch_code_pointer(bodyprog: memoryview, code_ptr, new_ptr):
    code1 = 0x3C020000 | (new_ptr >>16 & 0xFFFF) # lui     $v0, %hi(ptr)
    code2 = 0x24420000 | (new_ptr >>0  & 0xFFFF) # addiu   $v0, $v0, %lo(ptr)
    patch_pointer(bodyprog, code1, ((code_ptr+0) - _offset))
    patch_pointer(bodyprog, code2, ((code_ptr+4) - _offset))


code_patches_table = [
    # code addr   # string addr
    [ 0x8004F594, 0x800262AC ],
    [ 0x8004F5A0, 0x800262D0 ],
    [ 0x80051960, 0x80027F14 ],
    [ 0x8005196C, 0x80027F28 ],
]


def dump_inventory_options(bodyprog: memoryview):
    data = read_inventory_options(bodyprog)
    with open("./dump/inventory_options_strings.json", 'w') as f:
        json.dump(data, f, indent=4)

def dump_main_menu():
    data = {
        "main_menu":main_menu["main_menu_entries"],
        "diff_menu":main_menu["diff_menu_entries"],
    }
    with open("./dump/main_menu_strings.json", 'w') as f:
        json.dump(data, f, indent=4)


def patch_inventory_options(bodyprog: memoryview):
    txt_table_ptr = 0x80027E34
    pos_table_ptr = 0x80027DD8
    with open("./dump/inventory_options_strings.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    for i in range(8):
        oldposval = read_uint32_le(bodyprog, pos_table_ptr + (i*4) - _offset)
        x = inventory_options[i]["x"]
        y = inventory_options[i]["y"]
        oldtxt = game_encode(inventory_options[i]["txt"])
        oldlen = accumulate_widths(oldtxt)

        dataline = data[str(i)]
        news = game_encode(dataline["txt"])
        newlen = accumulate_widths(news)

        x = int(x + ((oldlen - newlen)/2))
        posval = ctypes.c_uint16(y).value << 16 | ctypes.c_uint16(x).value

        txt_ptr = find_room_for_blob(news)
        patch_pointer(bodyprog, txt_ptr, txt_table_ptr - _offset + (i*4))
        patch_blob(bodyprog, news, txt_ptr - _offset)
        patch_pointer(bodyprog, posval, pos_table_ptr + (i*4) - _offset)


def dump_small_strings(bodyprog: memoryview):
    data = {}
    for smallstr in code_patches_table:
        data[f"{smallstr[0]:x}"] = nice_encode(read_c_string(bodyprog, smallstr[1] - _offset))

    with open("./dump/small_strings.json", 'w') as f:
        json.dump(data, f, indent=4)


def dump_misc_strings(bodyprog: memoryview):
    data = {}
    for k, v in misc_ptr_tables.items():
        table = []
        for i in range(v):
            strptr = read_uint32_le(bodyprog, k + (4*i) - _offset)
            strptr -= _offset
            table.append(nice_encode(read_c_string(bodyprog, strptr)))
        data[f"{k:x}"] = table

    with open("./dump/misc_strings.json", 'w') as f:
        json.dump(data, f, indent=4)


def patch_inventory_misc(bodyprog: memoryview):
    with open("./dump/misc_strings.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    for tableptr, tablestr in data.items():
        tableptr = int(tableptr, 16) - _offset
        for s in tablestr:
            news = game_encode(s)
            txt_pointer = find_room_for_blob(news)
            patch_pointer(bodyprog, txt_pointer, tableptr)
            patch_blob(bodyprog, news, txt_pointer - _offset)
            tableptr = tableptr + 4


def patch_small_strings(bodyprog: memoryview):
    with open("./dump/small_strings.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    for codeptr, text in data.items():
        news = game_encode(text)
        txt_pointer = find_room_for_blob(news)
        patch_blob(bodyprog, news, txt_pointer - _offset)
        patch_code_pointer(bodyprog, int(codeptr, 16), txt_pointer)



#based on https://github.com/Vatuu/silent-hill-decomp/blob/master/tools/silentassets/extract.py
def xorBodyprog(silent: memoryview):
    bodyprog = extract_overlay(silent, BodyProg)
    outArray = bodyprog.cast("I") # uint32_t
    seed = 0

    for i, value in enumerate(outArray):
        seed = (seed + 0x01309125) & 0xffffffff
        seed = (seed * 0x03a452f7) & 0xffffffff
        outArray[i] ^= seed

    return bodyprog

def nice_encode(line):
    return line.replace('\t', '').replace('\n', '{~N}').replace('_', ' ')

def game_encode(line):
    line = line.replace(' ', '_').replace('{~N}', '\n')
    line = encode_local_text(line)
    return line.encode('ascii') + b'\x00'

def extract_inventory_messages(bodyprog: memoryview):
    item_names_ptr = 0x800ADB60 - _offset
    item_descs_ptr = 0x800ADE6C - _offset
    data = {}
    for i in range(200):
        try:
            in_ptr = read_uint32_le(bodyprog, item_names_ptr)
            id_ptr = read_uint32_le(bodyprog, item_descs_ptr)
            item_names_ptr += 4
            item_descs_ptr += 4
            if (in_ptr == 0 or id_ptr == 0):
                continue
            in_ptr -= _offset
            id_ptr -= _offset

            data[i] = {
                "name": nice_encode(read_c_string(bodyprog, in_ptr)),
                "desc": nice_encode(read_c_string(bodyprog, id_ptr))
            }
        except Exception as e:
            print(e)
            pass

    with open("./dump/inventory.json", 'w') as f:
        json.dump(data, f, indent=4)

def extract_font_width(bodyprog: memoryview):
    font_widths_offset = 0x80025D6C - _offset
    table = bodyprog[font_widths_offset: font_widths_offset + 84].cast('B')
    data = {}
    for i in range(84):
        char = chr(i+0x27)
        if char == '\\':
            char = '!'
        elif char == '^':
            char = '&'
        data[char] = table[i]

    with open("./dump/font_info.json", 'w') as f:
        json.dump(data, f, indent=4)

def patch_font_width(bodyprog: memoryview):
    font_widths_offset = 0x80025D6C - _offset
    table = bodyprog[font_widths_offset: font_widths_offset + 84].cast('B')
    with open("./dump/font_info.json", 'r') as f:
        data = json.load(f)

    for k, v in data.items():
        if k == '!':
            k = '\\'
        elif k == '&':
            k = '^'
        k = ord(k) - 0x27
        table[k] = v


def patch_left_quote(bodyprog: memoryview):
    # If we use the left quote (") for another localized glyph
    # we have to patch out few hardcoded uses of it from bodyprog
    mainmenu_left_quote = 0x800254F4 - _offset
    bodyprog[mainmenu_left_quote] = ord(']')



def patch_inventory(bodyprog: memoryview):
    item_names_ptr = 0x800ADB60 - _offset
    item_descs_ptr = 0x800ADE6C - _offset

    with open("./dump/inventory.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    for k, v in data.items():
        itemn_ptr = item_names_ptr + 4*int(k)
        itemd_ptr = item_descs_ptr + 4*int(k)
        name = game_encode(v['name'])
        desc = game_encode(v['desc'])

        txt_pointer = find_room_for_blob(name)
        patch_pointer(bodyprog, txt_pointer, itemn_ptr)
        patch_blob(bodyprog, name, txt_pointer - _offset)


        txt_pointer = find_room_for_blob(desc)
        patch_pointer(bodyprog, txt_pointer, itemd_ptr)
        patch_blob(bodyprog, desc, txt_pointer - _offset)




def dump_bodyprog(silent: memoryview):
    bodyprog = xorBodyprog(silent)
    init_patcher(bodyprog)
    extract_font_width(bodyprog)
    extract_inventory_messages(bodyprog)
    dump_small_strings(bodyprog)
    dump_misc_strings(bodyprog)
    dump_inventory_options(bodyprog)
    dump_main_menu()


def patch_bodyprog(silent: memoryview):
    bodyprog = xorBodyprog(silent)
    init_patcher(bodyprog)
    patch_inventory_options(bodyprog)
    patch_main_menu(bodyprog)
    patch_inventory(bodyprog)
    patch_font_width(bodyprog)
    patch_left_quote(bodyprog)
    patch_inventory_misc(bodyprog)
    patch_small_strings(bodyprog)
    patch_item_name_pos(bodyprog, 16)
    xorBodyprog(silent)

