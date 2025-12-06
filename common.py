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
    line = line.replace('ą', '\'').replace('ż', '*').replace('ć', 'Q').replace('ę', '/').replace('Ł', '\'')
    line = line.replace('ł', ';').replace('ń', '<').replace('ó', '>').replace('ś', '[').replace('ź', '&')
    return line

def read_font_widths(indir: str):
    with open(f"{indir}/bodyprog.json", 'r') as f:
        data = json.load(f)
    data = data["font_width"]

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

def text_w(line):
    line = encode_local_text(line)
    line = line.replace(' ', '_').replace('{~N}', '\n')
    line = re.sub(r'\{~.*?\}', '', line)
    current = 0
    maxlen = 0
    for c in line:
        if c == '_' or c == '\t':
            current += 6
            continue
        if c == '\n':
            maxlen = max(maxlen, current)
            current = 0
            continue
        try:
            current += font_widths[c]
        except:
            pass
    print(f"{line}, {maxlen}, {current}")
    return max(maxlen, current)



def nice_encode(line):
    return line.replace('\t', '').replace('\n', '{~N}').replace('_', ' ').replace('\x01', '')

def game_encode(line):
    line = line.replace(' ', '_').replace('{~N}', '\n')
    line = encode_local_text(line)
    print(line)
    return line.encode('ascii') + b'\x00'

def load_text_table(ovi: FileInfo, tableptr, tablecount):
    data = {}
    for i in range(tablecount):
        txtptr = r_u32(ovi, tableptr + (i*4))
        print(type(txtptr))
        data[i] = nice_encode(read_c_string2(ovi, txtptr))
    return data

def patch_text_table(ovi: FileInfo, tableptr, text):
    def iter_values(x):
        if isinstance(x, dict):
            return x.values()
        return x

    for i, val in enumerate(iter_values(text)):
        news = game_encode(val)
        txt_ptr = get_new_blob_ptr(news, ovi)
        w_u32(ovi, txt_ptr, tableptr + (i*4))


