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
from fileinfo import *

Font = OverlayInfo(0x00287, 33, "font16.tim", None, None)

Textures = [
    FileInfo(0x00066, 303, "2ZANKO_E", 0, None, None),
    FileInfo(0x002ea, 151, "NO_MCD_E", 0, None, None),
    FileInfo(0x002c4, 151, "NO_BLK_E", 0, None, None),
    FileInfo(0x088b4, 603, "MP_HSP2F", 0, None, None),
    FileInfo(0x08570, 603, "MP_0TOWN", 0, None, None),
    FileInfo(0x085bc, 603, "MP_BSTLN", 0, None, None),
    FileInfo(0x08608, 603, "MP_DRN1F", 0, None, None),
    FileInfo(0x08654, 603, "MP_DRN2F", 0, None, None),
    FileInfo(0x086a0, 603, "MP_DRNBK", 0, None, None),
    FileInfo(0x086ec, 603, "MP_HSP1F", 0, None, None),
    FileInfo(0x08738, 603, "MP_HSP2F", 0, None, None),
    FileInfo(0x08784, 603, "MP_HSP3F", 0, None, None),
    FileInfo(0x087d0, 603, "MP_HSPBF", 0, None, None),
    FileInfo(0x0881c, 603, "MP_RSORT", 0, None, None),
    FileInfo(0x08868, 603, "MP_SCL1F", 0, None, None),
    FileInfo(0x088b4, 603, "MP_SCL2F", 0, None, None),
    FileInfo(0x08900, 603, "MP_SCLBF", 0, None, None),
    FileInfo(0x0894c, 603, "MP_SCLRF", 0, None, None),
    FileInfo(0x08e31, 151, "TIPS_E01", 0, None, None),
    FileInfo(0x08e44, 151, "TIPS_E02", 0, None, None),
    FileInfo(0x08e57, 151, "TIPS_E03", 0, None, None),
    FileInfo(0x08e6a, 151, "TIPS_E04", 0, None, None),
    FileInfo(0x08e7d, 151, "TIPS_E05", 0, None, None),
    FileInfo(0x08e90, 151, "TIPS_E06", 0, None, None),
    FileInfo(0x08ea3, 151, "TIPS_E07", 0, None, None),
    FileInfo(0x08eb6, 151, "TIPS_E08", 0, None, None),
    FileInfo(0x08ec9, 151, "TIPS_E09", 0, None, None),
    FileInfo(0x08edc, 151, "TIPS_E10", 0, None, None),
    FileInfo(0x08eef, 151, "TIPS_E11", 0, None, None),
    FileInfo(0x08f02, 151, "TIPS_E12", 0, None, None),
    FileInfo(0x08f15, 151, "TIPS_E13", 0, None, None),
    FileInfo(0x08f28, 151, "TIPS_E14", 0, None, None),
    FileInfo(0x08f3b, 151, "TIPS_E15", 0, None, None),
    FileInfo(0x08a7a, 151, "OP_BRT_E", 0, None, None),
]

def dump_textures(silent: memoryview, outdir: str):
    for t in Textures:
        extract_overlay2(silent, t)
        png = decode_tim(t.memory)
        png.save(f"{outdir}/{t.filename}.png", "PNG")


