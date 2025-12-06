#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple
from common import *

FileInfos = [
    FileInfo(0x092af,  422,  "map0_s00", 0x800C9578, None, None),
    FileInfo(0x092e4,  401,  "map0_s01", 0x800C9578, None, None),
    FileInfo(0x09317,  160,  "map0_s02", 0x800C9578, None, None),
    FileInfo(0x0932b,  381,  "map1_s00", 0x800C9578, None, None),
    FileInfo(0x0935b,  349,  "map1_s01", 0x800C9578, None, None),
    FileInfo(0x09387,  454,  "map1_s02", 0x800C9578, None, None),
    FileInfo(0x093c0,  463,  "map1_s03", 0x800C9578, None, None),
    # map1_s04 is unused
    FileInfo(0x09404,  242,  "map1_s05", 0x800C9578, None, None),
    FileInfo(0x09423,  284,  "map1_s06", 0x800C9578, None, None),
    FileInfo(0x09447,  708,  "map2_s00", 0x800C9578, None, None),
    FileInfo(0x094a0,  131,  "map2_s01", 0x800C9578, None, None),
    FileInfo(0x094b1,  631,  "map2_s02", 0x800C9578, None, None),
    # map2_s03 is unused
    FileInfo(0x0950a,   95,  "map2_s04", 0x800C9578, None, None),
    FileInfo(0x09516,  201,  "map3_s00", 0x800C9578, None, None),
    FileInfo(0x09530,  243,  "map3_s01", 0x800C9578, None, None),
    FileInfo(0x0954f,  156,  "map3_s02", 0x800C9578, None, None),
    FileInfo(0x09563,  240,  "map3_s03", 0x800C9578, None, None),
    FileInfo(0x09581,  217,  "map3_s04", 0x800C9578, None, None),
    FileInfo(0x0959d,  320,  "map3_s05", 0x800C9578, None, None),
    FileInfo(0x095c5,  203,  "map3_s06", 0x800C9578, None, None),
    # map4_s00 is unused
    FileInfo(0x095e7,  236,  "map4_s01", 0x800C9578, None, None),
    FileInfo(0x09605,  639,  "map4_s02", 0x800C9578, None, None),
    FileInfo(0x09655,  373,  "map4_s03", 0x800C9578, None, None),
    FileInfo(0x09684,  218,  "map4_s04", 0x800C9578, None, None),
    FileInfo(0x096a0,  293,  "map4_s05", 0x800C9578, None, None),
    # map4_s06 is unused
    FileInfo(0x096cd,  335,  "map5_s00", 0x800C9578, None, None),
    FileInfo(0x096f7,  682,  "map5_s01", 0x800C9578, None, None),
    FileInfo(0x0974d,  277,  "map5_s02", 0x800C9578, None, None),
    FileInfo(0x09770,  220,  "map5_s03", 0x800C9578, None, None),
    FileInfo(0x0978c,  684,  "map6_s00", 0x800C9578, None, None),
    FileInfo(0x097e2,  193,  "map6_s01", 0x800C9578, None, None),
    FileInfo(0x097fb,  185,  "map6_s02", 0x800C9578, None, None),
    FileInfo(0x09813,  363,  "map6_s03", 0x800C9578, None, None),
    FileInfo(0x09841,  586,  "map6_s04", 0x800C9578, None, None),
    # map6_s05 is unued
    FileInfo(0x09894,  175,  "map7_s00", 0x800C9578, None, None),
    FileInfo(0x098aa,  415,  "map7_s01", 0x800C9578, None, None),
    FileInfo(0x098de,  559,  "map7_s02", 0x800C9578, None, None),
    FileInfo(0x09924,  698,  "map7_s03", 0x800C9578, None, None),
]

# US version doesn't set the flag when you read the newspaper which leads to some missing content.
# The missing flag was figured out by emoose.
def patch_missing_newspaper_memo():
    for ovi in FileInfos:
        if "map5_s03" == ovi.filename:
            w_u32(ovi, 0x018900CB, 0x800D39FC)
            w_u32(ovi, 0x0000212A, 0x800D3A04)
            return

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


def patch_text_tab(ovi: FileInfo, tableptr, text):
    def iter_values(x):
        if isinstance(x, dict):
            return x.values()
        return x

    for i, val in enumerate(iter_values(text)):
        news = game_encode(val)
        txt_ptr = get_new_blob_ptr(news, ovi)
        w_u32(ovi, txt_ptr, tableptr + (i*4))


def dump_map_messages(ovi: FileInfo, outdir: str):
    ptroffset = r_u32(ovi, 0x800C95AC)
    endoffset = r_u32(ovi, 0x800C95A0)

    i = 0
    msgs = []
    msgptr = ptroffset

    while True:
        if msgptr == endoffset:
            break

        msg1 = r_u32(ovi, msgptr)
        if msg1 == 0:
            break

        msg1_str = read_c_string2(ovi, msg1)
        msgs.append(nice_encode(msg1_str))
        msgptr += 4
        i += 1

    txt_last_byte = r_u32(ovi, ptroffset)
    txt_last_byte += len(read_c_string2(ovi, txt_last_byte))
    txtoffset = r_u32(ovi, ptroffset + ((i-1)*4))
    txtlen = txt_last_byte - txtoffset

    output = {
            "txt-offset": f"0x{txtoffset:X}",
            "ptr-offset": f"0x{ptroffset:X}",
            "txt-size"  : f"0x{txtlen:X}",
            "ptr-size"  : f"0x{i:X}", 
    }

    output["messages"] = msgs
    with open(f"{outdir}/{ovi.filename}.json", 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=4, ensure_ascii=False)


def dump_maps(silent: memoryview, outdir: str):
    for ovi in FileInfos:
        extract_overlay2(silent, ovi)
        dump_map_messages(ovi, outdir)


def patch_map(ovi: FileInfo, indir: str):
    with open(f"{indir}/{ovi.filename}.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    txt_offset = int(data['txt-offset'], 16)
    max_txt_size = int(data['txt-size'], 16)
    ovi.data_banks = [[txt_offset, max_txt_size]]

    ptr_offset = int(data['ptr-offset'], 16)
    for line in data["messages"]:
        width = text_w(line)
        if width > 320:
            raise RuntimeError(f"line '{line}' is too long ({width} pixels)")
    patch_text_tab(ovi, ptr_offset, data["messages"])


def patch_maps(silent: memoryview, indir: str):
    for ovi in FileInfos:
        extract_overlay2(silent, ovi)
        patch_map(ovi, indir)
    patch_missing_newspaper_memo()
