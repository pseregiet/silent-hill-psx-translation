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

from saveload import dump as saveload_dump, patch as saveload_patch
from options import dump as options_dump, patch as options_patch

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
        with open(output, 'wb') as f:
            f.write(silent)


def dump_data(silent: memoryview):
    Path("./dump-new").mkdir(parents=True, exist_ok=True)
    dump_font(silent)
    dump_maps(silent)
    dump_bodyprog(silent)
    options_dump(silent)
    saveload_dump(silent)

def patch_data(silent: memoryview):
    read_font_widths()
    patch_font(silent)
    patch_maps(silent)
    patch_bodyprog(silent)
    options_patch(silent)
    saveload_patch(silent)
    xorBodyProg(silent)


main()
