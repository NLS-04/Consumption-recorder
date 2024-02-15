from dataclasses import dataclass
from datetime import date, datetime
from math import floor, sqrt
from typing import Callable, Optional

import logging


from tabulate import tabulate, SEPARATING_LINE, PRESERVE_WHITESPACE
from textwrap import indent

from platformdirs import user_documents_path

# helpful docs and guides for reportlab, since i couldn't find any original nice documentation by them
# https://www.reportlab.com/docs/reportlab-reference.pdf
# https://www.reportlab.com/docs/reportlab-userguide.pdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.pdfbase.pdfmetrics import stringWidth

import locale
import webbrowser

import pynput.keyboard as keyboard

# Custom packages
from dbHandler import DBSession, Reading, Person
from constants import *
from gui import Console, Key

from Focus_Frame import Result, Register, TX_func_factory
from Focus_Frame import Manager, Name, Date, Value, Plain_Text
from Focus_Frame import Button_Manager, Button, Confirm_yes_no


##########################################
# template to mark "debug-lines" in code
# TODO: UNDO AFTER TESTING
##########################################

#----------------------------------------------------------------------------------------------------------------------
# TODO's
#----------------------------------------------------------------------------------------------------------------------
# main.py #
#---------#
#! TODO TABULATE - READINGS:         overhauled logical structure to improve readability and maintainability
#! TODO manipulate_readings:         last line of first FM disappears iff any data exists, as for now only happens to `manipulate_readings`
#!// TODO get_tabular_reading_detail:  blank reading values are not printed and all other reading values to the right of the blank one are shifted to the left
#! TODO visualize_reading:           add pyplot plots of consumption rates over time
#! TODO export_to_pdf:               add pyplot plots of consumption rates over time
#! TODO ...:                         auto-loading values for edit don't load when first entering Frame Manager, only after making an input do all interactables update
#! TODO logging:                     put logs folder at the location of the database.

# TODO ...:                         refactor all commends/docs: reading values like gas or water are to be called reading-attributes
# TODO visualize_reading:           add predictions for the upcoming invoice's compensation payment
# TODO do_invoice:                  complete invoice
# TODO manage_interactables:        ? maybe take this out of this function and let the user choose their own Confirm Frame
# TODO ...:                         add better descriptions to all menu/interaction pages
# TODO ...:                         de-hard-code main.py by making Console.write_line str's to constant variables and move them to constants.py
# TODO .spec                        add version-resource-file to .spec

#--------#
# gui.py #
#--------#
#! TODO Console: add option to suppress ctrl-c inputs or to raise an KeyboardInterrupt Exception if not suppressed and pressed
# TODO Key:     integrate pynput.keyboard into Key class
# TODO Console: expect ANSI codes to not work properly, assume that it needs refinement in the future when adding fancy ESC styling
# TODO Console: add icon to terminal window

#------#
# MISC #
#------#
#! TODO main.py      separate code chunks into own specified files
# TODO logging:      refactor logging for all files
#// TODO dbHandler.py: add better typing support


#----------------------------------------------------------------------------------------------------------------------
# CODE BASE
#----------------------------------------------------------------------------------------------------------------------

SESSION = DBSession()

# from tabulate namespace
PRESERVE_WHITESPACE = True

locale.setlocale( locale.LC_ALL, LANGUANGE_CODE )

#----------------------------------------------------------------------------------------------------------------------
# MANAGE LOGGING
#----------------------------------------------------------------------------------------------------------------------
_log_dir = Path(__file__).parent.parent.joinpath("logs")
_log_dir.mkdir( parents=True, exist_ok=True )

_log_path = _log_dir.joinpath("main.log")

_log_path.open("w").close()

class _format( logging.Formatter ):
    fmt_base = "{asctime:<8s} [ {levelname:>8s} ] | @{lineno:>4d}::{identifier:>25s}: "
    
    def __init__(self) -> None:
        super().__init__(self.fmt_base + "{message:s}", "%H:%M:%S", "{")
        
    def format(self, record) -> str:
        record.identifier = record.funcName
        
        s = super().format(record)
        
        if record.exc_text or record.exc_info or record.stack_info:
            return s
        
        l_space = ' ' * ( len(s) - len(record.message) )
        record.message = ('\n'+l_space).join( record.message.splitlines() )
        
        return self.formatMessage(record)

LOGGER = logging.getLogger( __name__ )
LOGGER.setLevel(logging.DEBUG)

_fh = logging.FileHandler( _log_path.as_posix() )
_fh.setLevel(logging.DEBUG)
_fh.setFormatter( _format() )

LOGGER.addHandler( _fh )


#----------------------------------------------------------------------------------------------------------------------
# MENU FUNCTIONS
#----------------------------------------------------------------------------------------------------------------------
def visualize_readings():
    Console.write_line( " --- ABLESUNGEN AUSGEBEN --- ", NL )
    #todo: better description
    
    Console.write_line( generate_printout_readings_all( SESSION.get_reading_all() ) )

def visualize_persons():
    Console.write_line( " --- PERSONEN AUSGEBEN --- ", NL )
    #todo: better description
    
    data = SESSION.get_person_all()
    
    Console.write_line( get_tabular_person_detail( data ), NL )


def manipulate_readings():
    #todo: better description
    
    Console.write_at( " --- ABLESUNG HINZUFÜGEN / ÜBERSCHREIBEN --- ", 0, 0 )

    FM = Manager(True, True).set_position_left_top( SIZE_TAB, 2 )
    
    # appending the date focus
    FM.append( Date( "Datum", preset_dates=get_all_reading_dates() ) )
    
    for i in range(COUNT_READING_ATTRIBUTES):
        FM.append( Value( LIST_READING_ATTRIBUTE_NAMES[i], True, None, LIST_DIGIT_OBJ_LAYOUTS[i] ) )
        FM.append_rule( 0, i+1, TX_func_factory.date_2_value(SESSION, i) )
    
    manage_interactables(
        FM,
        lambda data: SESSION.exists_readings( data[0], data[0] ),
        lambda data: SESSION.add_reading( *data ),
        lambda data, exists_datas: get_tabular_reading_simple( [exists_datas[0], data] ),
        " <-- Neu ",
        "Eine Ablesung mit folgenden Werten ist bereits eingetragen:",
        "Wollen Sie diese Werte überschreiben?",
        "Ablesung erstellt und in der Datenbank eingetragen"
    )

def manipulate_persons():
    #todo: better description
    
    Console.write_at( " --- PERSON HINZUFÜGEN / ÜBERSCHREIBEN --- ", 0, 0 )
    
    names = get_all_names()
    tab   = get_tabular_names(names)
    
    width, height = get_string_dimensions( tab )
    
    Console.write_in( tab, 4, 2, 4+width, 2+height )
    
    with Console.virtual_area( (4+width+ 4, 2), reset_cursor_on_exit=False ):
        Console.write_at( "Name der zu hinzufügenden oder zu überschreibenden Person eingeben", 0, 0 )

        FM = Manager( True, True ).set_position_left_top( SIZE_TAB, 2 )
        
        FM\
            .append( Name( "Name", False, SIZE_NAME, False, names ) )\
            .append( Date( "Einzugsdatum", True, "" ) )\
            .append( Date( "Auszugsdatum", True, "", lambda dat: not Register.get(1) or dat >= Register.get(1) ) )\
            .append_rule( 0, 1, TX_func_factory.name_2_date_move_in(SESSION) )\
            .append_rule( 0, 2, TX_func_factory.name_2_date_move_out(SESSION) )
        

        manage_interactables(
            FM,
            lambda data: SESSION.exists_person( data[0] ),
            lambda data: SESSION.add_person( *data ),
            lambda data, exists_datas: get_tabular_person_simple( [exists_datas[0], data] ),
            " <-- Neu ",
            "Eine Person mit folgenden Werten ist bereits eingetragen:",
            "Wollen Sie diese Werte überschreiben?",
            "Person in die Datenbank eingetragen"
        )


def delete_reading():
    #todo: better description
    
    Console.write_at( " --- ABLESUNG ENTFERNEN --- ", 0, 0 )
    
    # sub menu management
    tab = tabulate( [
        [ "Menü", "Eine Option mit den Tasten 1-2 auswählen" ],
        SEPARATING_LINE,
        [ "1)", "Einen Eintrag entfernen" ],
        [ "2)", "Mehrere Einträge entfernen" ],
        SEPARATING_LINE,
        [ "esc", "Zum Menü zurückkehren" ],
    ], tablefmt="simple", disable_numparse=True, colalign=('right', 'left') )
    tab_width, tab_height = get_string_dimensions( tab )
    
    Console.write_in( tab, SIZE_TAB, 2, SIZE_TAB+tab_width, 2+tab_height)
    
    is_digit, option = digit_input( [1, 2] )
    
    if not is_digit:
        user_decline_prompt(0, 3+tab_height)
        return
    
    with Console.virtual_area( (SIZE_TAB + tab_width + SIZE_TAB, 2), reset_cursor_on_exit=False ):
        # logic management
        # removing only one entry
        if option == 1:
            delete_reading_single()
            
        # removing multiple entries
        if option == 2:
            delete_reading_multiple()

