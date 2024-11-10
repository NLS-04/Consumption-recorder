from pathlib import Path
from platformdirs import user_data_path, user_documents_path
from tabulate import SEPARATING_LINE

from generic_lib.utils import digit_layout_t

IN_DEPLOYMENT_MODE: bool = Path(__file__).parent.name != "src"
'''Flag to indicate whether the project was 'compiled' with Pyinstaller into a .exe or folder'''

#-------------------------------------------------------------------------------
# Runtime Dependent
#-------------------------------------------------------------------------------
#  Paths  #
#---------#

PATH_ROOT = Path(__file__).parent if IN_DEPLOYMENT_MODE else Path(__file__).parent.parent

PATH_VERSION = PATH_ROOT.joinpath("VERSION")
PATH_ICON    = PATH_ROOT.joinpath("rsc").joinpath("main.ico")

assert PATH_VERSION.exists() and PATH_ICON.exists(), "Path to resources could not be located"


#-------------------------------------------------------------------------------
# Settable Constance | Runtime Independent
#-------------------------------------------------------------------------------
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
    [ "7)", "Kostenabrechnung erstellen" ],
    [ "8)", "Zeitraumanalyse - manuell" ],
    [ "9)", "Protokoll exportieren - PDF" ],
]


KEYBOARD_SLEEP_TIME = 0.5

# Digits-count (prePoint, postPoint)
DIGIT_LAYOUT_ELECTRICITY = digit_layout_t( 6, 1 )
DIGIT_LAYOUT_GAS         = digit_layout_t( 5, 3 )
DIGIT_LAYOUT_WATER       = digit_layout_t( 5, 3 )
DIGIT_LAYOUT_DELTA       = digit_layout_t( 2, 3 )
DIGIT_LAYOUT_MONEY       = digit_layout_t( 6, 2 )

# see for further language codes: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-lcid/a9eac961-e77d-41a6-90a5-ce1a8b0cdb9c?redirectedfrom=MSDN
LANGUANGE_CODE = "de-DE"
LOCAL_CURRENCY = '€'

# DATE_STR_FORMAT = "%d.%m.%Y"
DATE_STR_FORMAT = "%x"
PLACE_HOLDER    = '_'


# Data base specifics
NAME_FILE_DB = "data.db"

NAME_ELECTRICITY = "Strom"
NAME_GAS         = "Gas"
NAME_WATER       = "Wasser"

TABLE_HEADER_READINGS_SIMPLE = [ "Datum", NAME_ELECTRICITY, NAME_GAS, NAME_WATER ]
TABLE_HEADER_PERSONS_SIMPLE  = [ "Name", "Einzugsdatum", "Auszugsdatum"]


LIST_READING_ATTRIBUTE_NAMES: list[str] = [ NAME_ELECTRICITY, NAME_GAS, NAME_WATER ]
# cspell:ignore Eintr Abls
__TABLE_H_R_M_FORMAT = "{:^24s}\nExtrapolierter Verbrauch\npro Tag    pro Woche\nStandardabweichung p.Tag"
__TABLE_H_R_D_FORMAT = "{:^17s}\nDelta/Tag   Delta"
TABLE_HEADER_READINGS_DETAIL = [ "Datum\n      Delta", *[ __TABLE_H_R_D_FORMAT.format(obj) for obj in LIST_READING_ATTRIBUTE_NAMES ] ]
TABLE_HEADER_READINGS_STATS  = [ "Jahr : Monat\nZeitspanne   Anz. Eintr.\nAblesungen\nTage zw. Abls.|std. Abw.", *[ __TABLE_H_R_M_FORMAT.format(obj) for obj in LIST_READING_ATTRIBUTE_NAMES ] ]
TABLE_HEADER_PERSONS_DETAIL  = [ "Name", "Einzugsdatum", "Auszugsdatum", "Bewohnte Monate", "Voraussichtliche\nAbrechnungen" ]

PDF_FONT_TABLE = "Courier"
PDF_FONT_TITLE = "Courier-Bold"
PDF_FONTSIZE_NOTES = 7

SIZE_TAB  = 4
SIZE_NAME = 32
SIZE_DATE = 10

NL = '\n'


#--------------------------#
#  Derived non-settable's  #
#--------------------------#
PATH_APPDATA = user_data_path( APP_NAME, APP_AUTHOR, roaming=False, ensure_exists=True )

PATH_DB      = PATH_APPDATA.joinpath(NAME_FILE_DB)
PATH_LOGS    = (PATH_APPDATA if IN_DEPLOYMENT_MODE else PATH_ROOT).joinpath("logs")
PATH_PDF     = user_documents_path()


LIST_DIGIT_OBJ_LAYOUTS: list[digit_layout_t] = [ DIGIT_LAYOUT_ELECTRICITY, DIGIT_LAYOUT_GAS, DIGIT_LAYOUT_WATER ]


COUNT_READING_ATTRIBUTES = len( LIST_READING_ATTRIBUTE_NAMES )
COUNT_DIGIT_OBJS         = len( LIST_DIGIT_OBJ_LAYOUTS )


if __name__ == "__main__":
    print( *TABLE_HEADER_READINGS_DETAIL, sep=2*NL )