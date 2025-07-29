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
    return txt.replace(' ', '@@@').replace('_', ' ').replace('@@@', ' ').replace(' ~N ', '\n') + "\n-------"

def clean_tabs(s):
    return re.sub(r'(?<!\))\t+', '', s)

def concat_hex_lines_to_blob(filename):
    blob = bytearray()
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Hex lines start with /* and contain only hex digits (and maybe 0s) inside the comment
            if line.startswith("/*") and line.endswith("*/"):
                # Extract the hex string inside the comment, ignoring spaces
                content = line[2:-2].strip()
                if all(c in "0123456789ABCDEFabcdef" for c in content):
                    # Convert hex string to bytes and append
                    blob.extend(bytes.fromhex(content))
    return bytes(blob)

def find_blob_in_bin(blob, data):
    r = data.find(blob)
    if r == -1:
        print("can't find a blob")
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

read_translated_lines("translated_" + text_file)

# Step 1: Read .word pointers
pointers = []
new_pointers = []
base = 0
with open(text_file, encoding='utf-8') as f:
    for line in f:
        if '.word' in line:
            parts = line.strip().split()
            for part in parts:
                if part.startswith('0x') and len(part) == 10:
                    pointers.append(int(part, 16))
                    break

# Step 2: Find pointer table offset in binary
blob = b''.join(struct.pack('<I', p) for p in pointers)
ptr_table_offset = find_blob_in_bin(blob, data)

old_blob_of_text = concat_hex_lines_to_blob(text_file)
text_data_offset = find_blob_in_bin(old_blob_of_text, data)

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

blob_of_text = b''
base = next(iter(asciz_entries))
for k, v in asciz_entries.items():
    #deff = v.replace('\\t', '\t').replace('\\n', '').replace('~N', '~N ')
    #deff = clean_tabs(deff)

    #new_text = deff#prompt("Translate:\n", default=deff)
    #print(nice_text(new_text))
    #new_text = fix_encoding(new_text)
    new_text = get_next_translated_line()
    offset = len(blob_of_text)
    blob_of_text += new_text.encode('ascii') + b'\x00'
    new_pointers.append(base + offset)

# Step 6: Build addr map and update pointer table in same order
print("\n--- Updated Pointer Table ---\n")
for p in new_pointers:
    print(f"    .word 0x{p:08X}")

print("\n--- Translated Strings ---\n")
for e in new_pointers:
    offset = e - base
    orgstr = read_c_string(blob_of_text, offset)
    fix = orgstr#.replace('\n', '~N')
    print(f'    /* {e:08X} */ .asciz "{fix}"')


for i, ptr in enumerate(reversed(new_pointers)):
    offset = ptr_table_offset + i * 4
    org = data[offset:offset+4]
    org = struct.unpack('<I', org)[0]
    data[offset:offset+4] = struct.pack('<I', ptr)
    print(f"{offset:x} = {org:x} = {ptr:x}")

data[text_data_offset:text_data_offset + len(blob_of_text)] = blob_of_text

# Write modified data to new file
with open('modified.bin', 'wb') as f:
    f.write(data)

with open("Silent Hill (USA).bin", 'wb') as f:
    f.write(data)

