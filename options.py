#!/usr/bin/env python3

import sys
import struct
import json
import re
import ctypes
from collections import namedtuple
from common import *

data_banks = [
    [ 0x801E2C64, 0x10 ],
    [ 0x801E2BC8, 0x14 ],
    [ 0x801E2784, 0x88 ],
    [ 0x801E26CC, 0x98 ],
    [ 0x801E2CC0, 0x80 ],
    [ 0x801E2A04, 0x68 ],
    [ 0x801E2D0C, 0x64 ],
]

Options = FileInfo(0x0997c, 78,   "option", 0x801E2600, data_banks, None)

options_info = {
    "brightness_level": 0x801E2C64,
    "options_str": 0x801E2784,
    "extra_options_str": 0x801E26CC,
    "options_table": [ 0x801E280C, 9 ],
    "options_opts_table": [ 0x801E2BDC, 4 ],
    "options_highlight_width": 0x801E2858,
    "extra_options_table": [ 0x801E2764, 8 ],
    "extra_options_opts_table": [ 0x801E2A6C, 19 ],
    "controller_types_table":[ 0x801E736C, 4 ],
    "controller_actions_table": [ 0x801E737C, 14 ],
    "extra_options_highlight_width": 0x801E2830,
}


def dump_options(silent: memoryview, outdir: str):
    data = {}
    def dump_table(name):
        data[name] = load_text_table(Options, options_info[name][0], options_info[name][1])
    def dump_str(name):
        data[name] = nice_encode(read_c_string2(Options, options_info[name]))

    extract_overlay2(silent, Options)

    dump_str("brightness_level")
    dump_str("options_str")
    dump_str("extra_options_str")
    dump_table("options_table")
    dump_table("extra_options_table")
    dump_table("controller_types_table")
    dump_table("controller_actions_table")
    dump_table("extra_options_opts_table")
    dump_table("options_opts_table")
    with open(f"{outdir}/options.json", 'w', encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def patch_opts_triangles(ptrTop, ptrBot, t, xcenter, width):
    # option arrows/triangles. We only specify x offset
    # from the tip of the arrow
    # bottom triangle is 10 pixels high and wide, top is 8
    tris = {
        "lb": [0, 10, 10  ], # left bottom
        "lt": [1, 9,  9   ], # left top
        "rb": [0, -10, -10], # right bottom
        "rt": [-1, -9, -9 ], # right top
    }

    # calculate new vertices based on the xcenter position
    # and move to the left and right to get the desired width
    lax = xcenter - (width // 2)
    rax = xcenter + (width // 2)
    stride = 2 * 2 * 3 # 2x u16 * 3 vertices
    t = t * 2
    for v in range(3):
        w_s16(Options, tris["lb"][v] + lax, ptrBot + (t * stride) + (v*4))
        w_s16(Options, tris["lt"][v] + lax, ptrTop + (t * stride) + (v*4))
    t += 1
    for v in range(3):
        w_s16(Options, tris["rb"][v] + rax, ptrBot + (t * stride) + (v*4))
        w_s16(Options, tris["rt"][v] + rax, ptrTop + (t * stride) + (v*4))


def patch_main_opts(data):
    basex = 248
    trigCenter = basex - 160
    def patch_pos(idx, ptr):
        x = text_w(data[str(idx)]) // 2
        w_s16(Options, basex - x, ptr)
    def patch_trigs(idx, stridx):
        w = 0
        for si in stridx:
            w = max(w, text_w(data[str(si)]))
        patch_opts_triangles(0x801E2AD8, 0x801E2B50, idx, trigCenter, w + 24)

    patch_pos(0, 0x801E52F8)
    patch_pos(0, 0x801E5320)
    patch_pos(1, 0x801E52FC)
    patch_pos(1, 0x801E5324)
    patch_pos(2, 0x801E5348)
    patch_pos(3, 0x801E534C)
    patch_trigs(0, [0, 1])
    patch_trigs(1, [0, 1])
    patch_trigs(2, [2, 3])

    # Volume bars X offset
    w_s16(Options, 40, 0x801E3FE8)
    w_s16(Options, 40, 0x801E40A4)
    trigWidth3 = (16 * 6) + 24
    for t in range(2):
        patch_opts_triangles(0x801E2AD8, 0x801E2B50, 3+t, trigCenter, trigWidth3)

def patch_extra_opts(data):
    basex = 248
    trigCenter = basex - 160
    def patch_pos(idx, ptr):
        x = text_w(data[str(idx)]) // 2
        w_s16(Options, basex - x, ptr)
    def patch_trigs(idx, stridx):
        w = 0
        for si in stridx:
            w = max(w, text_w(data[str(si)]))
        patch_opts_triangles(0x801E2884, 0x801E2944, idx, trigCenter, w + 24)

    patch_pos(0,  0x801E4E08)
    patch_pos(1,  0x801E4E04)
    patch_pos(2,  0x801E4E44)
    patch_pos(3,  0x801E4E30)
    patch_pos(4,  0x801E4E58)
    patch_pos(5,  0x801E4E64)
    patch_pos(7,  0x801E4E98)
    patch_pos(7,  0x801E4ED0)
    patch_pos(7,  0x801E4F08)
    patch_pos(8,  0x801E4E94)
    patch_pos(8,  0x801E4ECC)
    patch_pos(8,  0x801E4F04)
    patch_pos(9,  0x801E4F40)
    patch_pos(10, 0x801E4F3C)
    patch_pos(11, 0x801E4F78)
    patch_pos(12, 0x801E4F74)
    patch_pos(13, 0x801E4FA0)
    patch_trigs(0, [0, 1])
    patch_trigs(1, [2, 3, 4, 5])
    patch_trigs(2, [7, 8])
    patch_trigs(3, [7, 8])
    patch_trigs(4, [7, 8])
    patch_trigs(5, [9, 10])
    patch_trigs(6, [11, 12])
    patch_trigs(7, [13, 14, 15, 16, 17, 18])

def patch_options(silent: memoryview, indir: str):
    def patch_table(name):
        patch_text_table(Options, options_info[name][0], data[name])

    with open(f"{indir}/options.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    extract_overlay2(silent, Options)

    patch_table("options_table")
    patch_table("extra_options_table")
    patch_table("controller_types_table")
    patch_table("controller_actions_table")
    patch_table("extra_options_opts_table")
    patch_table("options_opts_table")

    # Move the controller icons
    control_icons_x = 64
    w_u16(Options, control_icons_x, 0x801E70B0)

    # Brightness level string pointer
    news = game_encode(data["brightness_level"])
    txt_ptr = get_new_blob_ptr(news, Options)

    code1 = (txt_ptr >> 16) & 0xFFFF
    code2 = (txt_ptr >> 0 ) & 0xFFFF
    w_u16(Options, code1, 0x801E6244)
    w_u16(Options, code2, 0x801E6250)

    # OPTIONS string pointer
    news = game_encode(data["options_str"])
    txt_ptr = get_new_blob_ptr(news, Options)

    code1 = (txt_ptr >> 16) & 0xFFFF
    code2 = (txt_ptr >> 0 ) & 0xFFFF
    w_u16(Options, code1, 0x801E4304)
    w_u16(Options, code2, 0x801E4308)
    news = game_encode(data["extra_options_str"])
    txt_ptr = get_new_blob_ptr(news, Options)

    code1 = (txt_ptr >> 16) & 0xFFFF
    code2 = (txt_ptr >> 0 ) & 0xFFFF
    w_u16(Options, code1, 0x801E4198)
    w_u16(Options, code2, 0x801E41F0)

    # Options menu move bullets:
    bulletsx = (-160+16)

    w_s16(Options, bulletsx+0 , 0x801E2874+0x00)
    w_s16(Options, bulletsx+0 , 0x801E2874+0x04)
    w_s16(Options, bulletsx+14, 0x801E2874+0x08)
    w_s16(Options, bulletsx+14, 0x801E2874+0x0C)

    w_s16(Options, bulletsx+1 , 0x801E2864+0x00)
    w_s16(Options, bulletsx+1 , 0x801E2864+0x04)
    w_s16(Options, bulletsx+12, 0x801E2864+0x08)
    w_s16(Options, bulletsx+12, 0x801E2864+0x0C)

    w_s16(Options, bulletsx, 0x801E482C)
    w_s16(Options, bulletsx, 0x801E48E8)

    for k, v in data["options_table"].items():
        val = text_width(game_encode(v)) + 25
        w_u8(Options, val, 0x801E2858 + int(k))

    # Extra menu move bullets:
    w_s16(Options, bulletsx+0 , 0x801E2848+0x00)
    w_s16(Options, bulletsx+0 , 0x801E2848+0x04)
    w_s16(Options, bulletsx+14, 0x801E2848+0x08)
    w_s16(Options, bulletsx+14, 0x801E2848+0x0C)

    w_s16(Options, bulletsx+1 , 0x801E2838+0x00)
    w_s16(Options, bulletsx+1 , 0x801E2838+0x04)
    w_s16(Options, bulletsx+12, 0x801E2838+0x08)
    w_s16(Options, bulletsx+12, 0x801E2838+0x0C)


    w_s16(Options, bulletsx, 0x801E4548)
    w_s16(Options, bulletsx, 0x801E45F8)
    for k, v in data["extra_options_table"].items():
        val = text_width(game_encode(v))
        w_u8(Options, val, 0x801E2830 + int(k))


    w_s16(Options, 40, 0x801E4294)
    w_s16(Options, 40, 0x801E42CC)
    w_s16(Options, 40, 0x801E43F4)
    w_s16(Options, 40, 0x801E4428)


    patch_main_opts(data["options_opts_table"])
    patch_extra_opts(data["extra_options_opts_table"])
