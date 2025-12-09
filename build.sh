#!/bin/bash
./functions.py patch SILENT v2-dump iso-extract/SILENT.
psxbuild iso-extract/ -c patched.cue
