#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple

OverlayInfo = namedtuple("OverlayInfo", ["sector_start", "block_size", "filename"])

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


