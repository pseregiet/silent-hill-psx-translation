#!/usr/bin/env python3

import sys
import os
import struct
import json
import re
from collections import namedtuple
from pathlib import Path
from bodyprog import *
from textures import *
from maps import *

def main():
    silent_path = sys.argv[1]
    with open(silent_path, 'rb') as f:
        data = bytearray(f.read())
        silent = memoryview(data)

    mode = sys.argv[2]
    if (mode == "dump"):
        dump_data(silent)
    else:
        output = sys.argv[3]
        patch_data(silent)
        with open("../patch-SILENT", 'wb') as f:
            f.write(silent)


def dump_data(silent: memoryview):
    Path("./dump").mkdir(parents=True, exist_ok=True)
    dump_font(silent)
    dump_bodyprog(silent)
    dump_maps(silent)

def patch_data(silent: memoryview):
    patch_font(silent)
    patch_bodyprog(silent)

    read_font_widths()
    patch_maps(silent)

main()