def delete_person():
    Console.write_at( " --- PERSON ENTFERNEN --- ", 0, 0 )
    #todo: better description
    
    names = get_all_names()
    table = get_tabular_names(names)
    
    tab_width, tab_height = get_string_dimensions( table )
    
    Console.write_in( table, SIZE_TAB, 2, SIZE_TAB+tab_width, 2+tab_height)
    
    
    with Console.virtual_area( (SIZE_TAB + tab_width + SIZE_TAB, 2), reset_cursor_on_exit=False ):
        Console.write_at( "Name der zu entfernenden Person eingeben", 0, 0 )
        
        FM = Manager(True, True).set_position_left_top( SIZE_TAB, 2 )
        
        FM\
            .append( Name( "Name", False, SIZE_NAME, True, names ) )
        
        manage_interactables(
            FM,
            lambda data: SESSION.exists_person( data[0] ),
            lambda data: SESSION.remove_person( data[0] ),
            lambda data, exists_datas: get_tabular_person_simple( exists_datas ),
            " <-- Entfernen",
            "Eine Person mit folgenden Werten ist eingetragen:",
            "Wollen Sie diese Person entfernen?",
            "Person aus der Datenbank entfernt"
        )


def do_invoice():
    Console.write_line( " --- ABRECHNUNG DURCHFÜHREN --- ", NL )
    #todo: better description
    
    Console.write_line( "INOP", NL )

def do_analyze():
    Console.write_at( "Manuelle Analyse der Ablesungen über einen Zeitraum (Grenzen des Zeitraums sind inklusiv)", 0, 0 )
    
    FM = Manager(True, True).set_position_left_top( SIZE_TAB, 2 ).append( Confirm_yes_no( "Bestätigen", "Zurück" ) )
    
    result:Result = FM\
        .append( Date( "Datum Anfang", False, "", must_be_listed=False, preset_dates=get_all_reading_dates() ) )\
        .append( Date( "Datum Ende",   False, "", must_be_listed=False, preset_dates=get_all_reading_dates(), predicate=lambda dat: not Register.get(0) or dat >= Register.get(0) ) )\
        .append( Plain_Text( "Soll ein PDF Protokoll erstellt werden?" ) )\
        .append( Button_Manager( (1,0), (1,0) ).append_at(0,0, Button( "PDF erstellen", (3,0) )).finalize() )\
        .join()
    
    if not result.success:
        user_decline_prompt()
        return
    
    date_low, date_high, create_pdf = result
    
    data = SESSION.get_reading_between( date_low, date_high )
    
    Console.write( generate_printout_readings_all( data, False) )
    
    if create_pdf.success and create_pdf.data[0]:
        export_to_pdf( data_readings=data, use_years_for_reading_stats=False, name="export_span_%s_%s.pdf" % (date_low.strftime("%Y%m%d"), date_high.strftime("%Y%m%d")) )
        return
    
    Console.write_line()


def export_to_pdf(
    data_readings              :list[tuple[date, list[float]]] = SESSION.get_reading_all(), # todo: adjust new reading typing
    data_persons               :list[tuple[str, date, date]]   = SESSION.get_person_all(),
    use_years_for_reading_stats:bool                           = True,
    name                       :str                            = "export_%s.pdf" % date.today().strftime("%Y%m%d")
    ) -> None:
    
    Console.write_line( " --- PROTOKOLL EXPORTIEREN - PDF --- ", NL )
    #todo: better description
    
    EXPORT_NAME = str(name)
    TABLE_CONTINUE_STR = '. . .'
    
    # (210mm, 297mm)
    # (595pt, 842pt)
    WIDTH, HEIGHT = A4
    
    file_name = user_documents_path().joinpath( EXPORT_NAME )
    
    file_name.unlink(True)
    file_pdf = file_name.open("xb")
    
    c = canvas.Canvas( file_pdf, A4, 0 )
    
      #########
     # TITLE #
    #########
    c.setFont( PDF_FONT_TITLE, 20 )
    c.drawCentredString( WIDTH/2, 50, "Verbrauchsprotokollator" )
    c.drawCentredString( WIDTH/2, 70, "Übersicht vom %s" % date.today().strftime( DATE_STR_FORMAT ) )
    c.line( 100, 80, WIDTH-100, 80 )
    c.line( 100, 82, WIDTH-100, 82 )
    
    
    RX, RY = 50, 50
    
      ############
     # READINGS #
    ############
    
    # individual readings
    c.setFont( PDF_FONT_TABLE, 16 )
    c.drawString( RX, 120, "Ablesungen:" )
    
    table_readings = generate_printout_readings_detail( data_readings )
    draw_pdf_page( table_readings, c, WIDTH, HEIGHT, RX, RY, 80, PDF_FONT_TABLE, TABLE_CONTINUE_STR )
    
    # statistics readings
    c.setFont( PDF_FONT_TABLE, 16 )
    c.drawString( RX, RY-20, "Statistiken:" )
    
    table_months = generate_printout_readings_statistics( data_readings, use_years_for_reading_stats )
    draw_pdf_page( table_months, c, WIDTH, HEIGHT, RX, RY, 0, PDF_FONT_TABLE, TABLE_CONTINUE_STR )

     
      ###########
     # PERSONS #
    ###########
    c.setFont( PDF_FONT_TABLE, 16 )
    c.drawString( RX, RY-20, "Personen:" )
    
    table = get_tabular_person_detail( data_persons )
    
    draw_pdf_page( table, c, WIDTH, HEIGHT, RX, RY, 0, PDF_FONT_TABLE, TABLE_CONTINUE_STR )
    
    
    c.save()
    
    webbrowser.open_new( file_name.as_uri() )
    
    Console.write_line( '\t', f"Protokoll am {date.today().strftime( DATE_STR_FORMAT )} über alle Werte wurde erstellt", sep='' )
    Console.write_line( '\t', f"und als \"{EXPORT_NAME}\" in Ihrem Dokumenten-Ordner \"{user_documents_path()}\" gespeichert", sep='' )
    
    Console.write_line()


#----------------------------------------------------------------------------------------------------------------------
# HELPER FUNCTIONS
#----------------------------------------------------------------------------------------------------------------------
# MENU FUNCTIONS EXTENSIONS #
#---------------------------#
def delete_reading_single():
    Console.write_at( "Datum des zu entfernenden Eintrags eingeben", 0, 0 )
    
    FM = Manager(True, True).set_position_left_top( SIZE_TAB, 2 )
    
    FM\
        .append( Date( "Datum", False, "", must_be_listed=True, preset_dates=get_all_reading_dates() ) )
    
    manage_interactables(
        FM,
        lambda data: SESSION.exists_readings( data[0], data[0] ),
        lambda data: SESSION.remove_readings( data[0], data[0] ),
        lambda data, exists_datas: get_tabular_reading_simple( exists_datas ),
        " <-- Entfernen",
        "Zu Entfernender Eintrag",
        "Wollen Sie diesen Eintrag entfernen?",
        "Eintrag aus der Datenbank entfernt",
        "Kein Eintrag zum angegebenen Datum gefunden"
    )

def delete_reading_multiple():
    Console.write_at( "Zeitintervall der zu entfernenden Einträge eingeben (Grenzen sind inklusiv)", 0, 0 )
    
    FM = Manager(True, True).set_position_left_top( SIZE_TAB, 2 )
    
    FM\
        .append( Date( "Datum ab",  False, "", must_be_listed=False, preset_dates=get_all_reading_dates() ) )\
        .append( Date( "Datum bis", False, "", must_be_listed=False, preset_dates=get_all_reading_dates(), predicate=lambda dat: not Register.get(0) or dat >= Register.get(0) ) )
    
    manage_interactables(
        FM,
        lambda data: SESSION.exists_readings( data[0], data[1] ),
        lambda data: SESSION.remove_readings( data[0], data[1] ),
        lambda data, exists_data: get_tabular_reading_simple( exists_data ),
        " <-- Entfernen",
        "Zu Entfernende Einträge",
        "Wollen Sie diese Einträge entfernen?",
        "Einträge aus der Datenbank entfernt",
        "Kein Einträge im angegebenen Zeitraum gefunden"
    )

