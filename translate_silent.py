#!/usr/bin/env python3

import sys
import struct

line_index = 0
translated_lines = []
def read_translated_lines(infile):
    with open(infile, "r", encoding="utf-8") as f:
        content = f.read()

    return [entry.strip() for entry in content.split('\n-------') if entry.strip()]

def get_next_translated_line():
    global line_index
    global translated_lines
    r = translated_lines[line_index]
    line_index += 1
    return fix_encoding(r)

def fix_encoding(txt):
    txt = txt.replace('ł', ';').replace('ó', '*').replace('ę', '>').replace('ą', '^')
    txt = txt.replace('ż', '=').replace('ć', '<').replace('ń', '+')
    return txt.replace(' ', '@@@').replace('_', ' ').replace('@@@', '_').replace('\n', ' ~N ')

def find_blob_in_bin(blob, data, name):
    r = data.find(blob)
    if r == -1:
        print(f"can't find a blob {name}")
        sys.exit(1)

    return r

text_file = sys.argv[1]
bin_file = sys.argv[2]
data = None
with open(bin_file, 'rb') as f:
    data = bytearray(f.read())


def read_asciz(text_file):
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

asciz_entries = read_asciz(text_file)
base = next(iter(asciz_entries))

def build_old_text_blob(asciz_entries, base):
    blob = b''
    ptr = base
    for k, v in asciz_entries.items():
        decoded = bytes(v, 'utf-8').decode('unicode_escape')
        encoded = decoded.encode('utf-8') + b'\x00'
        print(f"...{encoded}...")

        blob.extend(encoded)
        ptr += len(encoded)

        align = (ptr + 3 ) & ~3
        blob.extend(b'\x00' * (align - ptr))
        ptr = align

    return blob

def build_new_text_blob(asciz_entries, base):
    blob = b''
    table = []
    ptr = base
    for k, v in asciz_entries.items():
        new_text = get_next_translated_line()
        offset = len(blob_of_text)
        blob_of_text += new_text.encode('ascii') + b'\x00'
        table.append(base + offset)

    return blob, table

        

ptr_blob = b''.join(struct.pack('<I', k) for k, v in enumerate(reversed(asciz_entries)))
ptr_table_offset = find_blob_in_bin(ptr_blob, data, "ptr")

txt_blob = build_old_text_blob(asciz_entries, base)
text_data_offset = find_blob_in_bin(txt_blob, data, "txt")

newblob, newtable = build_new_text_blob(asciz_entries, base)
