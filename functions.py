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
from konami_b import patch_konami_b

from saveload import dump_saveload, patch_saveload
from options import dump_options, patch_options

def print_help():
    print("Silent Hill (PSX) Translation tool")
    print("(c) Patryk Seregiet 2025")
    print("Shout out to decomp team https://github.com/Vatuu/silent-hill-decomp")
    print("To dump:  shtt.py dump original-SILENT dump-output-dir")
    print("To patch: shtt.py patch original-SILENT dump-input-dir patched-SILENT")


def main():
    if len(sys.argv) < 4:
        print_help()
        return

    silent_path = sys.argv[2]
    with open(silent_path, 'rb') as f:
        data = bytearray(f.read())
        silent = memoryview(data)

    mode = sys.argv[1]
    if (mode == "dump"):
        dump_data(silent, sys.argv[3])
    else:
        patch_data(silent, sys.argv[3])
        with open(sys.argv[4], 'wb') as f:
            f.write(silent)


def dump_data(silent: memoryview, outdir):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    dump_bodyprog(silent, outdir)
    dump_options(silent, outdir)
    dump_saveload(silent, outdir)
    dump_font(silent, outdir)
    dump_maps(silent, outdir)
    dump_textures(silent, outdir)


def patch_data(silent: memoryview, indir):
    read_font_widths(indir)
    patch_bodyprog(silent, indir)
    patch_options(silent, indir)
    patch_saveload(silent, indir)
    patch_font(silent, indir)
    patch_textures(silent, indir)
    patch_konami_b(silent)
    patch_maps(silent, indir)
    xorBodyProg(silent)


main()
