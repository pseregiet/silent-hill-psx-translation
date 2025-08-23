#!/usr/bin/env python3

import sys
import struct
import json
import re
from collections import namedtuple
from PIL import Image
import struct
from collections import Counter

from common import *

Font = OverlayInfo(0x00287, 33, "font16.tim")

def encode_tim(tim: memoryview, png: Image.Image):
    data = tim#.tobytes()
    off = 0
    def read(fmt):
        nonlocal off
        size = struct.calcsize(fmt)
        val = struct.unpack_from(fmt, data, off)
        off += size
        return val if len(val) > 1 else val[0]

    # TIM header
    magic = read("<I")
    if magic != 0x10:
        raise ValueError("Not a TIM file")

    flags = read("<I")
    has_clut = flags & 0x8
    bpp = flags & 0x7  # 0=4bpp, 1=8bpp, 2=16bpp, 3=24bpp

    #palette = []
    if has_clut:
        clut_block_len = read("<I")
        x, y, w, h = read("<HHHH")
        print(x, y, w, h)
        clut_data = data[off: off + (clut_block_len - 12)]
        off += clut_block_len - 12
        for i in range(w * h):
            c = struct.unpack_from("<H", clut_data, i * 2)[0]
            #palette.extend(bgr555_to_rgb(c))

    # Image block
    img_block_len = read("<I")
    x, y, w, h = read("<HHHH")
    print(x, y, w, h)
    img_data = data[off: off + (img_block_len - 12)]
    off += img_block_len - 12

    if bpp == 0:  # 4bpp
        for j in range(h):
            for i in range(w*2):
                c1 = png.getpixel(((i*2) + 0, j))
                c2 = png.getpixel(((i*2) + 1, j))
                img_data[j * (w*2) + i] = c1 | (c2 << 4)
    

def decode_tim(memory: memoryview):
    data = memory.tobytes()
    off = 0

    def read(fmt):
        nonlocal off
        size = struct.calcsize(fmt)
        val = struct.unpack_from(fmt, data, off)
        off += size
        return val if len(val) > 1 else val[0]

    def bgr555_to_rgb(c: int) -> tuple[int, int, int, int]:
        r = (c & 0x1F) << 3
        g = ((c >> 5) & 0x1F) << 3
        b = ((c >> 10) & 0x1F) << 3
        if r == 0 and g == 0 and b == 0:
            g = 255
            b = 255

        return r, g, b

    # TIM header
    magic = read("<I")
    if magic != 0x10:
        raise ValueError("Not a TIM file")

    flags = read("<I")
    has_clut = flags & 0x8
    bpp = flags & 0x7  # 0=4bpp, 1=8bpp, 2=16bpp, 3=24bpp

    palette = []
    if has_clut:
        clut_block_len = read("<I")
        x, y, w, h = read("<HHHH")
        print(x, y, w, h)
        clut_data = data[off: off + (clut_block_len - 12)]
        off += clut_block_len - 12
        for i in range(w * h):
            c = struct.unpack_from("<H", clut_data, i * 2)[0]
            palette.extend(bgr555_to_rgb(c))

    # Image block
    img_block_len = read("<I")
    x, y, w, h = read("<HHHH")
    img_data = data[off: off + (img_block_len - 12)]
    off += img_block_len - 12

    if bpp == 0:  # 4bpp
        out = Image.new("P", (w * 4, h))
        out.putpalette(palette, "RGB")
        pixels = out.load()
        for j in range(h):
            for i in range(w * 2):  # 2 pixels per byte
                byte = img_data[j * w * 2 + i]
                c1 = byte & 0x0f
                c2 = (byte >> 4) & 0x0f
                px = i * 2
                pixels[px, j] = c1
                pixels[px + 1, j] = c2

    elif bpp == 1:  # 8bpp
        out = Image.new("RGB", (w * 2, h))
        pixels = out.load()
        for j in range(h):
            for i in range(w * 2):
                idx = img_data[j * w * 2 + i]
                pixels[i, j] = idx
    
    #elif bpp == 2:  # 16bpp direct color
    #    out = Image.new("RGBA", (w, h))
    #    pixels = out.load()
    #    for j in range(h):
    #        for i in range(w):
    #            c = struct.unpack_from("<H", img_data, (j * w + i) * 2)[0]
    #            pixels[i, j] = bgr555_to_rgba(c)
    #
    #elif bpp == 3:  # 24bpp direct color
    #    out = Image.new("RGBA", (w, h))
    #    pixels = out.load()
    #    for j in range(h):
    #        for i in range(w):
    #            base = (j * w + i) * 3
    #            b = img_data[base]
    #            g = img_data[base + 1]
    #            r = img_data[base + 2]
    #            pixels[i, j] = (r, g, b, 255)
    #
    else:
        raise ValueError("Unsupported TIM bpp mode")

    return out

def flat_to_atlas(img: Image.Image) -> Image.Image:
    w, h = img.size
    if (w, h) != (1024, 16):
        raise ValueError(f"Unexpected image size {w}x{h}, expected 1024x16")

    out = Image.new("P", (256, 16 * 4))
    out.putpalette(img.getpalette())

    for i in range(4):
        box = (i * 256, 0, (i + 1) * 256, 16)
        chunk = img.crop(box)
        out.paste(chunk, (0, i * 16))

    return out

def atlas_to_flat(img: Image.Image) -> Image.Image:
    w, h = img.size
    if (w,h) != (256, 64):
        raise ValueError(f"Unexpected image size {w}x{h}, expected 256x64")

    out = Image.new("P", (1024, 16))
    out.putpalette(img.getpalette())
    for i in range(4):
        box = (0, i*16, 256, 16 + (i*16))
        chunk = img.crop(box)
        out.paste(chunk, (i*256, 0))

    return out

def dump_font(silent: memoryview):
    fonttim = extract_overlay(silent, Font)
    pngimg = decode_tim(fonttim)
    pngimg = flat_to_atlas(pngimg)
    pngimg.save("dump/font16.png", "PNG")

def patch_font(silent: memoryview):
    fonttim = extract_overlay(silent, Font)
    newimg = Image.open("dump/font16.png")
    newimg = atlas_to_flat(newimg)
    encode_tim(fonttim, newimg)