def rgb_to_rgb555(r, g, b, alpha_bit=1):
    r5 = (r >> 3) & 0x1F
    g5 = (g >> 3) & 0x1F
    b5 = (b >> 3) & 0x1F
    return (alpha_bit << 15) | (b5 << 10) | (g5 << 5) | r5


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

    if has_clut:
        transparencyIndex = png.info.get("transparency")
        print(f": {transparencyIndex}")
        palette = png.getpalette()
        if palette == None:
            raise ValueError("TIM has clut but PNG does not!")

        clut_block_len = read("<I")
        x, y, w, h = read("<HHHH")
        #print(x, y, w, h)
        clut_data = data[off: off + (clut_block_len - 12)]
        off += clut_block_len - 12
        palettelen = len(palette) // 3
        if palettelen > (w * h):
            raise ValueError("PNG has too many colors")

        for i in range(palettelen):
            r = palette[i*3 + 0]
            g = palette[i*3 + 1]
            b = palette[i*3 + 2]
            a = 1
            if r == 0 and g == 0 and b == 0 and transparencyIndex == i:
                a = 0
            new_color = rgb_to_rgb555(r, g, b, a)
            clutidx = i*2
            old_color = struct.unpack_from("<H", clut_data, clutidx)[0]
            clut_data[clutidx: clutidx+2] = struct.pack('<H', new_color)
            aft_color = struct.unpack_from("<H", clut_data, clutidx)[0]
            if aft_color != old_color:
                print(f"color[{i}] = {old_color:016b}, {aft_color:016b}")

    # Image block
    img_block_len = read("<I")
    x, y, w, h = read("<HHHH")
    #print(x, y, w, h)
    img_data = data[off: off + (img_block_len - 12)]
    off += img_block_len - 12

    if bpp == 0:  # 4bpp
        for j in range(h):
            for i in range(w*2):
                c1 = png.getpixel(((i*2) + 0, j))
                c2 = png.getpixel(((i*2) + 1, j))
                img_data[j * (w*2) + i] = c1 | (c2 << 4)
    
    elif bpp == 1:  # 8bpp
        for yy in range(h):
            for xx in range(w*2):
                img_data[yy * (w*2) + xx] = png.getpixel((xx, yy))
    
    

def decode_tim(memory: memoryview):
    data = memory.tobytes()
    off = 0

    def read(fmt):
        nonlocal off
        size = struct.calcsize(fmt)
        val = struct.unpack_from(fmt, data, off)
        off += size
        return val if len(val) > 1 else val[0]

    def bgr555_to_rgb(c: int) -> tuple[int, int, int]:
        r = (c & 0x1F) << 3
        g = ((c >> 5) & 0x1F) << 3
        b = ((c >> 10) & 0x1F) << 3

        return r, g, b

    # TIM header
    magic = read("<I")
    if magic != 0x10:
        raise ValueError("Not a TIM file")

    flags = read("<I")
    has_clut = flags & 0x8
    bpp = flags & 0x7  # 0=4bpp, 1=8bpp, 2=16bpp, 3=24bpp

    transparentIndex = None
    palette = []
    if has_clut:
        clut_block_len = read("<I")
        x, y, w, h = read("<HHHH")
        print(x, y, w, h)
        clut_data = data[off: off + (clut_block_len - 12)]
        off += clut_block_len - 12
        for i in range(w * h):
            c = struct.unpack_from("<H", clut_data, i * 2)[0]
            print(f"{c:016b}")
            palette.extend(bgr555_to_rgb(c))
            if c == 0 and transparentIndex == None:
                transparentIndex = i


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
        out = Image.new("P", (w * 2, h))
        out.putpalette(palette, "RGB")
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

    out.info["transparency"] = transparentIndex
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

    out.info["transparency"] = img.info["transparency"]
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

    out.info["transparency"] = img.info["transparency"]
    return out

def dump_font(silent: memoryview, outdir: str):
    fonttim = extract_overlay(silent, Font)
    pngimg = decode_tim(fonttim)
    pngimg = flat_to_atlas(pngimg)
    pngimg.save(f"{outdir}/font16.png", "PNG")

def patch_font(silent: memoryview, indir: str):
    fonttim = extract_overlay(silent, Font)
    newimg = Image.open(f"{indir}/font16.png")
    newimg = atlas_to_flat(newimg)
    encode_tim(fonttim, newimg)

def patch_textures(silent: memoryview, indir: str):
    for t in Textures:
        extract_overlay2(silent, t)
        png = Image.open(f"{indir}/{t.filename}.png")
        encode_tim(t.memory, png)
