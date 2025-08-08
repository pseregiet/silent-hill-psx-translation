#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple

def read_uint32_le(buf, offset):
    return struct.unpack_from('<I', buf, offset)[0]

def read_c_string(data, offset):
    end = data.find(b'\x00', offset)
    return data[offset:end].decode('ascii')

def read_translated_lines(infile):
    with open(infile, "r", encoding="utf-8") as f:
        content = f.read()

    return [entry.strip() for entry in content.split('\n-------') ]

def find_blob_in_bin(blob, data, name):
    r = data.find(blob)
    if r == -1:
        raise Exception(f"can't find a blob {name}")

    return r

def nice_encoding(line):
    pattern = re.compile(r'(~[CLS]\d|~[MDHET])')
    jpattern= re.compile(r'(~J\d\(\d\.\d\))')
    line = line.replace(' ', '').replace('_', ' ').replace('\n', '').replace('\t', '').replace('~N', '\n')
    line = pattern.sub(r' \1 ', line)
    return jpattern.sub(r' \1 ', line).strip()

def revert(filename):
    translated_lines = read_translated_lines(filename + ".tr.txt")
    with open("translate."+filename, 'w') as f:
        for l in reversed(translated_lines):
            f.write(l + "\n------\n")



MapInfo = namedtuple("MapInfo", ["sector_start", "block_size", "filename"])
MapInfos = [
    MapInfo(0x092af,  422,  "map0_s00.bin"),
    #MapInfo(0x092e5,  401,  "map0_s01.bin"),
    #MapInfo(0x09317,  160,  "map0_s02.bin"),
    #MapInfo(0x0932b,  381,  "map1_s00.bin"),
    #MapInfo(0x0935b,  349,  "map1_s01.bin"),
    #MapInfo(0x09387,  454,  "map1_s02.bin"),
    #MapInfo(0x093c0,  463,  "map1_s03.bin"),
    #MapInfo(0x093fa,   75,  "map1_s04.bin"),
    #MapInfo(0x09404,  242,  "map1_s05.bin"),
    #MapInfo(0x09423,  284,  "map1_s06.bin"),
    #MapInfo(0x09447,  708,  "map2_s00.bin"),
    #MapInfo(0x094a0,  131,  "map2_s01.bin"),
    #MapInfo(0x094b1,  631,  "map2_s02.bin"),
    #MapInfo(0x09500,   74,  "map2_s03.bin"),
    #MapInfo(0x0950a,   95,  "map2_s04.bin"),
    #MapInfo(0x09516,  201,  "map3_s00.bin"),
    #MapInfo(0x09530,  243,  "map3_s01.bin"),
    #MapInfo(0x0954f,  156,  "map3_s02.bin"),
    MapInfo(0x09563,  240,  "map3_s03.bin"),
    #MapInfo(0x09581,  217,  "map3_s04.bin"),
    #MapInfo(0x0959d,  320,  "map3_s05.bin"),
    #MapInfo(0x095c5,  203,  "map3_s06.bin"),
    #MapInfo(0x095df,   64,  "map4_s00.bin"),
    #MapInfo(0x095e7,  236,  "map4_s01.bin"),
    #MapInfo(0x09605,  639,  "map4_s02.bin"),
    #MapInfo(0x09655,  373,  "map4_s03.bin"),
    #MapInfo(0x09684,  218,  "map4_s04.bin"),
    #MapInfo(0x096a0,  293,  "map4_s05.bin"),
    #MapInfo(0x096c5,   64,  "map4_s06.bin"),
    #MapInfo(0x096cd,  335,  "map5_s00.bin"),
    #MapInfo(0x096f7,  682,  "map5_s01.bin"),
    #MapInfo(0x0974d,  277,  "map5_s02.bin"),
    #MapInfo(0x09770,  220,  "map5_s03.bin"),
    #MapInfo(0x0978c,  684,  "map6_s00.bin"),
    #MapInfo(0x097e2,  193,  "map6_s01.bin"),
    #MapInfo(0x097fb,  185,  "map6_s02.bin"),
    #MapInfo(0x09813,  363,  "map6_s03.bin"),
    #MapInfo(0x09841,  586,  "map6_s04.bin"),
    #MapInfo(0x0988b,   65,  "map6_s05.bin"),
    #MapInfo(0x09894,  175,  "map7_s00.bin"),
    #MapInfo(0x098aa,  415,  "map7_s01.bin"),
    #MapInfo(0x098de,  559,  "map7_s02.bin"),
    #MapInfo(0x09924,  698,  "map7_s03.bin"),
]



overlays = [ "map0_s00.asciz", "map0_s01.asciz", "map0_s02.asciz", "map1_s00.asciz",
             "map1_s01.asciz", "map1_s02.asciz", "map1_s03.asciz", "map1_s04.asciz",
             "map1_s05.asciz", "map1_s06.asciz", "map2_s00.asciz", "map2_s01.asciz",
             "map2_s02.asciz", "map2_s03.asciz", "map2_s04.asciz", "map3_s00.asciz",
             "map3_s01.asciz", "map3_s02.asciz", "map3_s03.asciz", "map3_s04.asciz",
             "map3_s05.asciz", "map3_s06.asciz", "map4_s00.asciz", "map4_s01.asciz",
             "map4_s02.asciz", "map4_s04.asciz", "map4_s05.asciz", "map4_s06.asciz",
             "map5_s00.asciz", "map5_s01.asciz", "map5_s02.asciz", "map5_s03.asciz",
             "map6_s00.asciz", "map6_s01.asciz", "map6_s02.asciz", "map6_s03.asciz",
             "map6_s04.asciz", "map6_s05.asciz", "map7_s00.asciz", "map7_s01.asciz",
             "map7_s02.asciz", "map7_s03.asciz" ]

#for ov in overlays:
#    revert(ov)

def extract_map_bin(silent, mi):
    start = (mi.sector_start - 0x40) * 0x800
    size  = mi.block_size * 0x100

    return silent[start: start+size]

def extract_map_messages(silent, mi):
    offset = 0x800C9578
    mapdata = extract_map_bin(silent, mi)

    ptroffset = read_uint32_le(mapdata, 0x34) - offset
    endoffset = read_uint32_le(mapdata, 0x28) - offset
    msgcount = int((endoffset - ptroffset) / 4)
    txt_last_byte = read_uint32_le(mapdata, ptroffset) - offset
    txt_last_byte += len(read_c_string(mapdata, txt_last_byte))
    txtoffset = read_uint32_le(mapdata, ptroffset + ((msgcount-1)*4)) - offset
    txtlen = txt_last_byte - txtoffset

    output = {
            "txt-offset": f"0x{txtoffset:X}",
            "ptr-offset": f"0x{ptroffset:X}",
            "txt-size"  : f"0x{txtlen:X}",
            "ptr-size"  : f"0x{msgcount:X}", 
    }

    i = 0
    msgs = []
    while True:
        if ptroffset + i*4 == endoffset:
            break

        msg1 = read_uint32_le(mapdata, ptroffset + i*4)
        msg1 -= offset
        print(f"{i}: {msg1:X}")

        i += 1
        msg1_str = read_c_string(mapdata, msg1)
        msgs.append(nice_encoding(msg1_str))
        #print(msg1_str)

    output["messages"] = msgs
    with open("messages/" + mi.filename + ".json", 'w') as f:
        json.dump(output, sys.stdout, indent=4)


def main():
    silent_path = sys.argv[1]
    silent = None
    with open(silent_path, 'rb') as f:
        silent = bytearray(f.read())

    for mi in MapInfos:
        extract_map_messages(silent, mi)


main()
