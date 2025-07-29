#!/usr/bin/env python3

import sys
import struct
import re
from prompt_toolkit import prompt

line_index = 0
translated_lines = []
def read_translated_lines(infile):
    global translated_lines
    with open(infile, "r", encoding="utf-8") as f:
        content = f.read()

    translated_lines = [entry.strip() for entry in content.split('\n-------') if entry.strip()]

def get_next_translated_line():
    global line_index
    global translated_lines
    r = translated_lines[line_index]
    line_index += 1
    return fix_encoding(r)
    

def read_c_string(data, offset):
    end = data.find(b'\x00', offset)
    return data[offset:end].decode('ascii')

def fix_encoding(txt):
    return txt.replace(' ', '@@@').replace('_', ' ').replace('@@@', '_').replace('\n', ' ~N ')

def nice_text(txt):
    txt = clean_tabs(txt)
    txt = txt.replace('\n', '')
    return txt.replace(' ', '@@@').replace('_', ' ').replace('@@@', ' ').replace(' ~N', '\n') + "\n-------\n"

def clean_tabs(s):
    return re.sub(r'(?<!\))\t+', '', s)

def find_blob_in_bin(blob, data, name):
    r = data.find(blob)
    if r == -1:
        print(f"can't find a blob {name}")
        sys.exit(1)

    return r

if len(sys.argv) != 3:
    print("Usage: translate_strings.py <text_file> <bin_file>")
    sys.exit(1)

text_file = sys.argv[1]
bin_file = sys.argv[2]
data = None
with open(bin_file, 'rb') as f:
    data = bytearray(f.read())


# Step 3: Read .asciz entries (address + text)
asciz_entries = {}
with open(text_file, encoding='utf-8') as f:
    for line in f:
        if '.asciz' in line:
            try:
                comment, rest = line.split('*/')
                addr = int(comment.split()[-1], 16)
                q1 = rest.index('"') + 1
                q2 = rest.rindex('"')
                text = rest[q1:q2]
                asciz_entries[addr] = text
            except:
                continue
base = next(iter(asciz_entries))

def extract_text_blob(asciz_entries, base):
    blob = bytearray()
    ptr = base
    for addr in asciz_entries:
        txt = asciz_entries[addr]
        decoded = bytes(txt, 'utf-8').decode('unicode_escape')
        encoded = decoded.encode('utf-8') + b'\x00'
        print(f"...{encoded}...")

        blob.extend(encoded)
        ptr += len(encoded)

        align = (ptr + 3 ) & ~3
        blob.extend(b'\x00' * (align - ptr))
        ptr = align

    return blob
        

blob_of_text = b''
ptr_blob = b''.join(struct.pack('<I', k) for k, v in enumerate(reversed(asciz_entries)))
ptr_table_offset = find_blob_in_bin(ptr_blob, data, "ptr")

txt_blob = extract_text_blob(asciz_entries, base)
text_data_offset = find_blob_in_bin(txt_blob, data, "txt")

with open(text_file+".tr.txt", 'w', encoding='utf-8') as f:
    for addr in asciz_entries:
        txt = asciz_entries[addr]
        decoded = bytes(txt, 'utf-8').decode('unicode_escape')
        f.write(nice_text(decoded))
        #encoded = decoded.encode('utf-8') + b'\x00'