#-----------------------------#
# UI - GENERAL FLOW FUNCTIONS #
#-----------------------------#
def flush_menu() -> None:
    Console.clear()
    Console.write_line( TITLE )
    
    Console.write_line( "Eine Option mit den Tasten 1-9 auswählen" )
    print_menu_options()
    Console.write_line( "Um das Programm zu verlassen: Esc drücken", NL )

def print_menu_options() -> None:
    tab = tabulate( MENUS, tablefmt="simple", disable_numparse=True, colalign=('right', 'left') )
    
    Console.write_line( NL, indent( tab, '\t' ), NL, sep='' )

def user_decline_prompt( col:int=None, line:int=None, absolute:bool=True ) -> None:
    if col != None and line != None:
        Console.set_cursor( col, line, absolute )
    Console.write_line( " --- Handlung wurde abgebrochen" )

def user_to_menu_prompt() -> None:
    Console.write_line( "--- Eingabe-Taste drücken um in das Menü zurückzukehren" )
    Console.await_key( Key( keyboard.Key.enter ), Key( keyboard.Key.esc) )


def confirmation( msg:str, col:int=None, line:int=None, absolute:bool=True ) -> bool:
    res = Console.get_input(msg, col, line, absolute) in ['Y', 'y']
    # maybe use or not, idk yet
    # if col or line:
    #     Console.write_line()
    return res

def digit_input( must_be_in:list[int]=None ) -> tuple[bool, int]:
    """
    get the digit the user pressed

    to cancel the loop press `esc`

    Args:
        must_be_in (`list`[`int`], optional): only return user inputted digit if it is one of the digits in must_be_in. Defaults to all digits (0,1,2,3,4,5,6,7,8,9).

    Returns:
        `tuple`[`bool`, `int`]: `[0]` is `True` if the user pressed a digit key, `[0]` is `False` if the user pressed the `esc` key; `[1]` is the integer digit the user pressed, defaults to -1 if `[0]` is `False`
    """
    if not must_be_in:
        must_be_in = [ i for i in range(10) ]
        
    while True:
        match Console.get_key():
            case Key( np=keyboard.Key.esc ):
                return False, -1
            
            case Key( np=None, an=ch ) if ch.isdigit() and int(ch) in must_be_in:
                return True, int(ch)
            
            case _:
                continue

def manage_interactables(
    fm:Manager,
    db_get: Callable[[list[object]], tuple[bool, list[list[object]]] ],
    db_set: Callable[[list[object]], None ],
    table_generator: Callable[[list[object], list[list[object]]], str],
    table_side_prompt: str,
    header_text: str,
    confirm_text: str,
    successful_text: str,
    unsuccessful_text: Optional[str] = None
    ):
    """
    handle user inputted data

    handles:
        - successfulness of user input
            - decline or accept input
        - if entry not in db
            - print table with header and confirmation
        - add/remove/override data to db

    Args:
        fm (`Manager`): Manager where the user made their input
        db_get (`Callable[[list[object]], tuple[bool, list[object]] ]`): retrieving data from the db:
            Args:
                data_from_the_fm_Results_object
            Returns:
                tuple[ data_exists_bool, list_of_stored_data_tuples_in_db ]
        db_set (`Callable[[list[object]], None ]`): set/remove/override data from the db:
            Args:
                data_from_the_fm_Results_object
        table_generator (`Callable[[list[object], list[list[object]]], str]`): tabulating function to prompt to user to verify the action of overriding/removing the data from the db:
            Args:
                tuple[ data_from_the_fm_Results_object, list_of_stored_data_tuples_in_db ]
            Returns:
                table_as_str
        table_side_prompt (`str`):           text pinned at the side of the table to indicate the associated action
        header (`str`):                      text printed before the table
        confirm (`str`):                     text to ask the user to confirm the action
        successful_set (`str`):              text to print after successful performing the action
        unsuccessful_text (`Optional[str]`): if `not None`, will print text to the Console and do not call `db_set`. If `None`, will always (unless entry exists in db and requires user confirmation) call `db_set`. Defaults to `None`.
    """
    
    # Layout:
    #    0 |  Plain[ Header ]                   
    #    1 |                                    
    #    2 |    |---------------------|         
    #  ... |    | ** Table Focuses ** |         
    #  X   |    |---------------------|         
    #  X+1 |                                    
    #  X+2 |  Plain[ Confirmation - Text ]      
    #  X+3 |  |--------------------------|      
    #  ... |  | ** Table Confirmation ** |      
    #  Y   |  |--------------------------|      
    #  Y+1 |                                    
    #  Y+2 |  Input[ Confirmation ]             
    #  Y+3 |                                    
    #  Y+4 |  Optional[ Plain[ Reading added ] ]
    #  Y+5 |                                    
    #  Y+7 |  Optional[ Plain[ Decline ] ]      
    #  Y+8 |  <<< Plain[ Back to menu ]         
    
    LINE_PTR = 0
    
    fm.append( Confirm_yes_no( "Bestätigen", "Zurück" ) )
    
    Console.show_cursor()
    fm_result = fm.join()
    Console.hide_cursor()
    
    # X
    LINE_PTR = fm.get_bbox()[1][1]
    if not fm_result.success:
        user_decline_prompt(0, LINE_PTR+2)
        return
    

    fm_data = fm_result.data
    
    exists, data = db_get( fm_data )
    
    if unsuccessful_text and not exists:
        Console.write_at( unsuccessful_text, 0, LINE_PTR+2 )
        user_decline_prompt(0, LINE_PTR+3)
        return
    
    if exists:
        tab = table_generator( fm_data, data )
        for i in range( len(data) ):
            tab = add_side_note_to_tabular( tab, table_side_prompt, -(2+i) )
        
        fm_2 = Manager(True, True).set_position_left_top( 0, LINE_PTR+2 )

        Console.show_cursor()
        result:Result = fm_2\
            .append( Plain_Text(header_text) )\
            .append( Plain_Text(tab) )\
            .append( Plain_Text(confirm_text) )\
            .append( Confirm_yes_no() )\
            .join()
        Console.hide_cursor()
        
        # Y
        LINE_PTR = fm_2.get_bbox()[1][1]
        
        if not result.success:
            user_decline_prompt(0, LINE_PTR+2)
            return
    
    db_set( fm_data )
    Console.write_at( successful_text, 0, LINE_PTR+3 )
    Console.set_cursor(0, LINE_PTR+4)

#------------#
# FORMATTING #
#------------#
def get_string_dimensions( s:str ) -> tuple[int, int]:
    # cspell:ignore nccc nddd
    """
    get the width and height (col, line) dimensions of the supplied string it would span on the terminal

    >>> get_string_dimensions( "aa\\nb\\nccc\\ndd" )
    (3, 4)

    Args:
        s (`str`): string to be analyzed for dimensions

    Returns:
        `tuple`[`int`, `int`]: dimensions ordered in (col, line)
    """
    lines = s.splitlines()
    return ( max_width_of_strings(lines)[1], len(lines) )

def max_width_of_strings( list_of_str:list[str] ) -> tuple[str, int]:
    """
    find the line and the associated width of the widest line

    Args:
        list_of_str (`list`[`str`]): lines of string

    Returns:
        `tuple`[`str`, `int`]:
        - [0] is the line/element with the widest width
        - [1] is the length of [0]; Will return (None, -1)
        - iff unable to `list_of_strings` is not of type `list[str]` or other errors occur during calculation
    """
    try:
        res = max( list_of_str, key=len )
        return res, len(res)
    finally:
        pass
    return None, -1

def format_decimal( value:float|None, digit_layout:tuple[int, int], alignment_format:str='>', format_size:int=None ) -> str:
    # to clamp the value to the specified digit_layout: abs_max = 10**digit_layout[0] - 10**(-digit_layout[1])
    # 
    # example:
    # >>> digit_layout = (2,3)
    # abs_max = 10**digit_layout[0] - 10**(-digit_layout[1]) = 100 - 0.001 = 99.999
    
    # sum(digit_layout)  + 1     + 1
    #       ^^^^          ^       ^^
    # number of digits,  '.', '-' or ' '
    if not value:
        return ' ' * sum(digit_layout)
    
    abs_max = 10**digit_layout[0] - 10**(-digit_layout[1])
    formatted_digits = ( "{: >%d.%df}" % ( sum(digit_layout) + 1 + 1, digit_layout[1] ) ).format( max( -abs_max, min( value, abs_max ) ) )
    
    if not format_size:
        return formatted_digits
    
    return ( "{:%s%ds}" % ( alignment_format, format_size ) ).format( formatted_digits )

