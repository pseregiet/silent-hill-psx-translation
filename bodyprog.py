#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple
from common import *

_offset = 0x80024B60
BodyProg = OverlayInfo(0x000cf, 2635, "bodyprog")

def nice_encode(line):
    return line.replace('\t', '').replace('\n', '{~N}').replace('_', ' ')

def game_encode(line):
    line = line.replace(' ', '_').replace('{~N}', '\n')
    line = encode_local_text(line)
    return line.encode('ascii') + b'\x00'

def extract_inventory_messages(bodyprog: memoryview):
    item_names_ptr = 0x800ADB60 - _offset
    item_descs_ptr = 0x800ADE6C - _offset
    data = {}
    for i in range(200):
        try:
            in_ptr = read_uint32_le(bodyprog, item_names_ptr) - _offset
            id_ptr = read_uint32_le(bodyprog, item_descs_ptr) - _offset
            data[i] = {
                "name": nice_encoding_for_bodyprog(read_c_string(bodyprog, in_ptr)),
                "desc": nice_encoding_for_bodyprog(read_c_string(bodyprog, id_ptr))
            }
        except:
            pass
        item_names_ptr += 4
        item_descs_ptr += 4

    with open("messages/inventory.json", 'w') as f:
        json.dump(data, f, indent=4)

def extract_font_width(bodyprog: memoryview):
    font_widths_offset = 0x80025D6C - _offset
    table = bodyprog[font_widths_offset: font_widths_offset + 84].cast('B')
    data = {}
    for i in range(84):
        char = chr(i+0x27)
        if char == '\\':
            char = '!'
        elif char == '^':
            char = '&'
        data[char] = table[i]

    with open("messages/font_info.json", 'w') as f:
        json.dump(data, f, indent=4)


def patch_inventory(bodyprog: memoryview):
    text_offset = 0x1b1c
    text_max_size = 0x175c + text_offset
    item_names_ptr = 0x800ADB60 - _offset
    item_descs_ptr = 0x800ADE6C - _offset

    with open("messages/inventory.json", 'r', encoding="utf-8") as f:
        data = json.load(f)

    for k, v in data.items():
        itemn_ptr = item_names_ptr + 4*int(k)
        itemd_ptr = item_descs_ptr + 4*int(k)
        name = game_encode(v['name'])
        desc = game_encode(v['desc'])

        txt_pointer = _offset + text_offset
        patch_pointer(bodyprog, txt_pointer, itemn_ptr)
        patch_blob(bodyprog, name, text_offset)

        print(f"name={name}, desc={desc}, offset={text_offset:x}")

        text_offset += len(name)

        txt_pointer = _offset + text_offset
        patch_pointer(bodyprog, txt_pointer, itemd_ptr)
        patch_blob(bodyprog, desc, text_offset)

        text_offset += len(desc)

        if text_offset > text_max_size:
            raise MemoryError("Inventory text is too long")

    with open("BODYPROG.BIN", 'wb') as f:
        f.write(bodyprog)

def dump_bodyprog(silent: memoryview):
    bodyprog = xorBodyprog(silent)
    extract_font_width(bodyprog)
    extract_inventory_messages(bodyprog)

def patch_bodyprog(silent: memoryview):
    bodyprog = xorBodyprog(silent)
    patch_inventory(bodyprog)
    xorBodyprog(silent)

