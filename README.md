# Silent Hill (PSX) Translation Patch

This tool was made for the purpose of translating Silent Hill to the Polish language. It is released to support translation into other languages.

It handles:
* Text of arbitrary length (total length of the text still must fit within the constrains)
* Ability to patch the font to make use of more font glyphs
* Correct positioning on the screen
* Moving around the screen interface in the options screen to make room for longer text

And more

Note: Currently only the NTSC version is supported.

# Usage
```
# first extract the SILENT file from your bin/cue/cd.
# dump text and textures from SILENT to output-dir
python3 shtp.py dump SILENT output-dir

# apply patches from input-dir and create new SILENT
python3 shtp.py patch SILENT input-dir NEW-SILENT
# now replace SILENT with NEW-SILENT on the disk 
```

# Brief explanation of the tech:

There are 4 files on the SH1 disk:
* SYSTEM.CNF
* SLUS_007.07
* SILENT
* HILL

We only care about `SILENT`. It's a container file containg most of the game textures and binaries called `overlays`. Each level has an overlay which contains
the dialog lines for that level. There are also strings in `bodyprog` (the main engine), `options`, `saveload` and `credits`. For this project we left `credits` unpached, but given the foundations here you can easily extend the translation to the `credits` if you want to.

Most of the text is stored in big tables, but some of it is hardcoded and used by the code directly. In either case, we declare all memory that is occupied by the text and stuff the new text there, fixing all the pointers on the way. We also patch the string position based on its length (it's hardcoded in all of the game).

The original font is made out of 84 glyphs and is stored in one 1024x16 texture. However, this texture had some gaps (for technical reasons) so for the ease of use
this tool will convert this texture into a 21x4 glyphs atlas and convert it back to the game's format. There's also a table of width for each glyph. If you patch in new
characters, this table will have to also be updated.

Few more minor patches added are:
* You can remove the usage of a dedicated left quote in the main menu to only use the right quote for both sides of the text. That gives you one free glyph to patch.
* In the inventory screen you can move the name of the item string to the left, replacing the "Name: " label. Giving you more room for a long name.
* You can add your splash screen after the Konami and KCET logo.
* You can patch out the buggy memo (this was already fixed in European and Japanese release, only NTSF was affected). Thanks @emoose for figuring out the easy binary
patch for this bug.

Code by Patryk Seregiet (c) 2025. Licensed under MIT. 

Shoutout to the sillent hill decomp team. It wouldn't be as complete without it. https://github.com/Vatuu/silent-hill-decomp