def format_person_data( person:Person ) -> tuple[str, str, str]:
    return (
        person.name,
        person.move_in.strftime( DATE_STR_FORMAT ) if person.move_in else None,
        person.move_out.strftime( DATE_STR_FORMAT ) if person.move_out else None,
    )


#-----------#
# PDF STUFF #
#-----------#
def find_fitting_fontsize( len_of_str:int, hor_space_avail:int ) -> int: 
    # should be representative for all ranges of font sizes, under assumption of monospace font
    char_width_size_ratio = stringWidth( ' ', PDF_FONT_TABLE, 100 ) / 100
    
    width_ratio_required = len_of_str * char_width_size_ratio
    
    return hor_space_avail / width_ratio_required

def add_info_pdf_page( canv:canvas.Canvas ) -> None:
    pageNum = canv.getPageNumber()

    f, fs, lead = canv._fontname, canv._fontsize, canv._leading
    
    canv.setFont( PDF_FONT_TABLE, PDF_FONTSIZE_NOTES, PDF_FONTSIZE_NOTES )
    
    canv.drawString( canv._pagesize[0]-1*cm, PDF_FONTSIZE_NOTES+2*mm, str(pageNum) )
    canv.drawString( 1*cm, canv._pagesize[1]-2*mm, f"PDF created {datetime.utcnow().strftime('%x %X')}" )
    
    canv.setFont( f, fs, lead )

