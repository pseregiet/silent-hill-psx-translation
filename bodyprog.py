#!/usr/bin/env python3

import sys
import struct
import json
import re
import ctypes
from collections import namedtuple
from common import *
from ov_bodyprog import *


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

#based on https://github.com/Vatuu/silent-hill-decomp/blob/master/tools/silentassets/extract.py
def xorBodyProg(silent: memoryview):
    outArray = BodyProg.memory.cast("I") # uint32_t
    seed = 0

    for i, value in enumerate(outArray):
        seed = (seed + 0x01309125) & 0xffffffff
        seed = (seed * 0x03a452f7) & 0xffffffff
        outArray[i] ^= seed


def patch_item_name_pos(val):
    code_ptr = [0x80051E64, 0x80051E78, 0x80051ED8]
    code_base = 0x24040000 # addiu $a0, $zero, val
    code = code_base | val
    for ptr in code_ptr:
        w_u32(BodyProg, code, ptr)

def read_main_menu():
    pos_table_ptr = main_menu["main_pos"]
    txt_table_ptr = main_menu["main_txt"]
    main_menu_entries = {}
    for i in range(4):
        posval = r_u8(BodyProg, pos_table_ptr + (i*1))
        txtptr = r_u32(BodyProg, txt_table_ptr + (i*4))
        txt = nice_encode(read_c_string2(BodyProg, txtptr))
        main_menu_entries[i] = { "txt": txt, "x": posval }
    main_menu["main_menu_entries"] = main_menu_entries

    pos_table_ptr = main_menu["diff_pos"]
    txt_table_ptr = main_menu["diff_txt"]
    diff_menu_entries = {}
    for i in range(3):
        posval = r_u8(BodyProg, pos_table_ptr + (i*1))
        txtptr = r_u32(BodyProg, txt_table_ptr + (i*4))
        txt = nice_encode(read_c_string2(BodyProg, txtptr))
        diff_menu_entries[i] = { "txt": txt, "x": posval }
    main_menu["diff_menu_entries"] = diff_menu_entries


def read_inventory_options():
    txt_table_ptr = 0x80027E34
    pos_table_ptr = 0x80027DD8
    data = {}
    for i in range(8):
        posval = r_u32(BodyProg, pos_table_ptr + (i*4))
        txtptr = r_u32(BodyProg, txt_table_ptr + (i*4))
        txt = nice_encode(read_c_string2(BodyProg, txtptr))
        x = (posval>>0 ) & 0xFFFF
        y = (posval>>16) & 0xFFFF
        data[i] = {
            "txt": txt,
            "x": ctypes.c_int16(x).value,
            "y": ctypes.c_int16(y).value,
        }
    return data

