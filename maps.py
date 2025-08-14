#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple
from common import *

_offset = 0x800C9578
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

def extract_map_messages(silent: memoryview, ovi: OverlayInfo):
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
    with open("messages/" + mi.filename + ".json", 'w') as f:
        #f = sys.stdout
        json.dump(output, f, indent=4)
    

def patch_map(silent: memoryview, ovi: OverlayInfo):
    with open("messages/" + ovi.filename + ".json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    mapdata = extract_overlay(silent, ovi)
    txt_offset = int(data['txt-offset'], 16)
    ptr_offset = int(data['ptr-offset'], 16)
    max_txt_size = int(data['txt-size'], 16)
    max_txt_size += txt_offset
    for line in data['messages']:
        txt_pointer = _offset + txt_offset
        line = game_encode(line)
        patch_pointer(mapdata, txt_pointer, ptr_offset)
        patch_blob(mapdata, line, txt_offset)
        txt_offset += len(line)
        ptr_offset += 4
        if txt_offset > max_txt_size:
            raise MemoryError("Not enough room for the new text")

