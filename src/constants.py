# Copyright (c) 2023, Schubert Nico (Github: NLS-04)
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. 


APP_NAME   = "Consumption recorder"
APP_AUTHOR = "Github_" 
VERSION    = '1.1'

TITLE =\
rf"""
+ ----------------------------------------------------------------------- +
| __     __           _                               _                   |
| \ \   / /___  _ __ | |__   _ __  __ _  _   _   ___ | |__   ___          |
|  \ \ / // _ \| '__|| '_ \ | '__|/ _` || | | | / __|| '_ \ / __| _____   |
|   \ V /|  __/| |   | |_) || |  | (_| || |_| || (__ | | | |\__ \|_____|  |
|    \_/  \___||_|   |_.__/ |_|   \__,_| \__,_| \___||_| |_||___/         |
|                     _          _           _  _         _               |
|  _ __   _ __  ___  | |_  ___  | | __ ___  | || |  __ _ | |_  ___   _ __ |
| | '_ \ | '__|/ _ \ | __|/ _ \ | |/ // _ \ | || | / _` || __|/ _ \ | '__||
| | |_) || |  | (_) || |_| (_) ||   <| (_) || || || (_| || |_| (_) || |   |
| | .__/ |_|   \___/  \__|\___/ |_|\_\\___/ |_||_| \__,_| \__|\___/ |_|   |
| |_|                                                                     |
|                                                            version: {VERSION:.3s} |
+ ----------------------------------------------------------------------- +
"""

# MENUS = [ # OLD
#     "Ablesungen einsehen",
#     "Personen   einsehen",
#     "Ablesungen hinzufügen / überschreiben",
#     "Personen   hinzufügen / überschreiben",
#     "Jahresabrechnung erstellen",
#     "Protokoll exportieren - PDF",
# ]

from tabulate import SEPARATING_LINE

MENUS = [
    [ "1)", "Ablesungen einsehen" ],
    [ "2)", "Personen   einsehen" ],
    SEPARATING_LINE,
    [ "3)", "Ablesungen hinzufügen / überschreiben" ],
    [ "4)", "Personen   hinzufügen / überschreiben" ],
    SEPARATING_LINE,
    [ "5)", "Ablesungen entfernen" ],
    [ "6)", "Personen   entfernen" ],
    SEPARATING_LINE,
    # [ "7)", "Jahresabrechnung erstellen" ],
    [ "7)", "INOP - (Jahresabrechnung erstellen)" ],
    [ "8)", "Protokoll exportieren - PDF" ],
]

KEYBOARD_SLEEP_TIME = 0.5

# Digitscount (prePoint, postPoint)
DIGIT_LAYOUT_ELECTRICITY = (6,1)
DIGIT_LAYOUT_GAS         = (5,3)
DIGIT_LAYOUT_WATER       = (5,3)
DIGIT_LAYOUT_DELTA       = (2,3)

DATE_STR_FORMAT = "%d.%m.%Y"

NAME_ELECTRICITY = "Strom"
NAME_GAS         = "Gas"
NAME_WATER       = "Wasser"


TABLE_HEADER_READINGS_SIMPLE = [ "Datum", NAME_ELECTRICITY, NAME_GAS, NAME_WATER ]
TABLE_HEADER_PERSONS_SIMPLE  = [ "Name", "Einzugs-\ndatum", "Auszugs-\ndatum"]

TABLE_HEADER_READINGS_DETAIL = [ "Datum\n      Delta", f"{NAME_ELECTRICITY:^17s}\nDelta/Tag   Delta", f"{NAME_GAS:^17s}\nDelta/Tag   Delta", f"{NAME_WATER:^17s}\nDelta/Tag   Delta" ]
TABLE_HEADER_PERSONS_DETAIL  = [ "Name", "Einzugs-\ndatum", "Auszugs-\ndatum", "Bewohnte-\nmonate", "Voraussichtliche\nAbrechungen" ]

PDF_FONT_TABLE = "Courier"
PDF_FONT_TITLE = "Courier-Bold"
PDF_FONTSIZE_NOTES = 7


NL = '\n'

if __name__ == "__main__":
    print( *TABLE_HEADER_READINGS_DETAIL, sep=2*NL )