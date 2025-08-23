#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple
from common import *

_offset = 0x800C9578
OverlayInfos = [
    OverlayInfo(0x092af,  422,  "map0_s00"),
    OverlayInfo(0x092e4,  401,  "map0_s01"),
    OverlayInfo(0x09317,  160,  "map0_s02"),
    OverlayInfo(0x0932b,  381,  "map1_s00"),
    OverlayInfo(0x0935b,  349,  "map1_s01"),
    OverlayInfo(0x09387,  454,  "map1_s02"),
    OverlayInfo(0x093c0,  463,  "map1_s03"),
    #OverlayInfo(0x093fa,   75,  "map1_s04"),
    OverlayInfo(0x09404,  242,  "map1_s05"),
    OverlayInfo(0x09423,  284,  "map1_s06"),
    OverlayInfo(0x09447,  708,  "map2_s00"),
    OverlayInfo(0x094a0,  131,  "map2_s01"),
    OverlayInfo(0x094b1,  631,  "map2_s02"),
    #OverlayInfo(0x09500,   74,  "map2_s03"),
    OverlayInfo(0x0950a,   95,  "map2_s04"),
    OverlayInfo(0x09516,  201,  "map3_s00"),
    OverlayInfo(0x09530,  243,  "map3_s01"),
    OverlayInfo(0x0954f,  156,  "map3_s02"),
    OverlayInfo(0x09563,  240,  "map3_s03"),
    OverlayInfo(0x09581,  217,  "map3_s04"),
    OverlayInfo(0x0959d,  320,  "map3_s05"),
    OverlayInfo(0x095c5,  203,  "map3_s06"),
    #OverlayInfo(0x095df,   64,  "map4_s00"),
    OverlayInfo(0x095e7,  236,  "map4_s01"),
    OverlayInfo(0x09605,  639,  "map4_s02"),
    OverlayInfo(0x09655,  373,  "map4_s03"),
    OverlayInfo(0x09684,  218,  "map4_s04"),
    OverlayInfo(0x096a0,  293,  "map4_s05"),
    #OverlayInfo(0x096c5,   64,  "map4_s06"),
    OverlayInfo(0x096cd,  335,  "map5_s00"),
    OverlayInfo(0x096f7,  682,  "map5_s01"),
    OverlayInfo(0x0974d,  277,  "map5_s02"),
    OverlayInfo(0x09770,  220,  "map5_s03"),
    OverlayInfo(0x0978c,  684,  "map6_s00"),
    OverlayInfo(0x097e2,  193,  "map6_s01"),
    OverlayInfo(0x097fb,  185,  "map6_s02"),
    OverlayInfo(0x09813,  363,  "map6_s03"),
    OverlayInfo(0x09841,  586,  "map6_s04"),
    #OverlayInfo(0x0988b,   65,  "map6_s05"),
    OverlayInfo(0x09894,  175,  "map7_s00"),
    OverlayInfo(0x098aa,  415,  "map7_s01"),
    OverlayInfo(0x098de,  559,  "map7_s02"),
    OverlayInfo(0x09924,  698,  "map7_s03"),
]

def nice_encode(line):
    pattern = re.compile(r'(~[CLS]\d|~[MDHETN])')
    jpattern= re.compile(r'(~J\d\(\d+\.\d+\))')
    line = line.replace(' ', '').replace('\n', '').replace('\t', '')
    line = line.replace('_', ' ')
    line = pattern.sub(r'{\1}', line)
    return jpattern.sub(r'{\1}', line).strip()

def game_encode(line):
    line = line.replace(' ', '_').replace('{', ' ').replace('}', ' ')
    line = encode_local_text(line)
    return line.encode('ascii') + b'\x00'

def dump_map_messages(silent: memoryview, ovi: OverlayInfo):
    mapdata = extract_overlay(silent, ovi)

    ptroffset = read_uint32_le(mapdata, 0x34) - _offset
    endoffset = read_uint32_le(mapdata, 0x28) - _offset

    i = 0
    msgs = []
    msgptr = ptroffset

    while True:
        if msgptr == endoffset:
            break

        msg1 = read_uint32_le(mapdata, msgptr)
        if msg1 == 0:
            break

        msg1 -= _offset
        msg1_str = read_c_string(mapdata, msg1)
        msgs.append(nice_encode(msg1_str))
        msgptr += 4
        i += 1

    txt_last_byte = read_uint32_le(mapdata, ptroffset) - _offset
    txt_last_byte += len(read_c_string(mapdata, txt_last_byte))
    txtoffset = read_uint32_le(mapdata, ptroffset + ((i-1)*4)) - _offset
    txtlen = txt_last_byte - txtoffset

    output = {
            "txt-offset": f"0x{txtoffset:X}",
            "ptr-offset": f"0x{ptroffset:X}",
            "txt-size"  : f"0x{txtlen:X}",
            "ptr-size"  : f"0x{i:X}", 
    }

    output["messages"] = msgs
    with open("./dump/" + ovi.filename + ".json", 'w') as f:
        json.dump(output, f, indent=4)

def dump_maps(silent: memoryview):
    for ovi in OverlayInfos:
        dump_map_messages(silent, ovi)

def patch_map(silent: memoryview, ovi: OverlayInfo):
    with open("./dump/" + ovi.filename + ".json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    mapdata = extract_overlay(silent, ovi)
    txt_offset = int(data['txt-offset'], 16)
    ptr_offset = int(data['ptr-offset'], 16)
    max_txt_size = int(data['txt-size'], 16)
    max_txt_size += txt_offset
    for line in data['messages']:
        txt_pointer = _offset + txt_offset
        game_line = game_encode(line)
        width = accumulate_widths(game_line)
        if width > 320:
            raise RuntimeError(f"line '{line}' is too long ({width} pixels)")

        patch_pointer(mapdata, txt_pointer, ptr_offset)
        patch_blob(mapdata, game_line, txt_offset)
        txt_offset += len(game_line)
        ptr_offset += 4
        if txt_offset > max_txt_size:
            raise MemoryError("Not enough room for the new text")

def patch_maps(silent: memoryview):
    for ovi in OverlayInfos:
        patch_map(silent, ovi)
