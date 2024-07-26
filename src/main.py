from tabulate import tabulate, SEPARATING_LINE
from datetime import date
from textwrap import indent
from typing   import Callable, Optional, Generic, TypeVar
from locale   import setlocale, LC_ALL

# Custom packages
from generic_lib.logger    import get_logger
from generic_lib.consoleIO import Console, Key, keyboard
from generic_lib.utils     import *
from constants             import *

import dbWrapper     as db
import ui_controller as ctrl
import formatter     as fmt
import pdf_gen       as pdf

from generic_lib.simpleTUI import Result, Register
from generic_lib.simpleTUI import Manager, Name, Date, Value, Plain_Text
from generic_lib.simpleTUI import Button_Manager, Button, Confirm_yes_no


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

# TODO ...:                         refactor all comments/docs: reading values like gas or water are to be called reading-attributes
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

setlocale( LC_ALL, LANGUANGE_CODE )


#----------------------------------------------------------------------------------------------------------------------
# MANAGE LOGGING
#----------------------------------------------------------------------------------------------------------------------

LOGGER = get_logger( PATH_LOGS, "main", identifier = lambda r: r.funcName )


#----------------------------------------------------------------------------------------------------------------------
# MENU FUNCTIONS
#----------------------------------------------------------------------------------------------------------------------
def visualize_readings():
    Console.write_line( " --- ABLESUNGEN AUSGEBEN --- ", NL )
    #todo: better description

    Console.write_line( ctrl.generate_printout_readings_all( db.get_all_readings() ) )

def visualize_persons():
    Console.write_line( " --- PERSONEN AUSGEBEN --- ", NL )
    #todo: better description
    
    Console.write_line( ctrl.get_tabular_person_detail( db.get_all_persons() ), NL )


def manipulate_readings():
    #todo: better description
    
    Console.write_at( " --- ABLESUNG HINZUFÜGEN / ÜBERSCHREIBEN --- ", 0, 0 )

    FM = Manager(True, True).set_position_left_top( SIZE_TAB, 2 )
    
    # appending the date focus
    FM.append( Date( "Datum", preset_dates=db.get_all_reading_dates() ) )
    
    for i in range(COUNT_READING_ATTRIBUTES):
        FM.append( Value( LIST_READING_ATTRIBUTE_NAMES[i], True, None, LIST_DIGIT_OBJ_LAYOUTS[i] ) )
        FM.append_rule( 0, i+1, ctrl.TX_func_factory.date_2_value( i ) )
    
    manage_interactables(
        FM,
        lambda data: db.exist_reading( data[0] ),
        lambda data: db.add_reading( db.Reading(data[0], data[1:]) ),
        lambda data, exists_datas: ctrl.get_tabular_reading_simple( [exists_datas[0], db.Reading(data[0], data[1:])] ),
        " <-- Neu ",
        "Eine Ablesung mit folgenden Werten ist bereits eingetragen:",
        "Wollen Sie diese Werte überschreiben?",
        "Ablesung erstellt und in der Datenbank eingetragen"
    )

