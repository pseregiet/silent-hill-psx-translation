#!/usr/bin/env python3

import sys
import struct
import json
import re
import ctypes
from collections import namedtuple
from common import *
from ov_bodyprog import *

#based on https://github.com/Vatuu/silent-hill-decomp/blob/master/tools/silentassets/extract.py
def xorBodyProg(silent: memoryview):
    outArray = BodyProg.memory.cast("I") # uint32_t
    seed = 0

    for i, value in enumerate(outArray):
        seed = (seed + 0x01309125) & 0xffffffff
        seed = (seed * 0x03a452f7) & 0xffffffff
        outArray[i] ^= seed


bodyprog_info = {
    "game_result_table":        [ 0x8002B4C0, 34],
    "inventory_options_table0": [ 0x80026214, 8 ],
    "inventory_options_table1": [ 0x80027F94, 7 ],
    "inventory_options_table2": [ 0x80027E34, 8, 0x80027DD8 ],
    "main_menu_table":          [ 0x800A9A8C, 4, 0x800254EC ],
    "diff_menu_table":          [ 0x800A9AA0, 3, 0x8002551C ],
    "inventory_items":          [ 0x800ADB60, 0x800ADE6C ],
    "small_strings":            [
        # code addr   # string addr
        [ 0x8004F594, 0x800262AC ],
        [ 0x8004F5A0, 0x800262D0 ],
        [ 0x80051960, 0x80027F14 ],
        [ 0x8005196C, 0x80027F28 ],
    ],
}


def dump_font_width():
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
    return data


def dump_inventory_items():
    nameptr = bodyprog_info["inventory_items"][0]
    descptr = bodyprog_info["inventory_items"][1]
    data = {}
    for i in range(195):
        nptr = r_u32(BodyProg, nameptr + (i*4))
        dptr = r_u32(BodyProg, descptr + (i*4))
        if nptr == 0 or dptr == 0:
            continue
        data[i] = {
            "name": nice_encode(read_c_string2(BodyProg, nptr)),
            "desc": nice_encode(read_c_string2(BodyProg, dptr))
        }
    return data


def dump_bodyprog(silent: memoryview, outdir: str):
    data = {}
    def dump_table(name):
        data[name] = load_text_table(BodyProg, bodyprog_info[name][0], bodyprog_info[name][1])
    def dump_str(name):
        data[name] = nice_encode(read_c_string2(BodyProg, saveload_info[name]))

    extract_overlay2(silent, BodyProg)
    xorBodyProg(silent)

    data["patch_left_quote"] = False
    data["patch_inventory_item_name"] = False

    data["font_width"] = dump_font_width()
    data["inventory_items"] = dump_inventory_items()
    dump_table("inventory_options_table0")
    dump_table("inventory_options_table1")
    dump_table("inventory_options_table2")
    dump_table("main_menu_table")
    dump_table("diff_menu_table")
    dump_table("game_result_table")

    data["small_strings"] = {}
    for i in range(4):
        data["small_strings"][i] = nice_encode(read_c_string2(BodyProg, bodyprog_info["small_strings"][i][1]))
    
    with open(f"{outdir}/bodyprog.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)



# If we use the left quote (") for another localized glyph
# we have to patch out the hardcoded use of it from bodyprog
def patch_left_quote():
    mainmenu_left_quote = 0x800254F4
    w_u8(BodyProg, ord(']'), 0x800254F4)


# We can leave the 'Name:' string blank and move the item name
# string into its place, giving us more screen real estate.
def patch_item_name_pos():
    code_ptr = [0x80051E64, 0x80051E78, 0x80051ED8]
    for ptr in code_ptr:
        w_u16(BodyProg, 16, ptr)


def patch_small_strings(data):
    print(data)
    for i in range(4):
        news = game_encode(data[str(i)])
        ptr = get_new_blob_ptr(news, BodyProg)
        hi = (ptr >> 16) & 0xFFFF
        lo = (ptr >> 0 ) & 0xFFFF
        sstab = bodyprog_info["small_strings"][i][0]
        w_u16(BodyProg, hi, sstab + 0)
        w_u16(BodyProg, lo, sstab + 4)


def patch_font_width(data):
    font_widths_offset = 0x80025D6C - BodyProg.offset
    table = BodyProg.memory[font_widths_offset: font_widths_offset + 84].cast('B')

    for k, v in data.items():
        if k == '!':
            k = '\\'
        elif k == '&':
            k = '^'
        k = ord(k) - 0x27
        table[k] = v


def patch_main_menu(data):
    def work(name):
        txttab = bodyprog_info[name][0]
        postab = bodyprog_info[name][2]
        for k, v in data[name].items():
            news = game_encode(v)
            newx = (text_width(news) // 2)
            txt_ptr = get_new_blob_ptr(news, BodyProg)
            w_u32(BodyProg, txt_ptr, txttab + int(k)*4)
            w_u8(BodyProg, newx, postab + int(k))

    work("main_menu_table")
    work("diff_menu_table")


def patch_inventory_options(data):
    txttab = bodyprog_info["inventory_options_table2"][0]
    postab = bodyprog_info["inventory_options_table2"][2]
    posx   = [162, 161, 65, 256, 256, 65, 29, 39]
    for i in range(8):
        news = game_encode(data[str(i)])
        txt_ptr = get_new_blob_ptr(news, BodyProg)
        w_u32(BodyProg, txt_ptr, txttab + (i*4))

        txtpos = posx[i] - (text_width(news) // 2)
        w_s16(BodyProg, txtpos, postab + (i*4))


def patch_items(data):
    nameptr = bodyprog_info["inventory_items"][0]
    descptr = bodyprog_info["inventory_items"][1]
    for k, v in data.items():
        k = int(k)
        news = game_encode(v["name"])
        ptr = get_new_blob_ptr(news, BodyProg)
        w_u32(BodyProg, ptr, nameptr + (k*4))

        news = game_encode(v["desc"])
        ptr = get_new_blob_ptr(news, BodyProg)
        w_u32(BodyProg, ptr, descptr + (k*4))


def patch_bodyprog(silent: memoryview, indir: str):
    def patch_table(name):
        patch_text_table(BodyProg, bodyprog_info[name][0], data[name])

    with open(f"{indir}/bodyprog.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    extract_overlay2(silent, BodyProg)
    xorBodyProg(silent)

    patch_main_menu(data)
    patch_table("game_result_table")
    patch_table("inventory_options_table0")
    patch_table("inventory_options_table1")
    patch_inventory_options(data["inventory_options_table2"])
    patch_items(data["inventory_items"])
    patch_small_strings(data["small_strings"])
    patch_font_width(data["font_width"])
    if data["patch_left_quote"] == True:
        patch_left_quote()
    if data["patch_inventory_item_name"] == True:
        patch_item_name_pos()

