#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple
from bodyprog import *

def main():
    silent_path = sys.argv[1]
    with open(silent_path, 'rb') as f:
        data = bytearray(f.read())
        silent = memoryview(data)

    #xorBodyprog(silent)

    #for mi in MapInfos:
        #patch_map(silent, mi)
        #extract_map_messages(silent, mi)

    #patch_map(silent, OverlayInfos[1])
    #extract_bodyprog_messages(silent)

    #patch_bodyprog(silent)
    #with open(silent_path+".new", 'wb') as f:
    #    f.write(silent)

    dump_bodyprog(silent)

main()
