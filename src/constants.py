from pathlib import Path

  ####################
 # RUNTIME DEPENDED #
####################
### PATH-ING ###
PATH_ROOT = Path(__file__).parent

# Path to VERSION when executing .exe
PATH_VERSION = PATH_ROOT.joinpath("VERSION")
if not PATH_VERSION.exists():
    # Path to VERSION when executing .py
    PATH_VERSION = PATH_ROOT.parent.joinpath("VERSION")

# Path to ICON file when executing .exe
PATH_ICON = PATH_ROOT.joinpath("rsc").joinpath("main.ico")
if not PATH_ICON.exists():
    # Path to ICON file when executing .py
    PATH_ICON = PATH_ROOT.parent.joinpath("rsc").joinpath("main.ico")


  ############################################
 # SETTABLE CONSTANTS | RUNTIME INDEPENDENT #
############################################

APP_NAME   = "Consumption recorder"
APP_AUTHOR = "github NLS-04"
VERSION    = ( f := PATH_VERSION.open(), f.readline()[0:-1], f.close() )[1]


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
| {'version: '+VERSION:>71s} |
+ ----------------------------------------------------------------------- +
"""

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
    [ "8)", "Analyse - manuell" ],
    [ "9)", "Protokoll exportieren - PDF" ],
]

KEYBOARD_SLEEP_TIME = 0.5

# Digits-count (prePoint, postPoint)
DIGIT_LAYOUT_ELECTRICITY = ( 6, 1 )
DIGIT_LAYOUT_GAS         = ( 5, 3 )
DIGIT_LAYOUT_WATER       = ( 5, 3 )
DIGIT_LAYOUT_DELTA       = ( 2, 3 )

# see for further language codes: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lcid/a9eac961-e77d-41a6-90a5-ce1a8b0cdb9c?redirectedfrom=MSDN
LANGUANGE_CODE = "de-DE"

# DATE_STR_FORMAT = "%d.%m.%Y"
DATE_STR_FORMAT = "%x"
PLACE_HOLDER    = '_'

NAME_ELECTRICITY = "Strom"
NAME_GAS         = "Gas"
NAME_WATER       = "Wasser"

LIST_READING_OBJ_NAMES: list[str]             = [ NAME_ELECTRICITY, NAME_GAS, NAME_WATER ]
LIST_DIGIT_OBJ_LAYOUTS: list[tuple[int, int]] = [ DIGIT_LAYOUT_ELECTRICITY, DIGIT_LAYOUT_GAS, DIGIT_LAYOUT_WATER ]

TABLE_HEADER_READINGS_SIMPLE = [ "Datum", NAME_ELECTRICITY, NAME_GAS, NAME_WATER ]
TABLE_HEADER_PERSONS_SIMPLE  = [ "Name", "Einzugsdatum", "Auszugsdatum"]

# cspell:ignore Eintr Abls
__TABLE_H_R_M_FORMAT = "{:^24s}\nExtrapolierter Verbrauch\npro Tag    pro Woche\nStandardabweichung p.Tag"
__TABLE_H_R_D_FORMAT = "{:^17s}\nDelta/Tag   Delta"
TABLE_HEADER_READINGS_DETAIL = [ "Datum\n      Delta", *[ __TABLE_H_R_D_FORMAT.format(obj) for obj in LIST_READING_OBJ_NAMES ] ]
TABLE_HEADER_READINGS_STATS  = [ "Jahr : Monat\nZeitspanne   Anz. Eintr.\nAblesungen\nTage zw. Abls.|std. Abw.", *[ __TABLE_H_R_M_FORMAT.format(obj) for obj in LIST_READING_OBJ_NAMES ] ]
TABLE_HEADER_PERSONS_DETAIL  = [ "Name", "Einzugsdatum", "Auszugsdatum", "Bewohnte Monate", "Voraussichtliche\nAbrechnungen" ]

COUNT_READING_OBJS = len( LIST_READING_OBJ_NAMES )
COUNT_DIGIT_OBJS   = len( LIST_DIGIT_OBJ_LAYOUTS)

PDF_FONT_TABLE = "Courier"
PDF_FONT_TITLE = "Courier-Bold"
PDF_FONTSIZE_NOTES = 7

SIZE_TAB  = 4
SIZE_NAME = 32
SIZE_DATE = 10

NL = '\n'

if __name__ == "__main__":
    print( *TABLE_HEADER_READINGS_DETAIL, sep=2*NL )