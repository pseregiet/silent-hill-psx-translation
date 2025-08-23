#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple

OverlayInfo = namedtuple("OverlayInfo", ["sector_start", "block_size", "filename"])
font_widths = {}

def extract_overlay(silent: memoryview, ovi: OverlayInfo):
    start = (ovi.sector_start - 0x40) * 0x800
    size  = ovi.block_size * 0x100

    return silent[start: start+size]

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
    line = line.replace('ą', '\'').replace('ż', '*').replace('ć', '+').replace('ę', '/')
    line = line.replace('ł', ';').replace('ń', '<').replace('ó', '>').replace('ś', '[').replace('ź', '&')
    return line

def read_font_widths():
    with open("dump/font_info.json", 'r') as f:
        data = json.load(f)

    for k, v in data.items():
        #if k == '!':
        #    k = '\\'
        #elif k == '&':
        #    k = '^'
        font_widths[k] = v


def accumulate_widths(line):
    i = 0
    total = 0
    last_line = 0
    text = line.decode("ascii")
    while i < len(text):
        ch = text[i]

        if ch == '\x00':
            break

        if ch == ' ' or ch == '\t':
            total += 6
            i += 1
            continue

        if ch == "~":
            if i + 1 < len(text):
                nxt = text[i + 1]
                # case 1: ~N, ~E, ~H, ~D, ~M → ignore both
                if nxt in "EHDM":
                    i += 2
                    continue
                if nxt in "N":
                    # new line, reset counter
                    i += 2
                    if total > last_line:
                        last_line = total
                    total = 0
                    continue

                # case 2: ~Sx, ~Lx, ~Cx (where x is a digit) → ignore all three
                if nxt in "SLC" and i + 2 < len(text) and text[i + 2].isdigit():
                    i += 3
                    continue

                # case 3: ~JNN.N\t
                if nxt == "J":
                    j = i + 2
                    # read number (could be like 12.3)
                    num = []
                    while j < len(text) and (text[j].isdigit() or text[j] == "."):
                        num.append(text[j])
                        j += 1
                    # expect a tab
                    if j < len(text) and text[j] == "\t":
                        j += 1
                    i = j
                    continue

        total += font_widths[ch]
        i += 1

    if total > last_line:
        last_line = total
    return last_line
