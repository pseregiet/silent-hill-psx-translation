#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple
from fileinfo import *
from ov_bodyprog import *

OverlayInfo = namedtuple("OverlayInfo", ["sector_start", "block_size", "filename", "offset", "memory"])
font_widths = {}

def to_signed(val, bits=32):
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val

def extract_overlay(silent: memoryview, ovi: OverlayInfo):
    start = (ovi.sector_start - 0x40) * 0x800
    size  = ovi.block_size * 0x100

    return silent[start: start+size]

def extract_overlay2(silent: memoryview, ovi: FileInfo):
    start = (ovi.sector_start - 0x40) * 0x800
    size  = ovi.block_size * 0x100

    ovi.memory = silent[start: start+size]

def read_uint32_le(buf, offset):
    return struct.unpack_from('<I', buf, offset)[0]

def read_u8(buf, offset):
    return struct.unpack_from('<B', buf, offset)[0]

def read_c_string(data: memoryview, offset: int) -> str:
    end = offset
    while end < len(data) and data[end] != 0:
        end += 1
    return data[offset:end].tobytes().decode('ascii')




def r_u32(ovi: FileInfo, offset):
    return struct.unpack_from('<I', ovi.memory, offset - ovi.offset)[0]

def r_s16(ovi: FileInfo, offset):
    return struct.unpack_from('<h', ovi.memory, offset - ovi.offset)[0]

def r_u8(ovi: FileInfo, offset):
    return struct.unpack_from('<B', ovi.memory, offset - ovi.offset)[0]

def w_u32(ovi: FileInfo, val, offset):
    srcblob = struct.pack('<I', val)
    offset = offset - ovi.offset
    ovi.memory[offset: offset + 4] = srcblob

def w_u8(ovi: FileInfo, val, offset):
    srcblob = struct.pack('<B', val)
    offset = offset - ovi.offset
    ovi.memory[offset: offset + 1] = srcblob

def w_s16(ovi: FileInfo, val, offset):
    srcblob = struct.pack('<h', val)
    offset = offset - ovi.offset
    ovi.memory[offset: offset + 2] = srcblob

def w_u16(ovi: FileInfo, val, offset):
    srcblob = struct.pack('<H', val)
    offset = offset - ovi.offset
    ovi.memory[offset: offset + 2] = srcblob

def add_s16(ovi: FileInfo, val, offset):
    org = r_s16(ovi, offset)
    w_s16(ovi, org+val, offset)


def w_blob(ovi: FileInfo, val, offset):
    blen = len(val)
    print(f"{offset:x}, {offset-ovi.offset:x}, {ovi.offset:x}")
    offset = offset - ovi.offset
    ovi.memory[offset: offset + blen] = val

def get_new_blob_ptr(blob, ovi: FileInfo):
    blen = len(blob)
    for bank in ovi.data_banks:
        if bank[1] >= blen:
            bank[1] -= blen
            ret = bank[0]
            w_blob(ovi, blob, ret)
            bank[0] += blen
            return ret

    for bank in BodyProg.data_banks:
        if bank[1] >= blen:
            bank[1] -= blen
            ret = bank[0]
            w_blob(BodyProg, blob, ret)
            ret = bank[0]
            bank[0] += blen
            return ret
    raise MemoryError("Not enough mem ({blen} bytes) for {blob}")

def read_c_string2(ovi: FileInfo, offset: int) -> str:
    offset = offset - ovi.offset
    end = offset
    while end < len(ovi.memory) and ovi.memory[end] != 0:
        end += 1
    return ovi.memory[offset:end].tobytes().decode('ascii')

def patch_blob(dstblob, srcblob, offset):
    bloblen = len(srcblob)
    dstblob[offset: offset + bloblen] = srcblob

def patch_pointer(dstblob, pointer, offset):
    srcblob = struct.pack('<I', pointer)
    patch_blob(dstblob, srcblob, offset)

def patch_u8(dstblob, val, offset):
    srcblob = struct.pack('<B', val)
    patch_blob(dstblob, srcblob, offset)

def patch_u32(dstblob, val, offset):
    srcblob = struct.pack('<I', val)
    patch_blob(dstblob, srcblob, offset)

def encode_local_text(line):
    line = line.replace('ą', '\'').replace('ż', '*').replace('ć', '+').replace('ę', '/')
    line = line.replace('ł', ';').replace('ń', '<').replace('ó', '>').replace('ś', '[').replace('ź', '&')
    return line

def read_font_widths():
    with open("./dump/font_info.json", 'r') as f:
        data = json.load(f)

    for k, v in data.items():
        #if k == '!':
        #    k = '\\'
        #elif k == '&':
        #    k = '^'
        font_widths[k] = v

    print(font_widths)

def text_width(line):
    total = 0
    if type(line) != str:
        line = line.decode("ascii")
    for c in line:
        if c == '_' or c == '\t':
            total += 6
            continue
        try:
            total += font_widths[c]
        except:
            pass
    return total

def accumulate_widths(line, decode=True):
    i = 0
    total = 0
    last_line = 0
    if decode:
        text = line.decode("ascii")
    else:
        text = line

    while i < len(text):
        ch = text[i]

        if ch == '\x00':
            break

        if ch == '\n':
            i += 1
            continue

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

def nice_encode(line):
    return line.replace('\t', '').replace('\n', '{~N}').replace('_', ' ').replace('\x01', '')

def game_encode(line):
    line = line.replace(' ', '_').replace('{~N}', '\n')
    line = encode_local_text(line)
    return line.encode('ascii') + b'\x00'

def load_text_table(ovi: FileInfo, tableptr, tablecount):
    data = {}
    for i in range(tablecount):
        txtptr = r_u32(ovi, tableptr + (i*4))
        print(type(txtptr))
        data[i] = nice_encode(read_c_string2(ovi, txtptr))
    return data

def patch_text_table(ovi: FileInfo, tableptr, tablecount, text):
    for i in range(tablecount):
        news = game_encode(text[str(i)])
        txt_ptr = get_new_blob_ptr(news, ovi)
        w_u32(ovi, txt_ptr, tableptr + (i*4))


