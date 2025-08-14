#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple

OverlayInfo = namedtuple("OverlayInfo", ["sector_start", "block_size", "filename"])
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

BodyProg = OverlayInfo(0x000cf, 2635, "bodyprog")

def extract_overlay(silent: memoryview, ovi: OverlayInfo):
    start = (ovi.sector_start - 0x40) * 0x800
    size  = ovi.block_size * 0x100

    return silent[start: start+size]

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

def read_uint32_le(buf, offset):
    return struct.unpack_from('<I', buf, offset)[0]

def read_c_string(data: memoryview, offset: int) -> str:
    end = offset
    while end < len(data) and data[end] != 0:
        end += 1
    return data[offset:end].tobytes().decode('ascii')

def patch_blob(dstblob, srcblob, offset):
    bloblen = len(srcblob)
    dstblob[offset: offset + bloblen] = srcblob

def patch_pointer(dstblob, pointer, offset):
    srcblob = struct.pack('<I', pointer)
    patch_blob(dstblob, srcblob, offset)

def encode_local_text(line):
    line = line.replace('ł', ';').replace('ó', '*').replace('ę', '>').replace('ą', '^')
    line = line.replace('ż', '=').replace('ć', '<').replace('ń', '+').replace('ś', '/').replace('ź', 'Q')
    return line


