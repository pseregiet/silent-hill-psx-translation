#!/usr/bin/env python3

import sys
import struct
import json
import re
import ctypes
from collections import namedtuple
from common import *

data_banks = [
    [ 0x801E2604, 0x104 ],
    [ 0x801E2744, 0xEC  ],
    [ 0x801E287C, 0x100 ],
]
SaveLoad = FileInfo(0x09986, 81,   "saveload", 0x801E2600, data_banks, None)


saveload_info = {
    "memcard0_table":  [ 0x801E2830, 11 ],
    "memcard1_table":  [ 0x801E297C, 12 ],
    "locations_table": [ 0x801E74A8, 25 ],
    "misc_table":      [ 0x801E2D70, 6  ],
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
    with open(f"{outdir}/saveload.json", 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def patch_saveload(silent: memoryview, indir: str):
    def patch_table(name):
        patch_text_table(SaveLoad, saveload_info[name][0], data[name])

    with open(f"{indir}/saveload.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    extract_overlay2(silent, SaveLoad)

    patch_table("memcard0_table")
    patch_table("memcard1_table")
    patch_table("locations_table")
    patch_table("misc_table")

    for k,v in data["locations_table"].items():
        w_u8(SaveLoad, text_width(game_encode(v)), 0x801E2728 + int(k))

