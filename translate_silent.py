#!/usr/bin/env python3

import sys
import struct

def print_hex(blob):
    hex_string = ' '.join(f'{byte:02X}' for byte in blob)
    print(hex_string)

def read_translated_lines(infile):
    with open(infile, "r", encoding="utf-8") as f:
        content = f.read()

    return [entry.strip() for entry in content.split('\n-------') ]

def fix_encoding(txt):
    txt = txt.replace('ł', ';').replace('ó', '*').replace('ę', '>').replace('ą', '^')
    txt = txt.replace('ż', '=').replace('ć', '<').replace('ń', '+')
    return txt.replace(' ', '@@@').replace('_', ' ').replace('@@@', '_').replace('\n', ' ~N ')

def find_blob_in_bin(blob, data, name):
    r = data.find(blob)
    if r == -1:
        raise Exception(f"can't find a blob {name}")
        #print(f"can't find a blob {name}")
        #print_hex(blob)
        #sys.exit(1)

    return r

def read_asciz(text_file):
    asciz_entries = {}
    with open(text_file, encoding='utf-8') as f:
        for line in f:
            if not '.asciz' in line:
                continue
            try:
                comment, rest = line.split('*/')
                addr = int(comment.split()[-1], 16)
                q1 = rest.index('"') + 1
                q2 = rest.rindex('"')
                text = rest[q1:q2]
                asciz_entries[addr] = text
            except:
                continue
    return asciz_entries

def build_old_text_blob(asciz_entries, base):
    blob = b''
    ptr = base
    for k, v in asciz_entries.items():
        decoded = bytes(v, 'utf-8').decode('unicode_escape')
        encoded = decoded.encode('utf-8') + b'\x00'

        blob += encoded
        ptr += len(encoded)

        align = (ptr + 3 ) & ~3
        blob += (b'\x00' * (align - ptr))
        ptr = align

    return blob

def build_new_ptr_blob(table):
    blob = b''
    for i, ptr in enumerate(reversed(table)):
        blob += struct.pack('<I', ptr)
    return blob

def build_new_txt_and_ptr_blob(asciz_entries, txt_base, filename):
    txt_blob = b''
    table = []
    translated_index = 0
    translated_lines = read_translated_lines(filename + ".tr.txt")
    for k, v in asciz_entries.items():
        new_text = fix_encoding(translated_lines[translated_index])
        translated_index += 1

        offset = len(txt_blob)
        txt_blob += new_text.encode('ascii') + b'\x00'
        table.append(txt_base + offset)

    ptr_blob = build_new_ptr_blob(table)
    return txt_blob, ptr_blob

def patch_blob(game, blob, offset):
    bloblen = len(blob)
    game[offset:offset + bloblen] = blob

def patch_overlay(game, filename):
    print(f"Try overlay {filename}")
    asciz_entries = read_asciz(filename)
    txt_base = next(iter(asciz_entries))

    ptr_blob = b''.join(struct.pack('<I', k) for k, v in reversed(asciz_entries.items()))
    #for k, v in reversed(asciz_entries.items()):
    #    print(f"{k:x}")

    ptr_data_offset = find_blob_in_bin(ptr_blob, game, "ptr")

    txt_blob = build_old_text_blob(asciz_entries, txt_base)
    txt_data_offset = find_blob_in_bin(txt_blob, game, "txt")

    new_txt_blob, new_ptr_blob = build_new_txt_and_ptr_blob(asciz_entries, txt_base, filename)
    patch_blob(game, new_txt_blob, txt_data_offset)
    patch_blob(game, new_ptr_blob, ptr_data_offset)

def main():
    game_in = sys.argv[1]
    game_out = sys.argv[2]
    game = None
    with open(game_in, 'rb') as f:
        game = bytearray(f.read())

    overlays = [ "map0_s00.asciz", "map0_s01.asciz", "map0_s02.asciz", "map1_s00.asciz",
                 "map1_s01.asciz", "map1_s02.asciz", "map1_s03.asciz", "map1_s04.asciz",
                 "map1_s05.asciz", "map1_s06.asciz", "map2_s00.asciz", "map2_s01.asciz",
                 "map2_s02.asciz", "map2_s03.asciz", "map2_s04.asciz", "map3_s00.asciz",
                 "map3_s01.asciz", "map3_s02.asciz", "map3_s03.asciz", "map3_s04.asciz",
                 "map3_s05.asciz", "map3_s06.asciz", "map4_s00.asciz", "map4_s01.asciz",
                 "map4_s02.asciz", "map4_s04.asciz", "map4_s05.asciz", "map4_s06.asciz",
                 "map5_s00.asciz", "map5_s01.asciz", "map5_s02.asciz", "map5_s03.asciz",
                 "map6_s00.asciz", "map6_s01.asciz", "map6_s02.asciz", "map6_s03.asciz",
                 "map6_s04.asciz", "map6_s05.asciz", "map7_s00.asciz", "map7_s01.asciz",
                 "map7_s02.asciz", "map7_s03.asciz" ]

    for ov in overlays:
        try:
            patch_overlay(game, ov)
        except:
            print(f"error with {ov}")
            continue

    with open(game_out, 'wb') as f:
        f.write(game)

main()