def draw_pdf_page( table_lines:str, can:canvas.Canvas, width:int, height:int, rx:int, ry:int, offset_ry:int, font:str, table_continue_str:str ) -> None:
    max_row_len = max_width_of_strings( table_lines.splitlines() )[1]
    
    RW, RH = width-2*rx, height-(ry+offset_ry)-rx
    
    FONT_SIZE = find_fitting_fontsize( max_row_len, RW )
    
    ROWS = floor( RH / FONT_SIZE )
    ENTRIES_PER_PAGE = floor( (ROWS-1-1) / 3 ) # (ROWS - LINE_UPPER_SEPARATOR - SPACE_BOTTOM) / LINES_PER_ENTRY
    
    textObj = can.beginText( rx, ry+offset_ry )
    textObj.setFont( font, FONT_SIZE, FONT_SIZE )
    
    lines_idx = 0
    for line in table_lines.splitlines():
        if lines_idx == 3 * ENTRIES_PER_PAGE:     # ENTRIES_PER_PAGE = 3 * REQUIRED_LINES_PER_PAGE
            lines_idx = 0
            
            RH = height-ry-rx 
            ROWS = floor( RH / FONT_SIZE )
            ENTRIES_PER_PAGE = floor( (ROWS-1-1) / 3 )
            
            textObj.moveCursor( ( RW - FONT_SIZE*len(table_continue_str) )//2, 0 )
            textObj.textOut( table_continue_str )
            
            can.drawText( textObj )
            
            # finalize this page and initiate new page
            add_info_pdf_page(can)
            can.showPage()
            
            
            textObj = can.beginText( rx, ry )
            textObj.setFont( PDF_FONT_TABLE, FONT_SIZE, FONT_SIZE )
            
        lines_idx+=1
        textObj.textLine(line)
        
    can.drawText( textObj )

    # finalize this page and initiate new page
    add_info_pdf_page(can)
    can.showPage()


#----------------------------------------------------------------------------------------------------------------------
# TABULATE - HELPER AND Console.write_line FUNCTIONS
#----------------------------------------------------------------------------------------------------------------------
def add_side_note_to_tabular( table:str, side_note:str, row:int ) -> str:
    lines = table.splitlines()
    lines[row] += side_note
    return NL.join( lines )

#--------------------#
# TABULATE - PERSONS #
#--------------------#
def get_all_names() -> list[str]:
    """
    fetches all individual names of persons in database

    Returns:
        `list[str]`: names of person in database
    """
    data = SESSION.get_person_all()
    
    return [ p.name for p in data ]

def get_tabular_names( names:list[str], tablefmt="grid" ) -> str:
    """
    generate simple `tabulate` table of names

    Args:
        names (`list[str]`): list of names to be tabulated
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "grid".

    Returns:
        `str`: string of table
    """
    return tabulate( [[n] for n in names], headers=["Personen in der Datenbank"], tablefmt=tablefmt, colalign=['center'] )

def get_tabular_person_simple( persons:list[ Person ], tablefmt="psql" ) -> str:
    """
    generate a simple `tabulate` Table of persons

    ---
    #### Table layout will be according to the following:
    
    Legend:
    - `Highlighted`: highlighted literals define one chunk of e.g. a str or other information
    - `$xyz$`: highlighted and encapsulated by `$` literals define input-variables to be inserted
    
    Header:
    | name | date move in | date move out |
    |-----:|:------------:|:-------------:|
    | `Name` | `moving in date` | `moving out date` |
    
    Body ( Data ):
    | name | date move in | date move out |
    |-----:|:------------:|:-------------:|
    | `$person_x.name$` | `$person_x.move_in$` | `$person_x.move_out$` |
    
    ---
    Args:
        persons (`list[ Person ]`): list of persons to be tabulated
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "psql".

    Returns:
        `str`: string of table
    """
    persons = [ format_person_data(p) for p in persons ]
    return tabulate(
        persons, 
        headers=TABLE_HEADER_PERSONS_SIMPLE, 
        tablefmt=tablefmt, 
        colalign=('right', 'center', 'center'), 
        maxcolwidths=[15, None, None, None]
    )

def get_tabular_person_detail( persons:list[ Person ], tablefmt="grid" ) -> str:
    """
    generate a detailed `tabulate` Table of persons

    ---
    #### Table layout will be according to the following:
    
    Legend:
    - `Highlighted`: highlighted literals define one chunk of e.g. a str or other information
    - `$xyz$`: highlighted and encapsulated by `$` literals define input-variables to be inserted
    - ------- : Horizontal lines in a cell indicates that either the above or below layout can be used for formatting
        
        (This is dependent on internal conditions choosing one version for formatting)
    
    #### Header:
    | name | date move in | date move out | inhabited months | included in invoices |
    |:----:|:------------:|:-------------:|:----------------:|:--------------------:|
    | `Name` | `moving in date` | `moving out date` | `inhabited months` | `included in` |
    |        |                  |                   |                    |   `invoices`  |
    
    #### Body ( Data ):
    | name | date move in | date move out | inhabited months | included in invoices |
    |:----:|:------------:|:-------------:|:----------------:|:--------------------:|
    | `$name$` |    `$move_in$`   |   `$move_out$`   |                `$PLACE_HOLDER$`                |        `$PLACE_HOLDER$`        |
    |          | ---------------- | ---------------- | ---------------------------------------------  | ------------------------------ |
    |          | `$PLACE_HOLDER$` | `$PLACE_HOLDER$` | `$month_less_half_prefix$` `$months_in_span$`  | `$invoices_vertically_listed$` |
    |          | `$PLACE_HOLDER$` | `( $move_out$ )` | `$move_in.month_yr$` `-` `$move_out.month_yr$` | ------------------------------ |
    |          |                  |                  | ---------------------------------------------- |      `( $move_in.year$ )`      |
    |          |                  |                  |               `not yet moved in`               |                                |
    
    ---
    Args:
        persons (`list[ Person ]`): list of persons to be tabulated
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "psql".

    Returns:
        `str`: string of table
    """
    PLACE_HOLDER = '*'
    
    table_data = []
    
    for p in persons:
        move_in_str  = p.move_in.strftime(  DATE_STR_FORMAT ) if p.move_in  else PLACE_HOLDER
        move_out_str = p.move_out.strftime( DATE_STR_FORMAT ) if p.move_out else PLACE_HOLDER
        
        effective_months_str = PLACE_HOLDER
        invoices = PLACE_HOLDER
        
        if p.move_in:
            artifical_move_out = p.move_out if p.move_out else date.today()
            
            years_str_list = [ str(year) for year in range(p.move_in.year, artifical_move_out.year+1) ]
            
            if artifical_move_out >= p.move_in:
                delta_months, delta_fraction = divmod( ( artifical_move_out - p.move_in ).days, 30 )
                
                delta_str = "%s%d" % ( '<' if delta_fraction < 15 else '', delta_months+1 )
                
                effective_months_str = ''.join( [delta_str, NL, p.move_in.strftime("%b%y"), ' - ', artifical_move_out.strftime("%b%y") ] )
            else:
                effective_months_str = "noch nicht\neingezogen\n"
                years_str_list = [ f"( {p.move_in.year} )" ]
            
            invoices = NL.join( years_str_list )
            
            # hint today's date in the moving_out slot in the table if no moving_out date is present
            if not p.move_out:
                move_out_str = NL.join( [ PLACE_HOLDER, f"( { date.today().strftime( DATE_STR_FORMAT ) } )" ] )
        
        table_data.append( [
            p.name,
            move_in_str,
            move_out_str,
            effective_months_str,
            invoices
        ])
        
    if not persons: # Database has no entries
        table_data = [["no data"]*len(TABLE_HEADER_PERSONS_DETAIL)]
    
    return tabulate(
        table_data,
        headers=TABLE_HEADER_PERSONS_DETAIL,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('right', 'center', 'center', 'center', 'center'),
        maxcolwidths=[15, None, None, None, None]
    )

#---------------------#
# TABULATE - READINGS #
#---------------------#
@dataclass
class Measurement:
    absolute : float | None
    mean     : float | None
    deviation: float | None
    
    minimum: float | Date | None = None
    maximum: float | Date | None = None

@dataclass
class Organized_point:
    amount_points: int
    
    days_stats: Measurement
    values_stats_per_day: list[ Measurement ]

@dataclass
class Organized_month:
    month: int
    points: Organized_point

@dataclass
class Organized_year:
    year: int
    points: Organized_point

@dataclass
class Grouped_year_organized_month:
    year: int
    months: list[ Organized_month ]

def get_all_reading_dates() -> list[str]:
    """
     fetches all individual reading dates in database

    Returns:
        `list[str]`: dates of person in database
    """
    data = SESSION.get_reading_all()
    
    return [ r.date for r in data ]

def get_tabular_reading_simple( readings:list[ Reading ], tablefmt="psql" ) -> str:
    """
    generate simple `tabulate` table of readings

    Args:
        readings (`list[Reading]`): list of readings to be tabulated
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "grid".

    Returns:
        `str`: string of table
    """
    readings = [
        [
            r.date.strftime( DATE_STR_FORMAT ),
            *[
                format_decimal( r.attributes[k], LIST_DIGIT_OBJ_LAYOUTS[k] ) for k in range(COUNT_READING_ATTRIBUTES)
            ]
        ]
        for r in readings
    ]
    
    return tabulate(
        readings,
        headers=TABLE_HEADER_READINGS_SIMPLE,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('left', *['decimal']*COUNT_READING_ATTRIBUTES)
    )


def generate_printout_readings_all( readings:list[ Reading ], use_years_for_stats_section:bool=True ) -> str:
    """
    generate string of readings to be displayed

    consists of two parts:
    1. Table of each individual readings + statistical information
    2. Table of readings grouped and summarized by [optional](year and) month with additional statistical information

    Args:
        readings (`list[ Reading ]`): raw data directly from database
        use_years_for_stats_section (`bool`, optional): if `True` groups readings in `Table 2` by year and months, `False` groups only by months. Defaults to `True`.

    Returns:
        str: Tables of readings formatted to be printed on screen or pdf
    """
    table_raw = generate_printout_readings_detail( readings )
    table_stats = generate_printout_readings_statistics( readings, use_years_for_stats_section )
    
    return ''.join([table_raw, NL, NL, table_stats, NL])

def generate_printout_readings_detail( readings:list[ Reading ], tablefmt="grid" ) -> str:
    """
    generate string of table for detailed readings output

    ---
    #### Table of each individual readings + statistical information. 
    #### Table layout will be according to the following:
    
    Legend:
    - `Highlighted`: highlighted literals define one chunk of e.g. a str or other information
    - `$xyz$`: highlighted and encapsulated by `$` literals define input-variables to be inserted
    
    Header:
    | Date section | value_0 | value_1 | ... |
    |:------------ |:-------:|:-------:|-----|
    | `Date`         |       `$name_value_0$`       |       `$name_value_1$`       | ... |
    | `Delta`        | `delta/day` `absolute delta` | `delta/day` `absolute delta` | ... |
    
    Body ( Data ):
    | Date section | value_0 | value_1 | ... |
    |:------------ |:-------:|:-------:|-----|
    | `$Date_reading_x$`          |                `$value_0$`               |                `$value_1$`               | ... |
    | `Days:` `$Delta_reading_x$` | `$delta_per_day_0$` `$absolute_delta_0$` | `$delta_per_day_1$` `$absolute_delta_1$` | ... |
    

    ---
    Args:
        readings (`list[ Reading ]`): raw data directly from database
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "grid".

    Returns:
        str: Table of detailed readings formatted to be printed on screen or pdf
    """
    table_data = []
    
    tabulating = lambda tab_data: tabulate( 
                                           tab_data,
                                           headers=TABLE_HEADER_READINGS_DETAIL,
                                           tablefmt=tablefmt,
                                           disable_numparse=True,
                                           colalign=('left', *['center']*COUNT_READING_ATTRIBUTES)
                                           )
    
    if not readings: # Database has no entries
        return tabulating( [["no data"]*len(TABLE_HEADER_READINGS_DETAIL)] )
    
    
    # append first entry since the following loop start iterating at the second entry
    table_data.append( [
        readings[0].date.strftime( DATE_STR_FORMAT ) +NL+ f"    Tage:---",
        *[
            format_decimal( readings[0].attributes[k], LIST_DIGIT_OBJ_LAYOUTS[k] ) +NL+\
            format_decimal( None, DIGIT_LAYOUT_DELTA ) +" "+ format_decimal( None, LIST_DIGIT_OBJ_LAYOUTS[k] )
            for k in range(COUNT_READING_ATTRIBUTES)
        ]
    ] )
    
    # "can't" use enumerate(...) since indexing should start at 1 and enumerate can't work with that
    # it would be feasible to use enumerate but for now this seems simpler
    for i in range(1, len(readings)):
        r = readings[i]
        
        delta = [None] * COUNT_READING_ATTRIBUTES
        
        table_data.append( [ r.date.strftime( DATE_STR_FORMAT ) +NL+ f"    Tage:{(r.date - readings[i-1].date).days:>3d}" ] )
        
        for k in range( COUNT_DIGIT_OBJS ):
            if r.attributes[k] is None:
                table_data[-1].append(
                    format_decimal( None, LIST_DIGIT_OBJ_LAYOUTS[k] ) +NL+\
                    format_decimal( None, DIGIT_LAYOUT_DELTA ) +" "+ format_decimal( None, LIST_DIGIT_OBJ_LAYOUTS[k] )
                )
                continue
            
            delta[k]  = None
            earlier_v = None
            n = (i-1)+1
            
            # search for an earlier value to calculate a delta value
            while (n:=n-1) >= 0:
                earlier_v = readings[n].attributes[k]
                if earlier_v is not None:
                    delta[k] = r.attributes[k] - earlier_v
                    break
            
            ddays = ( r.date - readings[n].date ).days
            
            table_data[-1].append(
                format_decimal( r.attributes[k], LIST_DIGIT_OBJ_LAYOUTS[k] ) +NL+\
                format_decimal( delta[k]/ddays if delta[k] else None, DIGIT_LAYOUT_DELTA ) +" "+ format_decimal( delta[k], LIST_DIGIT_OBJ_LAYOUTS[k] )
            )
    
    return tabulating( table_data )

def generate_printout_readings_statistics( readings:list[ Reading ], use_years_for_stats_section:bool=True, tablefmt="grid" ) -> str:
    """
    generate string of table of readings grouped and summarized by [optional](years and) months

    --- 
    #### Table layout will be according to the layout found in `readings_tabulate_data(...)`
    
    ---
    Args:
        readings (`list[ Reading ]`): raw data directly from database
        use_years_for_stats_section (`bool`, optional): if `True` groups readings in `Table 2` by year and months, `False` groups only by months. Defaults to `True`.
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "grid".

    Returns:
        str: Table of readings grouped and summarized by [optional](year and) month with additional statistical information to be printed on screen or pdf
    """
    years = readings_organize_data_monthly( readings )
    
    if use_years_for_stats_section:
        stats = readings_organize_data_yearly( readings )
    else:
        stats = readings_organize_data_span( readings )
    
    return readings_tabulate_data( years, stats, use_years_for_stats_section, tablefmt )


def readings_organize_data_monthly( readings:list[ Reading ] ) -> list[ Grouped_year_organized_month ]:
    """
    generate list of statistically analyzed data

    - Data is grouped by year and by month.
    - Only the month subgroups are statistically analyzed and summarized.

    Args:
        readings `(list[ Reading ]`): raw data directly from database

    Returns:
        `list[ Grouped_year_organized_month ]`: list of yearly grouped and monthly analyzed data
    """
    
    # sort all data entries by date (they should already be ordered correctly, but you never know)
    readings = sorted( readings, key=lambda r: r.date )

    years = [ Grouped_year_organized_month( yr, [] ) for yr in sorted( set( map(lambda r: r.date.year, readings) ) ) ]
    
    for year in years:
        filtered_data = list( filter( lambda r: r.date.year == year.year, readings ) )
        
        month_ids = list( map( lambda r: r.date.month, filtered_data ) )
        
        months = {
            m_id : 
            list( filter(lambda r: r.date.month == m_id, filtered_data) ) for m_id in month_ids
        }
        
        months = dict( filter( lambda kv: len(kv[1]) > 1, months.items() ) )
        
        year.months = [
            Organized_month( 
                month_id,
                readings_calculate_statistics(
                    points, 
                    date(year.year, month_id, 1), 
                    date(year.year, month_id+1, 1) if month_id < 12 else date(year.year+1, 1, 1) 
                )
            )
            for month_id, points in months.items()
        ]
    
    return list( filter( lambda y: y.months, years ) )

def readings_organize_data_yearly( readings:list[ Reading ] ) -> list[ Organized_year ]:
    """
    generate list of statistically analyzed data

    - Data is grouped by year.
    - Data is, per annual group, statistically analyzed and summarized.

    Args:
        readings `(list[ Reading ]`): raw data directly from database

    Returns:
        `list[ Organized_year ]`: list of yearly grouped and monthly analyzed data
    """
    year_ids = sorted( set( map( lambda r: r.date.year, readings ) ) )
    
    out_list = []
    for year_id in year_ids:
        points = list( filter( lambda r: r.date.year == year_id, readings ) )

        out_list.append(
            Organized_year(
                year_id,
                readings_calculate_statistics( points, date(year_id, 1, 1), date(year_id+1, 1, 1) )
            )
        )
    
    return out_list

def readings_organize_data_span( readings:list[ Reading ] ) -> Organized_point:
    """
    generate list of statistically analyzed data

    - Data is grouped into one group.
    - Data is statistically analyzed and summarized.

    Args:
        readings `(list[ Reading ]`): raw data directly from database

    Returns:
        `list[ Organized_year ]`: list of yearly grouped and monthly analyzed data
    """
    # sort all data entries by date (they should already be ordered correctly, but you never know)
    readings = sorted( readings, key=lambda r: r.date )
    
    return readings_calculate_statistics( readings )


def readings_calculate_statistics( points:list[ Reading ], extrapolation_date_lower_bound:date=None, extrapolation_date_upper_bound:date=None ) -> Organized_point:
    """
    statistically analyze a set of reading points

    calculates the following for the total days and for each reading-attribute:
    - sum
    - mean
    - standard deviation
    - minimum
    - maximum
    
    IF `extrapolation_date_lower_bound` OR `extrapolation_date_upper_bound` are not `None`:
        The calculated data is extra-/interpolated to the given time span.
        Expect noisy values for insufficiently small time spans or insufficient amounts of data points.

    Args:
        points (`list[ Reading ]`): raw data directly from database
        extrapolation_date_lower_bound (`date`, optional): lower bound for extra-/interpolation. Defaults to None.
        extrapolation_date_upper_bound (`date`, optional): upper bound for extra-/interpolation. Defaults to None.

    Returns:
        `Organized_points`: statistically analyzed data points
    """
    points = sorted( points, key=lambda r: r.date )
    
    amount_points = len(points)
    
    if amount_points < 2:
        return Organized_point( 0, Measurement(0, 0, 0), [Measurement(0, 0, 0)]*COUNT_READING_ATTRIBUTES )
    
    extrapolation_date_lower_bound = extrapolation_date_lower_bound if extrapolation_date_lower_bound else points[0].date
    extrapolation_date_upper_bound = extrapolation_date_upper_bound if extrapolation_date_upper_bound else points[-1].date
    
    
    delta_d, total_d, sum_stats_d, sum_stats_sqr_d = 0.0, 0.0, 0.0, 0.0
    mean_d, deviation_d = 0.0, None
    
    delta        :list[float]      = [0.0] * COUNT_READING_ATTRIBUTES
    total        :list[float|None] = [0.0] * COUNT_READING_ATTRIBUTES
    sum_stats    :list[float|None] = [0.0] * COUNT_READING_ATTRIBUTES
    sum_stats_sqr:list[float|None] = [0.0] * COUNT_READING_ATTRIBUTES
    gap          :list[int]        = [0]   * COUNT_READING_ATTRIBUTES
    
    included_points :list[int]  = [0]    * COUNT_READING_ATTRIBUTES
    first_point_date:list[date] = [None] * COUNT_READING_ATTRIBUTES
    last_point_date :list[date] = [None] * COUNT_READING_ATTRIBUTES
    
    mean     :list[float|None] = [None] * COUNT_READING_ATTRIBUTES
    deviation:list[float|None] = [None] * COUNT_READING_ATTRIBUTES
    
    # like extrapolation_date_lower_bound, extrapolation_date_upper_bound
    # set these lower and upper bound for each value individually
    for k in range(COUNT_READING_ATTRIBUTES):
        for r in points:
            if not r.attributes[k]:
                continue
            
            if not first_point_date[k]:
                first_point_date[k] = r.date
            
            last_point_date[k] = r.date
    
    # different edge cases may occur while analyzing the data. All possible edge cases are listed below as examples and are accounted for in the code below
    # day |    case 1     |     case 2     |      case 3     |      case 4     |      case 5     |      case 6     |      case 7     |
    #     | reader reset  |  missing point |  missing point  |  missing point  |  missing point  |  missing point  |  missing point  |
    #     |               |                | + reader reset  | + missing point | + reader reset  |                 | + missing point |
    # ----|---------------|----------------|-----------------|-----------------|-----------------|-----------------|-----------------|
    #  0  |    100.0      |     100.0      |     100.0       |      None       |     100.0       |      None       |      None       |
    #  1  |    200.0      |     200.0      |      None       |      None       |      None       |     200.0       |      None       |
    #  2  |      0.0      |      None      |       0.0       |     100.0       |       0.0       |       ---       |       ---       |
    #  3  |    100.0      |     400.0      |     100.0       |     200.0       |       ---       |       ---       |       ---       |
    
    
    for i in range(1, len(points)):
        r = points[i]
        
        delta_d          = (r.date - points[i-1].date).days
        total_d         += delta_d
        sum_stats_d     += delta_d
        sum_stats_sqr_d += delta_d ** 2
        
        # iterate over all reading value objs
        for k in range( COUNT_DIGIT_OBJS ):
            # implicitly catches case 7
            if r.attributes[k] is None:
                continue
            
            earlier_v = None
            n = (i-1)+1

            # search for an earlier value to calculate a delta value
            # catches case 2, 3, 5
            while (n:=n-1) >= 0:
                earlier_v = points[n].attributes[k]
                if earlier_v:
                    delta[k] = r.attributes[k] - earlier_v
                    break
            
            # we are not able to calculate a data value if all previous values are None
            # catches case 4, 6
            if earlier_v is None:
                continue
            
            ddays = ( r.date - points[n].date ).days
            
            # to correct for large negative values, e.g. because a meter got changed and was reseted to 0 or other faulty data
            # in this context we usually expect positive changes, i.e. strictly monotonic increasing data points
            # therefor we reject negative deltas and do not include that time span (and values)
            # case 1
            if delta[k] < 0:
                gap[k] += ddays
                continue
            
            included_points[k] += 1
            
            total[k]         += delta[k]
            sum_stats[k]     += delta[k] / ddays
            sum_stats_sqr[k] += (delta[k] / ddays) ** 2
    
    # ------------------------------------------------------------------------------------------------------------------------------------------
    # mean and deviation are measured in respect to the change of value per day
    # since we measure a "derivative" we "loose" one data point and thus need to reduce our number of points by one ( similar to z-Transform )
    # ------------------------------------------------------------------------------------------------------------------------------------------
    mean_d = sum_stats_d / ( amount_points - 1 )
    if amount_points > 2:
        deviation_d = sqrt( ( sum_stats_sqr_d - ( amount_points - 1 ) * ( mean_d**2 ) ) / ( amount_points - 2 ) )
    
    for k in range( COUNT_READING_ATTRIBUTES ):
        if included_points[k] <= 0:
            total[k] = None
            continue
        
        mean[k] = sum_stats[k] / included_points[k]
        
        if included_points[k] > 1:
            deviation[k] = sqrt( ( sum_stats_sqr[k] - included_points[k] * ( mean[k]**2 ) ) / ( included_points[k] - 1 ) )
        
        extra_days = ( first_point_date[k] - extrapolation_date_lower_bound ).days + ( extrapolation_date_upper_bound - last_point_date[k] ).days
        
        # adjust each value for gaps (negative delta) and days to be extrapolated in the data points
        total[k] += ( gap[k] + extra_days ) * mean[k]
    
    
    return Organized_point(
        amount_points,
        Measurement( total_d, mean_d, deviation_d, extrapolation_date_lower_bound, extrapolation_date_upper_bound ),
        [ 
            Measurement(
                total[k],
                mean[k],
                deviation[k],
                min( filter( lambda r: r.attributes[k] is not None, points ), key=lambda r: r.attributes[k] ),
                max( filter( lambda r: r.attributes[k] is not None, points ), key=lambda r: r.attributes[k] )
            )
            for k in range( COUNT_READING_ATTRIBUTES )
        ]
    )

def readings_tabulate_data(
    years: list[ Grouped_year_organized_month ],
    stats: list[ Organized_year ] | Organized_point,
    use_years_for_stats_section:bool=True,
    tablefmt="grid" ) -> str:
    """
    generate string of table of readings grouped and summarized by [optional](years and) months

    --- 
    #### Table layout will be according to the following:
    
    Legend:
    - `Highlighted`: highlighted literals define one chunk of e.g. a str or other information
    - `$xyz$`: highlighted and encapsulated by `$` literals define input-variables to be inserted
    
    Layout:
    - Header:
    | Date specifics | value_0 | value_1 | ... |
    |:-------------- |:-------:|:-------:|-----|
    | `Year : Month`                               |       `$name_value_0$`       |       `$name_value_1$ `      | ... |
    | `Time Span` `Number of Readings`             |  `Extrapolated Consumption`  |  `Extrapolated Consumption`  | ... |
    | `Readings`                                   |   `per Day`     `per Week`   |   `per Day`     `per Week`   | ... |
    | `Days between Readings` `standard deviation` | `standard deviation per Day` | `standard deviation per Day` | ... |
     
    - Body ( Data ):
    | Date specifics | value_0 | value_1 | ... |
    |:-------------- |:-------:|:-------:|-----|
    | `$Year_x$` : `$month_y$`                  |          `$extrapolated_consumption_0$`          |          `$extrapolated_consumption_1$`          | ... |
    | `$time_span_z$` `$number_readings_z$`     | `$consumption_per_day_0$` `$consumption_week_0$` | `$consumption_per_day_1$` `$consumption_week_1$` | ... |
    | `$days_between_readings_z$` `$std_dev_z$` |             `$std_dev_consumption_0$`            |             `$std_dev_consumption_1$`            | ... |
    | `- - - - - - - - - - - - - - - - - - -`   |      ` - - - - - - - - - - - - - - - - - `       |      ` - - - - - - - - - - - - - - - - - `       | ... |
    
    - IF `use_years_for_stats_section` == `True` => Body has also the following entries:
    | Date specifics | value_0 | value_1 | ... |
    |:-------------- |:-------:|:-------:|-----|
    | `$Year_x$` : `Annual Values`              |          `$extrapolated_consumption_0$`          |          `$extrapolated_consumption_1$`          | ... |
    | `$time_span_x$` `$number_readings_x$`     | `$consumption_per_day_0$` `$consumption_week_0$` | `$consumption_per_day_1$` `$consumption_week_1$` | ... |
    | `$days_between_readings_x$` `$std_dev_x$` |             `$std_dev_consumption_0$`            |             `$std_dev_consumption_1$`            | ... |

    ---
    Args:
        months (`list[ Grouped_year_organized_month ]`): monthly grouped and statistically analyzed
        stats  (`list[ Organized_year ] | Organized_points`): if `use_years_for_stats_section`==`True` then yearly grouped and statistically analyzed else grouped and statistically analyzed
        use_years_for_stats_section (`bool`, optional): if `True` groups readings in `Table 2` by year and months, `False` groups only by months. Defaults to `True`.
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "grid".

    Returns:
        str: Table of readings grouped and summarized by [optional](year and) month with additional statistical information to be printed on screen or pdf
    """
        
    # cspell:ignore Eintr Abls
    # table calculates extrapolated consumptions per month, per Day per Month and per Week per month
    # +--------------------------+--------------------------+--------------------------+--------------------------+
    # | Jahr : Monat             |          Strom           |           Gas            |          Wasser          |
    # | Zeitspanne   Anz. Eintr. | Extrapolierter Verbrauch | Extrapolierter Verbrauch | Extrapolierter Verbrauch |
    # | Ablesungen               |   pro Tag    pro Woche   |   pro Tag    pro Woche   |   pro Tag    pro Woche   |
    # | Tage zw. Abls.|std. Abw. | Standardabweichung p.Tag | Standardabweichung p.Tag | Standardabweichung p.Tag | 
    # +==========================+==========================+==========================+==========================+
    
    # get the maximum width of each columns header
    column_widths = [ max( map( len, lines.splitlines() ) ) for lines in TABLE_HEADER_READINGS_STATS ]
    
    table_data = []
    
    for year_group in years:
        for month in year_group.months:
            table_data.append( readings_format_month( year_group.year, month, column_widths[0] ) )
    
    # add spacing for years
    table_data.append( [ "- "*(column_widths[i]//2) for i in range(len(TABLE_HEADER_READINGS_STATS)) ] )
    
    if use_years_for_stats_section and isinstance( stats, list ):
        for year in stats:
            table_data.append( readings_format_year( year, column_widths[0] ) )
    elif isinstance( stats, Organized_point ):
        table_data.append( readings_format_span( stats, column_widths[0] ) )
    
    
    if not years: # Database has no entries
        table_data = [["no data"]*len(TABLE_HEADER_READINGS_STATS)]
    
    
    return tabulate(
        table_data,
        headers=TABLE_HEADER_READINGS_STATS,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('left', 'center', 'center', 'center')
    )


def readings_format_month( year:int, month_data:Organized_month, date_column_width:int ) -> list[str]:
    """
    format a reading to be appended to a `tabulate` Table of readings statistic

    This function formats a given month statistic for a given year

    Args:
        year (`int`): year to be displayed
        month_data (`Organized_month`): statistically analyzed data
        date_column_width (`int`): width of date i.e. 1st column in (printable) characters

    Returns:
        `list[str]`: `tabulate` formatted list of strings
    """
    row1 = date(year, month_data.month, 1).strftime( "%Y : %B" )
    
    return [
        row1 + NL + 
        readings_format_ddays_stats(
            month_data.points.amount_points,
            month_data.points.days_stats,
            date_column_width
        ) 
    ] + readings_format_values( month_data.points.values_stats_per_day )

def readings_format_year( year:Organized_year, date_column_width:int ) -> list[str]:
    """
    format a reading to be appended to a `tabulate` Table of readings statistic

    This function formats a given year statistic

    Args:
        year (`Organized_year`): statistically analyzed data
        date_column_width (`int`): width of date i.e. 1st column in (printable) characters

    Returns:
        `list[str]`: `tabulate` formatted list of strings
    """
    row1 = ( "%d : {:>%ds}" % (year.year, date_column_width - 4 - 3) ).format('Jahreswerte')
    
    return [
        row1 + NL + 
        readings_format_ddays_stats(
            year.points.amount_points,
            year.points.days_stats,
            date_column_width
        ) 
    ] + readings_format_values( year.points.values_stats_per_day )

def readings_format_span( point:Organized_point, date_column_width:int ) -> list[str]:
    """
    format a reading to be appended to a `tabulate` Table of readings statistic

    This function formats a given analyzed point (usually statistics of an user specified time span )

    Args:
        point (`Organized_point`): statistically analyzed data
        date_column_width (`int`): width of date i.e. 1st column in (printable) characters

    Returns:
        `list[str]`: `tabulate` formatted list of strings
    """
    size_of_strftime = 4 + 3 + 3
    
    row1 =  (" {:<%ds}{:>%ds}" % (size_of_strftime, date_column_width-size_of_strftime ))\
            .format(
                point.days_stats.minimum.strftime(r"%Y : %b") if point.days_stats.minimum else 'None',
                point.days_stats.maximum.strftime(r"%Y : %b") if point.days_stats.maximum else 'None'
            )
    
    return [
        row1 + NL + 
        readings_format_ddays_stats(
            point.amount_points,
            point.days_stats,
            date_column_width
        ) 
    ] + readings_format_values( point.values_stats_per_day )


def readings_format_ddays_stats( amount_points:int, days_measurement:Measurement, date_column_width:int ) -> str:
    """
    format the date column for the reading-statistics `tabulate` Table

    helper function - usually only used by:
    - `readings_format_month`
    - `readings_format_year`
    - `readings_format_span`
    
    ---
    Layout of the formatted output string:
    
    | line number | contents of formatted string |
    | :---------: | :--------------------------: |
    | 1 | `$time_span_x$` `$number_readings_x$`     |
    | 2 | `$days_between_readings_x$` `$std_dev_x$` |

    Args:
        amount_points (`int`): count of readings analyzed for this Table entry
        days_measurement (`Measurement`): statistical data of the analyzed reading days
        date_column_width (`int`): width of date i.e. 1st column in (printable) characters

    Returns:
        `str`: data-column formatted string
    """
    # column 1, row 2
    timeSpan_countEntries = f" {days_measurement.absolute:>3.0f} Tage " + ("{:>%dd}" % (date_column_width - 10)).format(amount_points)

    # column 1, row 3
    readings_stats = ( " {:s}{:>%ds}" % (date_column_width - 1 - sum(DIGIT_LAYOUT_DELTA) - 2) ).format(
        format_decimal( days_measurement.mean, DIGIT_LAYOUT_DELTA ),
        format_decimal( days_measurement.deviation, DIGIT_LAYOUT_DELTA )
    )
    
    return timeSpan_countEntries + NL + readings_stats

def readings_format_values( reading_attributes:list[Measurement] ) -> list[str]:
    """
    format all reading-attribute columns for the reading-statistics `tabulate` Table

    helper function - usually only used by:
    - `readings_format_month`
    - `readings_format_year`
    - `readings_format_span`
    
    ---
    Layout for each formatted string of the returned list:
    
    | line number | contents of formatted string |
    | :---------: | :--------------------------: |
    | 1 |          `$extrapolated_consumption_0$`          |
    | 2 | `$consumption_per_day_0$` `$consumption_week_0$` |
    | 3 |             `$std_dev_consumption_0$`            |

    Args:
        reading_attributes (`list[Measurement]`): list of statistically analyzed reading-attributes

    Returns:
        `list[str]`: list of reading-attribute-column formatted strings
    """
    return [ 
        "{:s}\n{:s}     {:s}\n{:s}".format(
            # line: 1
            format_decimal( reading_attributes[k].absolute, LIST_DIGIT_OBJ_LAYOUTS[k] ),
            
            # line: 2
            format_decimal( reading_attributes[k].mean, DIGIT_LAYOUT_DELTA ),
            format_decimal( 7*reading_attributes[k].mean if reading_attributes[k].mean else None, DIGIT_LAYOUT_DELTA ),
            
            # line: 3
            format_decimal( reading_attributes[k].deviation, DIGIT_LAYOUT_DELTA )
        )
        for k in range(COUNT_READING_ATTRIBUTES)
    ]

#----------------------------------------------------------------------------------------------------------------------
# MAIN LOOP AND STARTING POINT
#----------------------------------------------------------------------------------------------------------------------
MENU_OPTIONS = [
    visualize_readings,
    visualize_persons,
    manipulate_readings,
    manipulate_persons,
    delete_reading,
    delete_person,
    do_invoice,
    do_analyze,
    export_to_pdf,
]

def loop():
    flush_menu()
    
    is_digit, option = digit_input()
    
    if not is_digit:
        raise KeyboardInterrupt()
    
    if not ( 0 <= option-1 < len(MENU_OPTIONS) ):
        return
    
    Console.clear()
    
    MENU_OPTIONS[option-1]()
    
    user_to_menu_prompt()

def main() -> None:
    Console.setup( APP_NAME )
    Console.clear()
    
    try:
        while True:
            Console.hide_cursor()
            loop()
    except KeyboardInterrupt as e:
        Console.clear()
        Console.write_line( TITLE, NL, " Erfolgreich geschlossen ", NL )
    finally:
        Console.show_cursor()
        Console.stop()


if __name__ == '__main__':
    main()



###############################################################################################################################################################
#! DEPRECATED CODE ONLY FOR WIN32 MANIPULATION
#! REMOVE WHEN NO LONGER NEEDED

# !!! will freeze when executing with VSCode, requires external terminal window
# cspell:ignore hicon LOADFROMFILE DEFAULTSIZE SETICON evals screenbuffer winerror hwnd DEFAULTTONEAREST
# def setup_window() -> None:
#     """Set the window title, wait for it to apply, then adjust the icon."""
#     global CONSOLE_HWND, SCREEN_BUFFER
#     win32console.SetConsoleTitle( APP_NAME )
    
#     CONSOLE_HWND = 0
#     while (not CONSOLE_HWND):
#         CONSOLE_HWND = win32gui.FindWindow(None, APP_NAME)
#         sleep(0.025) # To not flood it too much...
    
#     # setting icon
#     hicon = win32gui.LoadImage(None, PATH_ICON.as_posix(), win32con.IMAGE_ICON, 0, 0, win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE)
    
#     win32gui.SendMessage(CONSOLE_HWND, win32con.WM_SETICON, win32con.ICON_SMALL, hicon)
#     win32gui.SendMessage(CONSOLE_HWND, win32con.WM_SETICON, win32con.ICON_BIG, hicon)
    
#     SCREEN_BUFFER = win32console.GetStdHandle( win32console.STD_OUTPUT_HANDLE )

# def set_clean_window_size( size:tuple[int, int], minSize:tuple[int, int] = (-1, -1), forced:bool=False ) -> None:
#     """
#     Set the size of the terminal if SIZE_DO_SET flag is set or forced is true. None as coordinate evals to same value as current coordinates size.
    
#     ! Be aware that after resizing the output buffer got emptied !
#     """
    
#     if not (forced or SIZE_DO_SET):
#         return
    
#     maxSize = getMaxConsoleSize()
    
    
#     if size[0] == SIZE_AUTO:
#         pass
    
#     if size[1] == SIZE_AUTO:
#         pass
    
    
#     # clamp values: max(0, minSize) < size < maxSize 
#     cols  = min( max( 0, minSize[0] ), max(size[0], maxSize[0]) )
#     lines = min( max( 0, minSize[1] ), max(size[1], maxSize[1]) )
    
#     os.system(f'mode con: cols={ cols } lines={ lines }') # refine with win32 modules
    
#     # readjust screenbuffer so none of the Console.write_line are getting left out
#     try:
#         SCREEN_BUFFER.SetConsoleScreenBufferSize( win32console.PyCOORDType( cols, SIZE_SCREEN_BUFFER ) )
#     except win32console.error as e:
#         # we expect the error (87, 'SetConsoleScreenBufferSize', ...)
#         # reraise the error if this was not the expected error
#         if e.winerror!= 87: 
#             raise e
    

# def getConsoleSize() -> tuple[int, int]:
#     """
#     Returns:
#         (width, height): width and height of the console if unsuccessful defaults to (-1, -1)
#     """
#     info: dict = SCREEN_BUFFER.GetConsoleScreenBufferInfo()
#     size: win32console.PyCOORDType = info.get( 'Size', win32console.PyCOORDType(-1, -1) )
#     return ( size.X, size.Y )

# def getWindowRect() -> tuple[int, int, int, int]:
#     """
#     Returns:
#         (left, top, right, bottom): left, top, right, bottom coordinates of the console window if unsuccessful defaults to (-1, -1, -1, -1)
#     """
#     return win32gui.GetWindowRect( CONSOLE_HWND )

# def getMaxWindowSize() -> tuple[int, int]:
#     """
#     calculates maximum window size in screen coordinate (Pixels) based on the current left-top position of the console window and the available screen space the window is currently limited by
    
#     Returns:
#         (width_px, height_px): width and height in pixels of the maximum console window size if unsuccessful defaults to (-1, -1)
#     """
#     monitor_hwnd = win32api.MonitorFromWindow(CONSOLE_HWND, win32con.MONITOR_DEFAULTTONEAREST)
    
#     info: dict = win32api.GetMonitorInfo( monitor_hwnd )
    
#     screen: tuple[int, int, int, int] = info.get('Work', None)
#     window = getWindowRect()
    
#     return ( screen[2] - window[0], screen[3] - window[1] )

# def getMaxConsoleSize() -> tuple[int, int]:
#     """
#     calculates maximum console size in characters based on the current left-top position of the console window and the available screen space the window is currently limited by
    
#     Returns:
#         (width_px, height_px): width and height in pixels of the maximum console window size if unsuccessful defaults to (-1, -1)
#     """
#     size = getMaxWindowSize()
#     fontSize = SCREEN_BUFFER.GetConsoleFontSize( SCREEN_BUFFER.GetCurrentConsoleFont(False)[0] )
    
#     return ( round(SIZE_SCALE_FACTOR * size[0]/fontSize.X), round(SIZE_SCALE_FACTOR * size[1]/fontSize.Y) )

# not correct at the moment
# def is_maximized() -> bool:
#     maxsize = SCREEN_BUFFER.GetLargestConsoleWindowSize()
    
#     size = getConsoleSize()
#     return size[0] == maxsize.X and size[1] == maxsize.Y
