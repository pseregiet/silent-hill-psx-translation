from fileinfo import *

# Separated from the bodyprog.py because other modules have to import it.
# This is because when patching other overlays, if theres no more room
# for new strings we will place them in spare bodyprog banks.

data_banks = [
    # pointer     size
    [ 0x800261E0, 0x34   ],
    [ 0x80027DF8, 0x3A   ],
    [ 0x800262AC, 0x4A   ],
    [ 0x80027F14, 0x7E   ],
    [ 0x8002667C, 0x175C ],
]

BodyProg = FileInfo(0x000CF, 2635, "bodyprog", 0x80024B60, data_banks, None)
