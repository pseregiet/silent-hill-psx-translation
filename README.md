This code was used to produce the polish translation of Silent Hill for Playstation 1. A brief explanation of the tech:

There are 4 files on the SH1 disk:
* SYSTEM.CNF
* SLUS_007.07
* SILENT
* HILL

SILENT is a container file, it contains all the textures and so called "overlays" which are part of the code. Because PS1 has so little memory the game's code
is split into several binaries. Roughly, every level is it's own small binary. Each of those binaries has dialog strings. They are just string literals in C.
There is also a pointer table to these strings.

All dialog strings are next to each other in memory with additional 1-3 padding bytes to align them to 4 bytes. Also these strings contain a lot of extra characters
that are ignored by the game engine and do not affect the way the text is displayed. For example, a lot of the strings contain the \n and \t characters (new line and tab).
This is most likely because they were writen in the source code in this way:
```
const char *notepad_dialog = "Someday,_someone_may_experience ~N
                              these_bizarre_events._Hopefully, ~N
                              they_will_find_my_notes_useful. ~E ";
```
Because of this we have extra bytes of spare room for new text.
We can treat the entire block of memory that is ocuppied by these strings as one buffer to which we will write our new text. Then we have to update the pointer table
to point to our new strings. This way we can have dialog lines of arbitrary length, as long as their total size does not exceed the original block size.

Some strings are duplicated in each overlay. In the original code they were probably included like.
```
#include "common_strings.h"
```
For simplicity this code does not do the same, all strings are as is in each overlay file. This is benefitial in case you need more room for long text. The long string "Someday, someone may experience..." is in every overlay, but is displayed only once in the entire game, when you use the notepad for the first time. In a desparate situation this string can be overwriten since the possiblity of it being used in late game is extremely low.

These strings are encoded in a specific way. Thankfuly it's all based on ASCII:
* ~N is a line break (\n is ignored).
* ~E waits for a button press.
* ~Cn changes color. Default white seems to be ~C7.
* ~S4 is the "Yes/No" selection. (not sure if other Sn are possible)
* ~Jn(n.n)\t Seems to be related to cutscene timing. This control sequence requires a tab character after it (\t).
* ~Ln Position or size (not tested).
*_ (underscore) is a visible space.
* (space) seems to be only used to separate control characters from the text, but is not required.

Text writen in the mapN_NN.asciz.tr.txt is in "plain text" format. New lines will be replaced by ~N, normal spaces will be replaced with underscores. This code will also replace polish accented characters like ąężźćńś with spare ASCII characters that are not otherwise used by the game but were defined in the font file. You can replace them if your language requires additional characters. This is done in "fix_encoding" function in translate_silent.py
