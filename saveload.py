#!/usr/bin/env python3

import sys
import struct
import json
import re
import ctypes
from collections import namedtuple
from common import *

data_banks = [
    [ 0x801E2710, 0x18  ],
    [ 0x801E2744, 0xEC  ],
    [ 0x801E287C, 0x100 ],
    [ 0x801E2604, 0x104 ],
]
SaveLoad = FileInfo(0x09986, 81,   "saveload", 0x801E2600, data_banks, None)


saveload_info = {
    "memcard0_table":  [ 0x801E2830, 11 ],
    "memcard1_table":  [ 0x801E297C, 12, 0x801E29AC ],
    "locations_table": [ 0x801E74A8, 25 ],
    "misc_table":      [ 0x801E2D70, 6  ],
    "small_strings":   [ 0x801E2710, 0x801E2718, 0x801E2720 ],
}


def dump_saveload(silent: memoryview, outdir: str):
    data = {}
    def dump_table(name):
        data[name] = load_text_table(SaveLoad, saveload_info[name][0], saveload_info[name][1])

    extract_overlay2(silent, SaveLoad)

    dump_table("memcard0_table")
    dump_table("memcard1_table")
    dump_table("locations_table")
    dump_table("misc_table")
    data["small_strings"] = {}
    for i in range(3):
        data["small_strings"][i] = nice_encode(read_c_string2(SaveLoad, saveload_info["small_strings"][i]))

    with open(f"{outdir}/saveload.json", 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def patch_memcard1_pos(data):
    postab = saveload_info["memcard1_table"][2]
    for k, v in data.items():
        k = int(k)
        pos = text_w(v)
        w_s16(SaveLoad, pos, postab + (k*2))


def patch_small_strings(data):
    news = game_encode(data["0"])
    nptr = get_new_blob_ptr(news, SaveLoad)
    hi, lo = split_mips_addr(nptr)
    w_u16(SaveLoad, hi, 0x801E2EFC)
    w_u16(SaveLoad, lo, 0x801E2F00)

    news = game_encode(data["1"])
    nptr = get_new_blob_ptr(news, SaveLoad)
    hi, lo = split_mips_addr(nptr)
    w_u16(SaveLoad, hi, 0x801E2F08)
    w_u16(SaveLoad, lo, 0x801E2F0C)

    news = game_encode(data["2"])
    nptr = get_new_blob_ptr(news, SaveLoad)
    hi, lo = split_mips_addr(nptr)
    w_u16(SaveLoad, hi, 0x801E2FE0)
    w_u16(SaveLoad, lo, 0x801E3004)


def patch_misc_table(data):
    tableptr = saveload_info["misc_table"][0]
    def work(text, orgptr):
        news = game_encode(text)
        nptr = get_new_blob_ptr(news, SaveLoad)
        hi, lo = split_mips_addr(nptr)
        w_u32(SaveLoad, nptr, tableptr + (i*4))
        # Also patch few pointers that read these strings directly
        w_u16(SaveLoad, hi, orgptr[0])
        w_u16(SaveLoad, lo, orgptr[1])
        print(f"{news}, {nptr:x}, {orgptr[0]:x}={((nptr>>16)&0xFFFF):x}, {orgptr[1]:x}={((nptr>>0 )&0xFFFF):x}")

    ptrlist = [
        [0x801E5FFC, 0x801E6000],
        [0x801E603C, 0x801E6040],
        [0x801E607C, 0x801E6080],
        [0x801E6150, 0x801E6158],
        [0x801E6168, 0x801E6170],
        [0x801E5EF8, 0x801E5EFC],
    ]
    for i in range(6):
        work(data[str(i)], ptrlist[i])

    posx = 160 - (text_w(data["5"]) // 2)
    w_u16(SaveLoad, posx, 0x801E5EEC)


def patch_saveload(silent: memoryview, indir: str):
    def patch_table(name):
        patch_text_table(SaveLoad, saveload_info[name][0], data[name])

    with open(f"{indir}/saveload.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    extract_overlay2(silent, SaveLoad)

    patch_small_strings(data["small_strings"])
    patch_table("memcard0_table")
    patch_table("memcard1_table")
    patch_table("locations_table")
    patch_misc_table(data["misc_table"])
    patch_memcard1_pos(data["memcard1_table"])

    for k,v in data["locations_table"].items():
        w_u8(SaveLoad, text_width(game_encode(v)), 0x801E2728 + int(k))

