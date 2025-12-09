#!/usr/bin/env python3

import struct
import json
from common import *
from ov_bodyprog import *

Konami = FileInfo(0x00219, 151, "B_KONAMI.BIN", 0x800C9578, None, None)
#based on https://github.com/Vatuu/silent-hill-decomp/blob/master/tools/silentassets/extract.py
def xorKonami():
    outArray = Konami.memory.cast("I") # uint32_t
    seed = 0

    for i, value in enumerate(outArray):
        seed = (seed + 0x01309125) & 0xffffffff
        seed = (seed * 0x03a452f7) & 0xffffffff
        outArray[i] ^= seed

# The logic behind splash screens is more or less like this (skipping irrelevant info):
# 1 show Konami logo
# 2 show KCET logo
# 3.1 if no MC load the no MC background texture
# 3.2 if MC with no free blocks load the no free blocks background texture
# 3.3 otherwise leave the background blank
# 4.1 if save autoload is set, load the saveload overlay and start it.
# 4.2 otherwise play the intro movie.
# While the movie player code is loading the background texture will fade in and out.
# This patch makes case 3.1 and 3.2 use the same texture. If the MC is fine and there is no
# auto load enabled, also load the no MC background texture. This way we can display
# additional credits.

# The konami_b overlay is very tiny. This extra bit of code is stuffed into g_SysWork.npcs_1A0, in bodyprog.
# It's in data, but ps1 doesn't care and this game includes all data in the binary, it's just zeros.
# It's gonna be overwriten once we start playing, but at this stage it's free real estate for early boot code.

def patch_konami_flow():
    bytecode = [
    # 0x800BA160:
        0xF0, 0xA4, 0x82, 0x92, #    lbu  $v0, -0x5b10($s4)
        0x04, 0x00, 0x03, 0x20, #    addi $v1, $zero, 4
        0x06, 0x00, 0x15, 0x20, #    addi $s5, $zero, 6
        0x02, 0x00, 0x43, 0x10, #    beq  $v0, $v1, skip
        0x00, 0x00, 0x00, 0x00, #    nop
    # 0x800BA174:
        0x02, 0x00, 0x15, 0x20, #    addi $s5, $zero, 2
                                #skip:
        0x10, 0x27, 0x03, 0x08, #    j    0x800c9c40
        0x98, 0x05, 0x55, 0xAE, #    sw   $s5, 0x598($s2)
    # 0x800BA180:
        0x06, 0x00, 0x15, 0x20, #    addi $s5, $zero, 6
        0x10, 0x27, 0x03, 0x08, #    j    0x800c9c40
        0x98, 0x05, 0x55, 0xAE, #    sw   $s5, 0x598($s2)
    ]
    w_blob(BodyProg, bytes(bytecode), 0x800BA160)
    w_u32(Konami, 0x0802E860, 0x800C9B08)
    w_u32(Konami, 0x0802E85D, 0x800C9B28)
    w_u32(Konami, 0x0802E858, 0x800C9C3C)
    w_u16(Konami, 3, 0x800C98D4)

def patch_konami_b(silent: memoryview):
    extract_overlay2(silent, Konami)
    xorKonami()
    patch_konami_flow()
    xorKonami()