def patch_main_menu():
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

            txt_ptr = get_new_blob_ptr(news, BodyProg)
            w_u32(BodyProg, txt_ptr, txt_table_ptr + (i*4))
            w_u8(BodyProg, ctypes.c_uint8(x).value, pos_table_ptr + (i*1))

    with open("./dump/main_menu_strings.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(data)
    work(4, main_menu["main_pos"], main_menu["main_txt"], data["main_menu"], main_menu["main_menu_entries"])
    work(3, main_menu["diff_pos"], main_menu["diff_txt"], data["diff_menu"], main_menu["diff_menu_entries"])


# Read some values before we patch anything
def init_patcher(silent: memoryview):
    extract_overlay2(silent, BodyProg)
    xorBodyProg(silent)
    global inventory_options
    inventory_options = read_inventory_options()
    read_main_menu()

# These are small strings that do not use a pointer table.
# Instead they use a direct pointer in the code, which requires patching
# The specific instructions.
def patch_code_pointer(code_ptr, new_ptr):
    code1 = 0x3C020000 | (new_ptr >>16 & 0xFFFF) # lui     $v0, %hi(ptr)
    code2 = 0x24420000 | (new_ptr >>0  & 0xFFFF) # addiu   $v0, $v0, %lo(ptr)
    w_u32(BodyProg, code1, (code_ptr+0))
    w_u32(BodyProg, code2, (code_ptr+4))


code_patches_table = [
    # code addr   # string addr
    [ 0x8004F594, 0x800262AC ],
    [ 0x8004F5A0, 0x800262D0 ],
    [ 0x80051960, 0x80027F14 ],
    [ 0x8005196C, 0x80027F28 ],
]


def dump_inventory_options():
    data = read_inventory_options()
    with open("./dump-new/inventory_options_strings.json", 'w') as f:
        json.dump(data, f, indent=4)

def dump_main_menu():
    data = {
        "main_menu":main_menu["main_menu_entries"],
        "diff_menu":main_menu["diff_menu_entries"],
    }
    with open("./dump-new/main_menu_strings.json", 'w') as f:
        json.dump(data, f, indent=4)


def patch_inventory_options():
    txt_table_ptr = 0x80027E34
    pos_table_ptr = 0x80027DD8
    with open("./dump/inventory_options_strings.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    for i in range(8):
        oldposval = r_u32(BodyProg, pos_table_ptr + (i*4))
        x = inventory_options[i]["x"]
        y = inventory_options[i]["y"]
        oldtxt = game_encode(inventory_options[i]["txt"])
        oldlen = accumulate_widths(oldtxt)

        dataline = data[str(i)]
        news = game_encode(dataline["txt"])
        newlen = accumulate_widths(news)

        x = int(x + ((oldlen - newlen)/2))
        posval = ctypes.c_uint16(y).value << 16 | ctypes.c_uint16(x).value

        txt_ptr = get_new_blob_ptr(news, BodyProg)
        w_u32(BodyProg, txt_ptr, txt_table_ptr + (i*4))
        w_u32(BodyProg, posval, pos_table_ptr + (i*4))


def dump_small_strings():
    data = {}
    for smallstr in code_patches_table:
        data[f"{smallstr[0]:x}"] = nice_encode(read_c_string2(BodyProg, smallstr[1]))

    with open("./dump-new/small_strings.json", 'w') as f:
        json.dump(data, f, indent=4)


def dump_misc_strings():
    data = {}
    for k, v in misc_ptr_tables.items():
        table = []
        for i in range(v):
            strptr = w_u32(BodyProg, k + (4*i))
            table.append(nice_encode(read_c_string2(BodyProg, strptr)))
        data[f"{k:x}"] = table

    with open("./dump-new/misc_strings.json", 'w') as f:
        json.dump(data, f, indent=4)


def patch_inventory_misc():
    with open("./dump/misc_strings.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    for tableptr, tablestr in data.items():
        tableptr = int(tableptr, 16)
        for s in tablestr:
            news = game_encode(s)
            txt_pointer = get_new_blob_ptr(news, BodyProg)
            w_u32(BodyProg, txt_pointer, tableptr)
            tableptr = tableptr + 4


def patch_small_strings():
    with open("./dump/small_strings.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    for codeptr, text in data.items():
        news = game_encode(text)
        txt_pointer = get_new_blob_ptr(news, BodyProg)
        patch_code_pointer(int(codeptr, 16), txt_pointer)



def extract_inventory_messages():
    item_names_ptr = 0x800ADB60
    item_descs_ptr = 0x800ADE6C
    data = {}
    for i in range(200):
        try:
            in_ptr = r_u32(BodyProg, item_names_ptr)
            id_ptr = r_u32(BodyProg, item_descs_ptr)
            item_names_ptr += 4
            item_descs_ptr += 4
            if (in_ptr == 0 or id_ptr == 0):
                continue

            data[i] = {
                "name": nice_encode(read_c_string2(BodyProg, in_ptr)),
                "desc": nice_encode(read_c_string2(BodyProg, id_ptr))
            }
        except Exception as e:
            print(e)
            pass

    with open("./dump-new/inventory.json", 'w') as f:
        json.dump(data, f, indent=4)

def extract_font_width():
    font_widths_offset = 0x80025D6C - BodyProg.offset
    table = BodyProg.memory[font_widths_offset: font_widths_offset + 84].cast('B')
    data = {}
    for i in range(84):
        char = chr(i+0x27)
        if char == '\\':
            char = '!'
        elif char == '^':
            char = '&'
        data[char] = table[i]

    with open("./dump-new/font_info.json", 'w') as f:
        json.dump(data, f, indent=4)

def patch_font_width():
    font_widths_offset = 0x80025D6C - BodyProg.offset
    table = BodyProg.memory[font_widths_offset: font_widths_offset + 84].cast('B')
    with open("./dump/font_info.json", 'r') as f:
        data = json.load(f)

    for k, v in data.items():
        if k == '!':
            k = '\\'
        elif k == '&':
            k = '^'
        k = ord(k) - 0x27
        table[k] = v


def patch_left_quote():
    # If we use the left quote (") for another localized glyph
    # we have to patch out few hardcoded uses of it from bodyprog
    mainmenu_left_quote = 0x800254F4# - _offset
    w_u8(BodyProg, ord(']'), 0x800254F4)
    #BodyProg.memory[mainmenu_left_quote] = ord(']')



def patch_inventory():
    item_names_ptr = 0x800ADB60
    item_descs_ptr = 0x800ADE6C

    with open("./dump/inventory.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    for k, v in data.items():
        itemn_ptr = item_names_ptr + 4*int(k)
        itemd_ptr = item_descs_ptr + 4*int(k)
        name = game_encode(v['name'])
        desc = game_encode(v['desc'])

        txt_pointer = get_new_blob_ptr(name, BodyProg)
        w_u32(BodyProg, txt_pointer, itemn_ptr)


        txt_pointer = get_new_blob_ptr(desc, BodyProg)
        w_u32(BodyProg, txt_pointer, itemd_ptr)




def dump_bodyprog(silent: memoryview):
    init_patcher(silent)
    extract_font_width(bodyprog)
    extract_inventory_messages(bodyprog)
    dump_small_strings(bodyprog)
    dump_misc_strings(bodyprog)
    dump_inventory_options(bodyprog)
    dump_main_menu()


def patch_bodyprog(silent: memoryview):
    init_patcher(silent)
    patch_inventory_options()
    patch_main_menu()
    patch_inventory()
    patch_font_width()
    patch_left_quote()
    patch_inventory_misc()
    patch_small_strings()
    patch_item_name_pos(16)
    #xorBodyProg(silent)