def manipulate_persons():
    #todo: better description
    
    Console.write_at( " --- PERSON HINZUFÜGEN / ÜBERSCHREIBEN --- ", 0, 0 )
    
    names = db.get_all_names()
    tab   = ctrl.get_tabular_names(names)
    
    width, height = get_string_dimensions( tab )
    
    Console.write_in( tab, 4, 2, 4+width, 2+height )
    
    with Console.virtual_area( (4+width+ 4, 2), reset_cursor_on_exit=False ):
        Console.write_at( "Name der zu hinzufügenden oder zu überschreibenden db.Person eingeben", 0, 0 )

        FM = Manager( True, True ).set_position_left_top( SIZE_TAB, 2 )
        
        FM\
            .append( Name( "Name", False, SIZE_NAME, False, names ) )\
            .append( Date( "Einzugsdatum", True, "" ) )\
            .append( Date( "Auszugsdatum", True, "", lambda dat: not Register.get(1) or dat >= Register.get(1) ) )\
            .append_rule( 0, 1, ctrl.TX_func_factory.name_2_dates( False ) )\
            .append_rule( 0, 2, ctrl.TX_func_factory.name_2_dates( True  ) )
        

        manage_interactables(
            FM,
            lambda data: db.exist_person( data[0] ),
            lambda data: db.add_person( db.Person(*data) ),
            lambda data, exists_datas: ctrl.get_tabular_person_simple( [exists_datas[0], db.Person(*data)] ),
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
    
    names = db.get_all_names()
    table = ctrl.get_tabular_names(names)
    
    tab_width, tab_height = get_string_dimensions( table )
    
    Console.write_in( table, SIZE_TAB, 2, SIZE_TAB+tab_width, 2+tab_height)
    
    
    with Console.virtual_area( (SIZE_TAB + tab_width + SIZE_TAB, 2), reset_cursor_on_exit=False ):
        Console.write_at( "Name der zu entfernenden db.Person eingeben", 0, 0 )
        
        FM = Manager(True, True).set_position_left_top( SIZE_TAB, 2 )
        
        FM\
            .append( Name( "Name", False, SIZE_NAME, True, names ) )
        
        manage_interactables(
            FM,
            lambda data: db.exist_person( data[0] ),
            lambda data: db.remove_person( data[0] ),
            lambda data, exists_datas: ctrl.get_tabular_person_simple( exists_datas ),
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
        .append( Date( "Datum Anfang", False, "", must_be_listed=False, preset_dates=db.get_all_reading_dates() ) )\
        .append( Date( "Datum Ende",   False, "", must_be_listed=False, preset_dates=db.get_all_reading_dates(), predicate=lambda dat: not Register.get(0) or dat >= Register.get(0) ) )\
        .append( Plain_Text( "Soll ein PDF Protokoll erstellt werden?" ) )\
        .append( Button_Manager( (1,0), (1,0) ).append_at(0,0, Button( "PDF erstellen", (3,0) )).finalize() )\
        .join()
    
    if not result.success:
        user_decline_prompt()
        return
    
    date_low  : date
    date_high : date
    create_pdf: Result
    date_low, date_high, create_pdf = result
    
    readings, persons = db.get_data_between( date_low, date_high )
    
    table_readings_raw   = ctrl.generate_printout_readings_detail( readings )
    table_readings_stats = ctrl.generate_printout_readings_statistics( readings, False )
    table_persons        = ctrl.get_tabular_person_detail( persons )
    
    Console.write( table_readings_raw, table_readings_stats, table_persons, sep="\n\n" )
    
    if create_pdf.success and create_pdf.data[0]:
        export_to_pdf(
            table_readings_raw,
            table_readings_stats,
            table_persons,
            name="export_span_%s_%s.pdf" % (date_low.strftime("%Y%m%d"), date_high.strftime("%Y%m%d"))
        )
        return
    
    Console.write_line()

def do_export_pdf():
    readings, persons = db.get_all_readings(), db.get_all_persons()
    
    table_readings_raw   = ctrl.generate_printout_readings_detail( readings )
    table_readings_stats = ctrl.generate_printout_readings_statistics( readings, True )
    table_persons        = ctrl.get_tabular_person_detail( persons )
    
    export_to_pdf( table_readings_raw, table_readings_stats, table_persons )

#----------------------------------------------------------------------------------------------------------------------
# HELPER FUNCTIONS
#----------------------------------------------------------------------------------------------------------------------
# MENU FUNCTIONS EXTENSIONS #
#---------------------------#

def delete_reading_single():
    Console.write_at( "Datum des zu entfernenden Eintrags eingeben", 0, 0 )
    
    FM = Manager(True, True).set_position_left_top( SIZE_TAB, 2 )
    
    FM\
        .append( Date( "Datum", False, "", must_be_listed=True, preset_dates=db.get_all_reading_dates() ) )
    
    manage_interactables(
        FM,
        lambda data: db.exist_reading( data[0] ),
        lambda data: db.remove_reading( data[0] ),
        lambda data, exists_datas: ctrl.get_tabular_reading_simple( exists_datas ),
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
        .append( Date( "Datum ab",  False, "", must_be_listed=False, preset_dates=db.get_all_reading_dates() ) )\
        .append( Date( "Datum bis", False, "", must_be_listed=False, preset_dates=db.get_all_reading_dates(), predicate=lambda dat: not Register.get(0) or dat >= Register.get(0) ) )
    
    manage_interactables(
        FM,
        lambda data: db.exist_readings( data[0], data[1] ),
        lambda data: db.remove_readings( data[0], data[1] ),
        lambda data, exists_data: ctrl.get_tabular_reading_simple( exists_data ),
        " <-- Entfernen",
        "Zu Entfernende Einträge",
        "Wollen Sie diese Einträge entfernen?",
        "Einträge aus der Datenbank entfernt",
        "Kein Einträge im angegebenen Zeitraum gefunden"
    )

def export_to_pdf( table_readings_raw: str, table_readings_stats: str, table_persons: str, export_name: str="export_%s.pdf" % date.today().strftime("%Y%m%d") ):
    Console.write_line( " --- PROTOKOLL EXPORTIEREN - PDF --- ", NL )
    
    pdf.export_to_pdf( table_readings_raw, table_readings_stats, table_persons, PATH_PDF, export_name )
    
    Console.write_line(
        f"\tProtokoll über alle Werte wurde am {date.today().strftime( DATE_STR_FORMAT )} erstellt", 
        f"\tund als \"{export_name}\" in Ihrem Dokumenten-Ordner \"{PATH_PDF.absolute()}\" gespeichert",
        "",
        sep='\n' )


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


T_fm_data = Generic[ TypeVar('T_fm_data', bound=list[object | None]) ]
T_db = Generic[ TypeVar('T_db') ]
def manage_interactables(
    fm               : Manager,
    db_get           : Callable[[T_fm_data], tuple[bool, list[T_db]] ],
    db_set           : Callable[[T_fm_data], None ],
    table_generator  : Callable[[T_fm_data, list[T_db]], str],
    table_side_prompt: str,
    header_text      : str,
    confirm_text     : str,
    successful_text  : str,
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
        - fm (`Manager`): Manager where the user made their input
        - db_get (`(T_fm_data) -> (bool, T_db)`): func to get `T_db` data from the database for a given `T_fm_data` result data
        - db_set (`(T_fm_data) -> None`): function to alter(i.e. set/remove/override) data from the db for a given `T_fm_data` result data:
        - table_generator (`(T_fm_data, list[T_db]) -> str`): tabulating function visualizing already existing `T_fm_data` data points to be overridden by `T_db` data points or removed from the database :
        - table_side_prompt (`str`):           text pinned at the side of the table to indicate the associated action
        - header (`str`):                      text printed before the table
        - confirm (`str`):                     text to ask the user to confirm the action
        - successful_set (`str`):              text to print after successful performing the action
        - unsuccessful_text (`Optional[str]`): if `not None`, will print text to the Console and do not call `db_set`. If `None`, will always (unless entry exists in db and requires user confirmation) call `db_set`. Defaults to `None`.
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
    #  Y+4 |  Optional[ Plain[ db.Reading added ] ]
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
    

    fm_data: T_fm_data = fm_result.data
    
    exists, data = db_get( fm_data )
    
    if unsuccessful_text and not exists:
        Console.write_at( unsuccessful_text, 0, LINE_PTR+2 )
        user_decline_prompt(0, LINE_PTR+3)
        return
    
    if exists:
        tab = table_generator( fm_data, data )
        for i in range( len(data) ):
            tab = fmt.add_side_note_to_tabular( tab, table_side_prompt, -(2+i) )
        
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


#----------------------------------------------------------------------------------------------------------------------
# MAIN LOOP AND STARTING POINT
#----------------------------------------------------------------------------------------------------------------------
MENU_OPTIONS: list[Callable[[], None]] = [
    visualize_readings,
    visualize_persons,
    manipulate_readings,
    manipulate_persons,
    delete_reading,
    delete_person,
    do_invoice,
    do_analyze,
    do_export_pdf,
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
