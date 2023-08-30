from datetime import date, datetime
from calendar import isleap
from math import floor, sqrt
from time import sleep, time

from tabulate import tabulate, SEPARATING_LINE, PRESERVE_WHITESPACE
from textwrap import indent

from platformdirs import user_documents_path

# helpful docs and guides for reportlab, since i couldnt find any original nice docuentation by them
# https://www.reportlab.com/docs/reportlab-reference.pdf
# https://www.reportlab.com/docs/reportlab-userguide.pdf
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.pdfbase.pdfmetrics import stringWidth

# keystrokes access without input(...)
import msvcrt

import win32gui
import win32con
import os
import locale
import webbrowser

# Custom packages
from dbHandler import DBSession
from constants import *


  #:########:#
 #: TODO's :#
#:########:#

#// TODO manipulate_person:   moving_out date must be blank or greater than moving_in date
#// TODO visualize_person:    person with moving_in date in the future and no moving_out date has negative amount of occupancy months
#// TODO visaulize_reading:   add table of monthly and yearly averages and add it to the pdf output
#// TODO visaulize_reading:   add better key input with arrow cursur moving
#// TODO visualize_readding:  fix broken curser input for get_general

#// TODO visaulize_reading:   installing a new meter causes negative extrapolation of the data
#// TODO export_to_pdf:       put the readings conclusion on a new line to (avoid bad page-breaks) improve readability
#// TODO export_pdf:          open file in browser or explorer after generating
#// TODO: ...                 add icon to project
#// TODO: main.py:            add icon and title to terminal window
#// TODO: .spec               add icon to .exe
#// TODO: ...                 add CHANGELOG.md for automated releases
# TODO .spec                add version-resource-file to .spec
# TODO analyse:             add functionality to analyse timespans
# TODO analyse:             add functionality to export anlysed timespan to pdf
# TODO visaulize_reading:   add predicitons for the upcoming invoice's compensation payment
# TODO do_invoice:          complete invoice
# TODO ...:                 add descriptions to all menu/interaction pages
# TODO ...:                 de-hard-code main.py by making printed str's to constant variables and move them to constants.py


SESSION = DBSession()

# from tabulate namespace
PRESERVE_WHITESPACE = True

locale.setlocale( locale.LC_ALL, LANGUANGE_CODE )

#################################################
  ######
 # UI #
######
def cls():
    os.system("cls")


def flush_menu():
    cls()
    print( TITLE )
    
    print( "Eine Option mit den Tasten 1-9 auswählen" )
    print_menu_options()
    print( "Um das Programm zu verlassen: Ctrl+C drücken", NL )

def print_menu_options():
    tab = tabulate( MENUS, tablefmt="simple", disable_numparse=True, colalign=('right', 'left') )
    
    print( NL, indent( tab, '\t' ), NL, sep='' )


def user_decline_prompt():
    print( " --- Handlung wurde abgebrochen" )

def user_to_menu_prompt():
    input( " --- Eingabe-Taste drücken um in das Menü zurückzukehren" )

# !!! will freeze with wait_for_change=True when executing with VSCode, requires external terminal window
def set_window_title( window_title_string, wait_for_change=False ) -> None:
    os.system("title " + window_title_string)
    
    if (not wait_for_change):
        return
    
    matched_window = 0
    while (not matched_window):
        matched_window = win32gui.FindWindow(None, window_title_string)
        sleep(0.025) # To not flood it too much...

def set_window_icon( window_title, image_path ):
    hwnd  = win32gui.FindWindow(None, window_title)
    hicon = win32gui.LoadImage(None, image_path, win32con.IMAGE_ICON, 0, 0, win32con.LR_LOADFROMFILE | win32con.LR_DEFAULTSIZE)
    
    win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, hicon)
    win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, hicon)

def set_title_and_icon(window_title, icon_path):
    """Set the window title, wait for it to apply, then adjust the icon."""
    window_title = set_window_title(window_title, wait_for_change=True)
    set_window_icon(window_title, icon_path)
    return window_title


def await_user_key_codes( console_out_function, data:str, cursur_ptr:int, cursur_char_data:str='_', cursur_char_placeholder:str=' ' ) -> int:
    period = 0.5
    time_next_flip = -1
    cursur_on = False
    current_data = data
    
    while not msvcrt.kbhit():
        if time() >= time_next_flip:
            time_next_flip = time() + period
            
            # cursur = not cursur; if cursur: ...
            if cursur_on := not cursur_on:
                current_data = data[:cursur_ptr] + (cursur_char_placeholder if data[min(max(0, cursur_ptr), len(data)-1)] == PLACE_HOLDER else cursur_char_data) + data[cursur_ptr+1:]
            else:
                current_data = data
        print( console_out_function( current_data ), end='\r' )
        
    return ord(msvcrt.getwch())


def get_date( prefillDateISO:str=date.today().strftime("%d%m%Y"), validRequired:bool=True, prompt_name:str="Datum:", date_predicat=lambda d: True ) -> date or None:
    """
    parameter date_predicat: after verifying if the user supplied date is a valid, the date_predicat takes the supplied date as input and returns true if the supplied date should be accepted in the current context
    """
    # data:layout = 'ddmmyyyy'
    #                01234567
    data = ( prefillDateISO + PLACE_HOLDER*8 )[:8] # right padding with place holder chars
    data_ptr = max( 0, len(prefillDateISO)-1 )
    
    console_out_explicit = lambda pn, d: f"\t{pn} {d[0:2]}.{d[2:4]}.{d[4:8]}"
    console_out = lambda: console_out_explicit( prompt_name, data )
    
    while True:
        key = await_user_key_codes( lambda _data: console_out_explicit(prompt_name, _data), data, data_ptr )
        
        # enter keycode
        if key == KEY_ENTER:
            # check for empty entry (if not validRequired)
            if data == PLACE_HOLDER*8 and not validRequired:
                print( console_out() + "\t - REGISTERED EMPTY ENTRY", end='\r' )
                return None
            
            # otherwise try parsing the user input to a date
            try:
                supplied_date = date.fromisoformat( '-'.join([data[4:8], data[2:4], data[0:2]]) )
                
                if not date_predicat( supplied_date ):
                    raise ValueError()
                
                print( console_out(), end='\r' )
                
                return supplied_date
            except ValueError:
                print( console_out() + "\t - INVALID ENTRY", end='\r' )
            
            continue

        # digit keycode (ord[48-57] mapping to str[0-9])
        if 48 <= key <= 57:
            data = data[:data_ptr] + chr(key) + data[data_ptr+1:]
            data_ptr = min( data_ptr+1, 7 )
        
        # complete line delete
        if key == KEY_CTRL_BACKSPACE:
            data_ptr = 0
            data = PLACE_HOLDER*8
        
        # single character delete
        if key == KEY_BACKSPACE:
            data = data[:data_ptr] + PLACE_HOLDER + data[data_ptr+1:]
            data_ptr = max(0, data_ptr-1)
        
        # moving cursur
        if key == KEY_SPECIAL:
            key = ord(msvcrt.getwch()) # get the second part of the key code
        
            if key == KEY_LEFT:
                data_ptr = max(0, data_ptr-1)
                
            if key == KEY_RIGHT:
                data_ptr = min( data_ptr+1, 7 )
        
        # update visuals
        print( ' '*60, end='\r' )

def get_general( prompt_name:str, digit_count:tuple[int, int], prefill:float=None ) -> float:
    digit_sum = digit_count[0] + digit_count[1]
    
    data_ptr = digit_sum - 1
    
    if not prefill:
        data = PLACE_HOLDER * digit_sum
    else:
        # assure float-type
        prefill = float(prefill)
        
        
        #? transform float to the needed str format, so that the user input can correctly be entred
        #? { str(floor(prefill)) : PLACE_HOLDER > digit_count[0] s }         right fit pre-period digits with leading PLACE_HOLDER chars
        #? { str( prefill - floor(prefill) )[2:] : 0 < digit_count[1] s }    left fit post-period digits with trealing zeros
        #? str( round( prefill - floor(prefill), digit_count[1] ) )[2:]      string of the decimal part of the float, will always be leading with '0.', therefor slice string [2:]
        #? round( prefill - floor(prefill), digit_count[1] )                 assure only digit_count[1] amount of digits after the period
        data = ( "{:%s>%ds}{:0<%ds}" % (PLACE_HOLDER, digit_count[0], digit_count[1]) ).format( str( floor(prefill) ), str( round( prefill - floor(prefill), digit_count[1] ) )[2:] )
    
    console_out_explicit = lambda pn, d: f"\t{pn} {d[0:digit_count[0]]}.{d[digit_count[0]:]}"
    console_out = lambda: console_out_explicit( prompt_name, data )
    
    while True:
        # key = await_user_key( lambda _data: console_out_explicit(prompt_name, _data), data, data_ptr )
        key = await_user_key_codes( lambda _data: console_out_explicit(prompt_name, _data), data, data_ptr )
        
        if key == KEY_ENTER: # enter keycode
            try:
                # reconstruct the value as a string of float format
                value = float( f"{data[:digit_count[0]]}.{data[digit_count[0]:]}".replace(PLACE_HOLDER, '0') )
                
                # update data with zero-padding and print to screen as user feedback
                data = ("{:>%d.%df}" % (digit_sum+1, digit_count[1])).format( value ).replace('.', '')
                print( console_out(), end='\r' )
                
                return value
            except ValueError as e:
                pass
                
            print( console_out().rstrip() + "\t - INVALID ENTRY", end='\r' )
        else:
            # digit keycode (ord[48-57] mapping to str[0-9])
            if 48 <= key <= 57:
                # curser at trailing position
                if data_ptr == digit_sum-1:
                    if data[0] == PLACE_HOLDER:
                        # left shift data array and append user input (key) at end, if data has empty leading slots
                        data = data[1:] + chr(key)
                        print( console_out(), end='\r' )
                else:
                    data = data[:data_ptr] + chr(key) + data[data_ptr+1:]
                    data_ptr = min( data_ptr+1, digit_sum - 1 )
            
            # complete line delete
            if key == KEY_CTRL_BACKSPACE:
                data_ptr = digit_sum - 1
                data = PLACE_HOLDER * digit_sum
            
            # single character delete
            if key == KEY_BACKSPACE:
                if data_ptr == digit_sum-1:
                    data = PLACE_HOLDER + data[:len(data)-1]
                else:
                    data = data[:data_ptr] + PLACE_HOLDER + data[data_ptr+1:]
                    data_ptr = max(0, data_ptr-1)
            
            # moving cursur
            if key == KEY_SPECIAL:
                key = ord(msvcrt.getwch()) # get the second part of the key code
            
                if key == KEY_LEFT:
                    data_ptr = max(0, data_ptr-1)
                    
                if key == KEY_RIGHT:
                    data_ptr = min( data_ptr+1, digit_sum-1 )
            
        # update visuals
        print( ' '*60, end='\r' )

def get_string( prompt_name:str="\tName:" ) -> str:
    while True:
        n = input( '\t'+ prompt_name + ' ' ).strip().lower()
        
        if not n:
            print( '\t', "! Ungültiger Name, bitte anderen Namen wählen ! ", NL, sep='' )
            continue
        
        return n

#################################################
  #############
 # FUNCTIONS #
#############
def visualize_readings():
    print( " --- ABLESUNGEN AUSGEBEN --- ", NL )
    #todo: better description
    
    print( gather_readings_output() )

def visualize_persons():
    print( " --- PERSONEN AUSGEBEN --- ", NL )
    #todo: better description
    
    data = SESSION.get_person_all()
    
    table = get_tabular_person_detail( data )
    
    print( table, NL )


def manipulate_readings():
    print( " --- ABLESUNG HINZUFÜGEN / ÜBERSCHREIBEN --- ", NL )
    #todo: better description
    
    # setable-ish in future should be handled automatically
    min_len_prompt_title = len( max( [NAME_ELECTRICITY, NAME_GAS, NAME_WATER, "Datum"], key=lambda x: len(x) ) )
    
    prompt_format_str = "{:>%ds}:" % min_len_prompt_title
    
    d = get_date( prompt_name=prompt_format_str.format( "Datum" ) );                                             print()
    
    exists, data = SESSION.exists_readings( d, d )
    _, e, g, w = data[0] if exists else ( None, None, None, None )
    
    e = get_general( prompt_format_str.format(NAME_ELECTRICITY), DIGIT_LAYOUT_ELECTRICITY, e );   print()
    g = get_general( prompt_format_str.format(NAME_GAS)        , DIGIT_LAYOUT_GAS        , g );   print()
    w = get_general( prompt_format_str.format(NAME_WATER)      , DIGIT_LAYOUT_WATER      , w );   print()
    
    sleep(KEYBOARD_SLEEP_TIME)
    print()
    
    if exists:
        print( "Eine Ablesung mit folgenden Werten ist bereits eingetragen:" )
        print( add_side_note_to_tabular( get_tabular_reading_simple( [data[0],(d,e,g,w)] ), " <-- Neu ", -2 ), NL )
        
        decision:str = input( "Wollen Sie diese Werte überschreiben [Y/N]: " )
        
        if not decision in ["Y", "y"]: # User declined to override
            print()
            user_decline_prompt()
            return
    
    SESSION.add_reading(d, e, g, w)
    
    print( NL, "Ablesung erstellt und in der Datenbank eingetragen", NL, sep='' )

def manipulate_persons():
    print( " --- PERSON HINZUFÜGEN / ÜBERSCHREIBEN --- ", NL )
    #todo: better description
    
    print_all_names()
    
    print( "Name der zu hinzufügenden oder zu überschreibenden Person eingeben", NL )
    
    prompts_name = "        Name:"
    prompts_din  = "Einzugsdatum:"
    prompts_dout = "Auszugsdatum:"
    
    nameID = get_string( prompts_name )
    
    exists, data = SESSION.exists_person( nameID )
    
    d1, d2 = None, None
    
    if exists:
        try: d1 = data[1].strftime("%d%m%Y")
        except (AttributeError, IndexError): pass
        
        try: d2 = data[2].strftime("%d%m%Y")
        except (AttributeError, IndexError): pass
    
    move_in  = get_date( d1 if d1 else "", False, prompts_din ); print()
    move_out = get_date( d2 if d2 else "", False, prompts_dout, lambda d: d >= move_in ); print()
    
    sleep(KEYBOARD_SLEEP_TIME)
    print()
    
    if exists:
        print( "Eine Person mit folgenden Werten ist bereits eingetragen:" )
        print( add_side_note_to_tabular( get_tabular_person_simple( [data,(nameID, move_in, move_out)] ), " <-- Neu ", -2 ), NL )
        
        decision:str = input( "Wollen Sie diese Werte überschreiben [Y/N]: " )
        
        if not decision in ["Y", "y"]: # User declined to override
            print()
            user_decline_prompt()
            return
    
    SESSION.add_person(nameID, move_in, move_out)
    
    print( NL, "Person in die Datenbank eingetragen", sep='' )


def delete_reading():
    print( " --- ABLESUNG ENTFERNEN --- ", NL )
    #todo: better description
    
    # sub menu management
    tab = tabulate( [
        [ "1)", "Einen Eintrag entfernen" ],
        [ "2)", "Mehrere Einträge entfernen" ],
        SEPARATING_LINE,
        [ "beliebig", "Zum Menü zurückkehren" ],
    ], tablefmt="simple", disable_numparse=True, colalign=('right', 'left') )
    
    print( "Eine Option mit den Tasten 1-9 auswählen" )
    print( NL, indent( tab, '\t' ), NL, sep='' )
    option:str = input("Action auswählen: ")
    
    option = int(option) if option.isdigit() else 9
    
    # logic management
    if option == 1: # removing only one entry
        print( "Datum des zu entfernenden Eintrags eingeben", NL )
        d = get_date( "" ); print()

        exists, data = SESSION.exists_readings( d, d )
        sleep(KEYBOARD_SLEEP_TIME)
        print()
        
        if not exists:
            print( f"Kein Eintrag gefunden mit dem Datum: {d.strftime( DATE_STR_FORMAT )}", NL )
            return
        
        print( add_side_note_to_tabular( get_tabular_reading_simple( data ), " <-- Entfernen ", -2 ), NL )
        
        decision:str = input( "Wollen Sie diesen Eintrag entfernen [Y/N]: " )
        
        if not decision in ["Y", "y"]: # User declined to override
            print()
            user_decline_prompt()
            return
    
        SESSION.remove_readings( d, d )
        
        print( NL, "Eintrag aus der Datenbank entfernt", NL, sep='' )
        
    if option == 2: # removing multiple entries
        print( "Daten für Zeitinterval der zu entfernenden Einträge eingeben", NL )
        d_from = get_date( "", True, "Datum ab: " )                       ; print()
        d_till = get_date( "", True, "Datum bis:", lambda d: d >= d_from ); print()

        exists, data = SESSION.exists_readings( d_from, d_till )
        sleep(KEYBOARD_SLEEP_TIME)
        print()
        
        if not exists:
            print( f"Keine Einträge gefunden im Zeitraum: {d_from.strftime( DATE_STR_FORMAT )} - {d_till.strftime( DATE_STR_FORMAT )}", NL )
            return
        
        table = get_tabular_reading_simple( data )
        for i in range( len(data) ):
            table = add_side_note_to_tabular( table, " <-- Entfernen ", -(2+i) )
        
        print( table, NL )
        
        decision:str = input( "Wollen Sie diese Einträge entfernen [Y/N]: " )
        
        if not decision in ["Y", "y"]: # User declined to override
            print()
            user_decline_prompt()
            return
    
        SESSION.remove_readings( d_from, d_till )
        
        print( NL, "Einträge aus der Datenbank entfernt", sep='' )

def delete_person():
    print( " --- PERSON ENTFERNEN --- ", NL )
    #todo: better description
    
    print_all_names()
    
    print( "Name des zu entfernenden Eintrags eingeben", NL )
    
    nameID = get_string()
    
    exists, data = SESSION.exists_person( nameID )
    sleep(KEYBOARD_SLEEP_TIME)
    print()
    
    if not exists:
        print( f"Kein Eintrag gefunden mit dem Namen: {nameID}", NL )
        return
    
    print( add_side_note_to_tabular( get_tabular_person_simple( [data] ), " <-- Entfernen ", -2 ), NL )
    
    decision:str = input( "Wollen Sie diesen Eintrag entfernen [Y/N]: " )
    
    if not decision in ["Y", "y"]: # User declined to override
        print()
        return

    SESSION.remove_person( nameID )
    
    print( NL, "Eintrag aus der Datenbank entfernt", sep='' )


def do_invoice():
    print( " --- ABRECHNUNG DURCHFÜHREN --- ", NL )
    #todo: better description
    
    print( "INOP" )

def do_analyze():
    print( "Manuelle Analyse der Ablesungen über einen Zeitraum", NL )
    
    prompt_low  = "Datum Anfang:" 
    prompt_high = "Datum Ende:  "
    
    date_low  = get_date( "", True, prompt_low ); print()
    date_high = get_date( "", True, prompt_high, lambda d: d >= date_low ); print()
    
    data = SESSION.get_reading_between( date_low, date_high )
    
    table_readings = get_tabular_reading_detail( data )
    table_months = get_tabular_reading_stats( data )
    
    print( ''.join([table_readings, NL, NL, table_months, NL]) )
    
    decision:str = input( "Soll ein PDF Protokoll erstellt werden? [Y/N]: " )
    
    if not decision in ["Y", "y"]: # User declined to override
        print()
        return
    
    export_to_pdf( data_readings=data, name="export_span_%s_%s.pdf" % (date_low.strftime("%Y%m%d"), date_high.strftime("%Y%m%d")) )

def export_to_pdf( data_readings:list[tuple[date, float, float, float]]=SESSION.get_reading_all(), data_persons:list[tuple[str, date, date]]=SESSION.get_person_all(), name:str="export_%s.pdf" % date.today().strftime("%Y%m%d") ):
    print( " --- PROTOKOLL EXPORTIEREN - PDF --- ", NL )
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
    
    # inividual readings
    c.setFont( PDF_FONT_TABLE, 16 )
    c.drawString( RX, 120, "Ablesungen:" )
    
    table_readings = get_tabular_reading_detail( data_readings )
    draw_pdf_page( table_readings, c, WIDTH, HEIGHT, RX, RY, 80, PDF_FONT_TABLE, TABLE_CONTINUE_STR )
    
    # statistics readings
    c.setFont( PDF_FONT_TABLE, 16 )
    c.drawString( RX, RY-20, "Statistiken:" )
    
    table_months = get_tabular_reading_stats( data_readings )
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
    
    print( '\t', f"Protokoll am {date.today().strftime( DATE_STR_FORMAT )} über alle Werte wurde erstellt", sep='' )
    print( '\t', f"und als \"{EXPORT_NAME}\" in Ihrem Dokumenten-Ordner \"{user_documents_path()}\" gespeichert", sep='' )
    
    print()


def print_all_names( tablefmt="grid" ):
    # print out all the names of the person in the database
    
    data = SESSION.get_person_all()
    
    names = [ [n] for n, *_ in data ]
    
    table = tabulate( names, headers=["Personen in der Datenbank"], tablefmt=tablefmt, colalign=['center'] )
    
    print( table, NL )


def format_decimal( value:float, digit_layout:tuple[int, int], alignement_format:str='>', format_size:int=None ) -> str:
    # to clamp the value to the specified digit_layout: abs_max = 10**digit_layout[0] - 10**(-digit_layout[1])
    # 
    # example:
    # >>> digit_layout = (2,3)
    # abs_max = 10**digit_layout[0] - 10**(-digit_layout[1]) = 100 - 0.001 = 99.999
    
    # sum(digit_layout)  + 1     + 1
    #       ^^^^          ^       ^^
    # number of digits,  '.', '-' or ' '
    
    abs_max = 10**digit_layout[0] - 10**(-digit_layout[1])
    formated_digits = ( "{: >%d.%df}" % ( sum(digit_layout) + 1 + 1, digit_layout[1] ) ).format( max( -abs_max, min( value, abs_max ) ) )
    
    if not format_size:
        return formated_digits
    
    return ( "{:%s%ds}" % ( alignement_format, format_size ) ).format( formated_digits )

def extrapolate_averageOut_data( value_dateMin:float, value_dateMax:float, days_date_span:int, days_in_month:int ) -> tuple[ float, float, float ]:
    
    true_delta    = value_dateMax - value_dateMin
    delta_per_day = true_delta / days_date_span
    extra_delta   = ( days_in_month - days_date_span ) * delta_per_day
    
    return true_delta + extra_delta, delta_per_day, 7 * delta_per_day

def extrapolate_meanOut_data( total_delta:float, per_day_mean:float, delta_days:float ) -> tuple[ float, float, float ]:
    extra_delta = delta_days * per_day_mean
    
    return total_delta + extra_delta, per_day_mean, 7 * per_day_mean


def format_reading_data( d:date, e:float, g:float, w:float ) -> tuple[str, str, str, str]:
    return (
        d.strftime( DATE_STR_FORMAT ),
        format_decimal( e, DIGIT_LAYOUT_ELECTRICITY ),
        format_decimal( g, DIGIT_LAYOUT_GAS ),
        format_decimal( w, DIGIT_LAYOUT_WATER )
    )

def format_person_data( name:str, move_in:date, move_out:date ) -> tuple[str, str, str]:
    return (
        name,
        move_in.strftime( DATE_STR_FORMAT ) if move_in else None,
        move_out.strftime( DATE_STR_FORMAT ) if move_out else None,
    )


def get_tabular_reading_simple( data:list[tuple[date, float, float, float]], tablefmt="psql" ) -> str:
    data = [ format_reading_data(*d) for d in data ]
    return tabulate(
        data,
        headers=TABLE_HEADER_READINGS_SIMPLE,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('left', 'decimal', 'decimal', 'decimal')
    )

def get_tabular_person_simple( data:list[tuple[str, date, date]], tablefmt="psql" ) -> str:
    data = [ format_person_data(*d) for d in data ]
    return tabulate(
        data, 
        headers=TABLE_HEADER_PERSONS_SIMPLE, 
        tablefmt=tablefmt, 
        colalign=('right', 'center', 'center'), 
        maxcolwidths=[15, None, None, None]
    )


def get_tabular_reading_detail( data:list[tuple[date, float, float, float]], tablefmt="grid" ) -> str:
    table_data = []
    for i, (d, e, g, w) in enumerate( data ):
        delta_d = (d - data[i-1][0]).days if i > 0 else 0
        delta_e = (e - data[i-1][1]) if i > 0 else 0
        delta_g = (g - data[i-1][2]) if i > 0 else 0
        delta_w = (w - data[i-1][3]) if i > 0 else 0
        
        table_data.append( [
            d.strftime( DATE_STR_FORMAT ) +NL+ f"    Tage:{delta_d:>3d}",
            #todo: make aligne first row
            format_decimal( e, DIGIT_LAYOUT_ELECTRICITY ) +NL+ format_decimal( delta_e/delta_d if delta_d else 0, DIGIT_LAYOUT_DELTA ) +" "+ format_decimal( delta_e, DIGIT_LAYOUT_ELECTRICITY ),
            format_decimal( g, DIGIT_LAYOUT_GAS         ) +NL+ format_decimal( delta_g/delta_d if delta_d else 0, DIGIT_LAYOUT_DELTA ) +" "+ format_decimal( delta_g, DIGIT_LAYOUT_GAS ),
            format_decimal( w, DIGIT_LAYOUT_WATER       ) +NL+ format_decimal( delta_w/delta_d if delta_d else 0, DIGIT_LAYOUT_DELTA ) +" "+ format_decimal( delta_w, DIGIT_LAYOUT_WATER ),
        ])
    
    if not data: # Database has no entries
        table_data = [["no data"]*len(TABLE_HEADER_READINGS_DETAIL)]
    
    return tabulate(
        table_data,
        headers=TABLE_HEADER_READINGS_DETAIL,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('left', 'center', 'center', 'center')
    )

def get_tabular_reading_months( data:list[tuple[date, float, float, float]], tablefmt="grid" ) -> str:
    # table calculates extrapolated consumptions per month, per Day per Month and per Week per month
    # +--------------------------+--------------------------+--------------------------+--------------------------+
    # | Monat                    |          Strom           |           Gas            |          Wasser          |
    # | Anz. Eintr.   Zeitspanne | Extrapolierter Verbrauch | Extrapolierter Verbrauch | Extrapolierter Verbrauch |
    # |                          |   pro Tag    pro Woche   |   pro Tag    pro Woche   |   pro Tag    pro Woche   |
    # +==========================+==========================+==========================+==========================+
    
    table_data = []
    
    # get the maximum width of each columns header
    column_widths = [ len( max( lines.splitlines(), key=lambda x: len(x) ) ) for lines in TABLE_HEADER_READINGS_MONTHS ]
    
    # sort all data entries by date (they should allready be ordered correctly, but you never know)
    data = sorted( data, key=lambda d, *_: d )
    
    # get all unique years as a dicts
    years = { d.year:{} for d, e, g, w in data }
    
    for year in sorted( years.keys() ):
        # get all unique months of a specific year as a dicts
        months = { d.month:[] for d, *_ in data if d.year == year }
        
        # put all entries into their associated month slot
        for d, e, g, w in data:
            months[d.month].append( (d, e, g, w) )
            
        # filter out all months with not enought entries for proper calculations
        months = { k: v for k, v in months.items() if len(v) > 1 }
        
        years[year] |= months
        
        for month_id, entries in months.items():
            if month_id == 12:
                next_month_date = date(year+1, 1, 1)
            else:
                next_month_date = date(year, month_id+1, 1)
                
            days_in_month = ( next_month_date - date(year, month_id, 1)).days
            
            days_date_span = ( entries[-1][0] - entries[0][0] ).days
            
            # todo de-spaghettify, improve readability
            # month entry
            table_data.append( [
                entries[0][0].strftime( "%Y : %B" ) +NL+ \
                    f" {len(entries):>3d}" + ("{:>%ds}" % ( column_widths[0] - 3 ) ).format( f"{entries[0][0].day:>3d}. - {entries[-1][0].day:>3d}." ),
                "{:s}\n{:s}     {:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( extrapolate_averageOut_data( entries[0][1], entries[-1][1], days_date_span, days_in_month ), [DIGIT_LAYOUT_ELECTRICITY]+[DIGIT_LAYOUT_DELTA]*2 ) ] ),
                "{:s}\n{:s}     {:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( extrapolate_averageOut_data( entries[0][2], entries[-1][2], days_date_span, days_in_month ), [DIGIT_LAYOUT_GAS]        +[DIGIT_LAYOUT_DELTA]*2 ) ] ),
                "{:s}\n{:s}     {:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( extrapolate_averageOut_data( entries[0][3], entries[-1][3], days_date_span, days_in_month ), [DIGIT_LAYOUT_WATER]      +[DIGIT_LAYOUT_DELTA]*2 ) ] )
            ] )
        
        degw_min = months[ min(months) ][0]
        degw_max = months[ max(months) ][-1]
        
        days_date_span = ( degw_max[0] - degw_min[0] ).days
        
        # todo de-spaghettify, improve readability
        # year entry
        table_data.append( [
            ( "%d : {:>%ds}" % (year, column_widths[0] - 4 - 2) ).format('Jahreswerte') +NL+ \
                f" {sum(len(v) for v in months.values()):>3d}" + ("{:>%ds}" % ( column_widths[0] - 3 ) ).format( f"{degw_min[0].strftime('%b'):>3s} - {degw_max[0].strftime('%b'):>3s}" ),
            "{:s}\n{:s}     {:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( extrapolate_averageOut_data( degw_min[1], degw_max[1], days_date_span, 365.25 ), [DIGIT_LAYOUT_ELECTRICITY]+[DIGIT_LAYOUT_DELTA]*2 ) ] ),
            "{:s}\n{:s}     {:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( extrapolate_averageOut_data( degw_min[2], degw_max[2], days_date_span, 365.25 ), [DIGIT_LAYOUT_GAS]        +[DIGIT_LAYOUT_DELTA]*2 ) ] ),
            "{:s}\n{:s}     {:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( extrapolate_averageOut_data( degw_min[3], degw_max[3], days_date_span, 365.25 ), [DIGIT_LAYOUT_WATER]      +[DIGIT_LAYOUT_DELTA]*2 ) ] )
        ] )
        table_data.append( [ "- "*(column_widths[i]//2) for i in range(len(TABLE_HEADER_READINGS_MONTHS)) ] )
    
    if not data: # Database has no entries
        table_data = [["no data"]*len(TABLE_HEADER_READINGS_MONTHS)]
    
    return tabulate(
        table_data,
        headers=TABLE_HEADER_READINGS_MONTHS,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('left', 'center', 'center', 'center')
    )

def get_tabular_person_detail( data:list[tuple[str, date, date]], tablefmt="grid" ) -> str:
    PLACE_HOLDER = '*'
    
    table_data = []
    
    for i, (n, din, dout) in enumerate( data ):
        # setup default values
        din_str  = din.strftime(  DATE_STR_FORMAT ) if din  else PLACE_HOLDER
        dout_str = dout.strftime( DATE_STR_FORMAT ) if dout else PLACE_HOLDER
        effective_months_str = PLACE_HOLDER
        invoices = PLACE_HOLDER
        
        if din:
            artifical_dout = dout if dout else date.today()
            
            years_str_list = [ str(year) for year in range(din.year, artifical_dout.year+1, 1) ]
            
            if artifical_dout >= din:
                delta_days, delta_fraction = divmod( ( artifical_dout - din ).days, 30 )
                
                delta_str = "%s%d" % ( '<' if delta_fraction < 15 else '', delta_days+1 )
                
                effective_months_str = ''.join( [delta_str, NL, din.strftime("%b%y"), ' - ', artifical_dout.strftime("%b%y") ] )
            else:
                effective_months_str = "noch nicht\neingezogen\n"
                years_str_list = [ f"( {din.year} )" ]
            
            invoices = NL.join( years_str_list )
            
            # hint today's date in the moving_out slot in the table if no moving_out date is present
            if not dout:
                dout_str = NL.join( [ PLACE_HOLDER, f"( { date.today().strftime( DATE_STR_FORMAT ) } )" ] )
        
        table_data.append( [
            n,
            din_str,
            dout_str,
            effective_months_str,
            invoices
        ])
        
    if not data: # Database has no entries
        table_data = [["no data"]*len(TABLE_HEADER_PERSONS_DETAIL)]
    
    return tabulate(
        table_data,
        headers=TABLE_HEADER_PERSONS_DETAIL,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('right', 'center', 'center', 'center', 'center'),
        maxcolwidths=[15, None, None, None, None]
    )


def add_side_note_to_tabular( table:str, side_note:str, row:int ) -> str:
    lines = table.splitlines()
    lines[row] += side_note
    return NL.join( lines )


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
    max_row_len = len( max( table_lines.splitlines(), key=lambda x: len(x) ) )
    
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
    

def gather_readings_output() -> str:
    data = SESSION.get_reading_all()
    
    table_readings = get_tabular_reading_detail( data )
    table_months = get_tabular_reading_stats( data )
    
    return ''.join([table_readings, NL, NL, table_months, NL])


def readings_calculate_statistics( points:tuple[date, float, float, float] ) -> tuple[int, tuple[float, float,float,float], tuple[float, float,float,float], tuple[float, float,float,float]]:
    amount_points = len(points)
    
    if amount_points == 0:
        return (0, (0,0,0,0), (0,0,0,0), (-1,-1,-1,-1))
    
    delta_d,         delta_e,         delta_g,         delta_w         = 0, 0, 0, 0
    total_d,         total_e,         total_g,         total_w         = 0, 0, 0, 0
    sum_stats_d,     sum_stats_e,     sum_stats_g,     sum_stats_w     = 0, 0, 0, 0
    sum_stats_sqr_d, sum_stats_sqr_e, sum_stats_sqr_g, sum_stats_sqr_w = 0, 0, 0, 0
    
    gap_e, gap_g, gap_w = 0, 0, 0
    
    last_d, last_e, last_g, last_w = points.pop(0)
    
    if amount_points == 1:
        return (1, (last_d, last_e, last_g, last_w), (0, 0, 0, 0), (-1,-1,-1,-1))
    
    for d, e, g, w in points:
        delta_d = (d - last_d).days
        delta_e = e - last_e
        delta_g = g - last_g
        delta_w = w - last_w
        
        last_d = d
        last_e = e
        last_g = g
        last_w = w
        
        
        # to correct for large negative values, e.g. because a meter got changed and was reseted to 0 or other faulty data
        # in this context we usually expect positive changes, i.e. strictly monotonic increasing data points
        # therefor we reject negative deltas and do not include that timespan (and values)
        if delta_e < 0:
            gap_e += delta_d
            delta_e = 0     # so that we dont influence our running statistics
        
        if delta_g < 0:
            gap_g += delta_d
            delta_g = 0     # so that we dont influence our running statistics
        
        if delta_w < 0:
            gap_w += delta_d
            delta_w = 0     # so that we dont influence our running statistics
        
        
        total_d += delta_d
        total_e += delta_e
        total_g += delta_g
        total_w += delta_w
        
        sum_stats_d += delta_d
        sum_stats_e += delta_e / delta_d
        sum_stats_g += delta_g / delta_d
        sum_stats_w += delta_w / delta_d
        
        sum_stats_sqr_d += delta_d ** 2
        sum_stats_sqr_e += (delta_e / delta_d) ** 2
        sum_stats_sqr_g += (delta_g / delta_d) ** 2
        sum_stats_sqr_w += (delta_w / delta_d) ** 2
    
    # ------------------------------------------------------------------------------------------------------------------------------------------
    # mean and deviation are meassured in respect to the change of value per day
    # since we meassure a "derivative" we "loose" one data point and thus need to reduce our number of points by one ( similar to z-Transform )
    # ------------------------------------------------------------------------------------------------------------------------------------------
    
    mean_d = sum_stats_d / ( amount_points - 1 )
    mean_e = sum_stats_e / ( amount_points - 1 )
    mean_g = sum_stats_g / ( amount_points - 1 )
    mean_w = sum_stats_w / ( amount_points - 1 )
    
    deviation_d = deviation_e = deviation_g = deviation_w = -1
    if amount_points > 2:
        deviation_d = sqrt( ( sum_stats_sqr_d - ( amount_points - 1 ) * ( mean_d**2 ) ) / ( amount_points - 2 ) )
        deviation_e = sqrt( ( sum_stats_sqr_e - ( amount_points - 1 ) * ( mean_e**2 ) ) / ( amount_points - 2 ) )
        deviation_g = sqrt( ( sum_stats_sqr_g - ( amount_points - 1 ) * ( mean_g**2 ) ) / ( amount_points - 2 ) )
        deviation_w = sqrt( ( sum_stats_sqr_w - ( amount_points - 1 ) * ( mean_w**2 ) ) / ( amount_points - 2 ) )
    
    # adjust each value for gaps (negative delta) in the data points
    total_e += gap_e * mean_e
    total_g += gap_g * mean_g
    total_w += gap_w * mean_w
    
    return (
        amount_points,
        (
            total_d,
            total_e,
            total_g,
            total_w
        ), (
            mean_d,
            mean_e,
            mean_g,
            mean_w 
        ), (
            deviation_d,
            deviation_e,
            deviation_g,
            deviation_w
        ) 
    )

def readings_organize_data_months( data:list[tuple[date, float, float, float]] ) -> dict[int, dict[int, tuple[int, tuple[float, float,float,float], tuple[float, float,float,float], tuple[float, float,float,float]]]]:
    # returns follwing structure: 
    #   dict( 
    #       year, 
    #       dict( 
    #           month, 
    #           tuple( 
    #               amount_points,
    #               tuple(total_d, total_e, total_g, total_w),
    #               tuple(mean_delta_d, per_day_mean_e, per_day_mean_g, per_day_mean_w),
    #               tuple(deviation_delta_d, per_day_deviation_e, per_day_deviation_g, per_day_deviation_w)
    #            )
    #       )
    #   )
    
    # sort all data entries by date (they should allready be ordered correctly, but you never know)
    data = sorted( data, key=lambda d, *_: d )
    
    # get all unique years as a dict
    years = { d.year:{} for d, e, g, w in data }
    
    for year in years.keys():
        # get all unique months of a specific year as a dict
        months = { d.month:[] for d, *_ in data if d.year == year }
        
        # put all entries into their associated month slot
        for d, e, g, w in data:
            months[d.month].append( (d, e, g, w) )
            
        # filter out all months with not enought entries for proper calculations
        months = { k: v for k, v in months.items() if len(v) > 1 }        
        
        for month_id, points in months.items():
            months[month_id] = readings_calculate_statistics( points )

        years[year] |= months
    
    return years

def readings_organize_data_years( data:list[tuple[date, float, float, float]] ) -> dict[int, tuple[int, tuple[float, float,float,float], tuple[float, float,float,float], tuple[float, float,float,float]]]:
    # returns follwing structure:  
    #   dict( 
    #       years, 
    #       tuple( 
    #           amount_points,
    #           tuple(total_d, total_e, total_g, total_w),
    #           tuple(mean_delta_d, per_day_mean_e, per_day_mean_g, per_day_mean_w),
    #           tuple(deviation_delta_d, per_day_deviation_e, per_day_deviation_g, per_day_deviation_w)
    #        )
    #   )
    
    # ------------------------------------------------------------------------------------------------------------------------------------------------------
    # YES! this is more or less the same code as above for the months version
    # It is actually friendlier for readability to NOT make both statistical calulations in one loop, thats why we now do more or less the same loop again
    # ------------------------------------------------------------------------------------------------------------------------------------------------------
    
    # sort all data entries by date (they should allready be ordered correctly, but you never know)
    data = sorted( data, key=lambda d, *_: d )
    
    # get all unique years as a dict
    years = { d.year:{} for d, e, g, w in data }
    
    for year_id in years.keys():
        # get all points of this year
        points = list( filter( lambda param: param[0].year == year_id, data ) )

        years[year_id] = readings_calculate_statistics( points )
    
    return years

def readings_tabulate_data(
    year_months:dict[int, dict[int, tuple[int, tuple[float, float,float,float], tuple[float, float,float,float]]]],
    year_stats:dict[int, tuple[int, tuple[float, float,float,float], tuple[float, float,float,float]]],
    tablefmt="grid" ) -> str:
    
    # table calculates extrapolated consumptions per month, per Day per Month and per Week per month
    # +--------------------------+--------------------------+--------------------------+--------------------------+
    # | Monat                    |          Strom           |           Gas            |          Wasser          |
    # | Zeitspanne   Anz. Eintr. | Extrapolierter Verbrauch | Extrapolierter Verbrauch | Extrapolierter Verbrauch |
    # | Ablesungen               |   pro Tag    pro Woche   |   pro Tag    pro Woche   |   pro Tag    pro Woche   |
    # | Tage bis Abls.|std. Abw. | Standardabweichung p.Tag | Standardabweichung p.Tag | Standardabweichung p.Tag | 
    # +==========================+==========================+==========================+==========================+
    
    table_data = []
    
    # get the maximum width of each columns header
    column_widths = [ len( max( lines.splitlines(), key=lambda x: len(x) ) ) for lines in TABLE_HEADER_READINGS_MONTHS ]
    
    
    for year, months in year_months.items():
        for month_id, (
            amount_points, (
                total_d,
                total_e,
                total_g,
                total_w
            ), (
                mean_d,
                mean_e,
                mean_g,
                mean_w 
            ), (
                deviation_d,
                deviation_e,
                deviation_g,
                deviation_w
            )
        ) in months.items():
            
            if month_id == 12:
                next_month_date = date(year+1, 1, 1)
            else:
                next_month_date = date(year, month_id+1, 1)
                
            days_in_month = ( next_month_date - date(year, month_id, 1)).days
            
            delta_days = days_in_month - total_d
            
            # month entry
            table_data.append( [
                date(year, month_id, 1).strftime( "%Y : %B" ) +NL+ \
                    f" {total_d:>3d} Tage" + (" {:>%dd}" % (column_widths[0] - 9 - 1)).format(amount_points) +NL+ \
                    ( " {:s}{:>%ds}" % (column_widths[0] - 1 - (DIGIT_LAYOUT_DELTA[0]+DIGIT_LAYOUT_DELTA[1]) - 2) ).format( format_decimal( mean_d, DIGIT_LAYOUT_DELTA ), format_decimal( deviation_d, DIGIT_LAYOUT_DELTA ) ),
                "{:s}\n{:s}     {:s}\n{:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( (*extrapolate_meanOut_data( total_e, mean_e, delta_days ), deviation_e), [DIGIT_LAYOUT_ELECTRICITY]+[DIGIT_LAYOUT_DELTA]*4 ) ] ),
                "{:s}\n{:s}     {:s}\n{:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( (*extrapolate_meanOut_data( total_g, mean_g, delta_days ), deviation_g), [DIGIT_LAYOUT_GAS]        +[DIGIT_LAYOUT_DELTA]*4 ) ] ),
                "{:s}\n{:s}     {:s}\n{:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( (*extrapolate_meanOut_data( total_w, mean_w, delta_days ), deviation_w), [DIGIT_LAYOUT_WATER]      +[DIGIT_LAYOUT_DELTA]*4 ) ] )
            ] )
    
    table_data.append( [ "- "*(column_widths[i]//2) for i in range(len(TABLE_HEADER_READINGS_MONTHS)) ] )
    
    for year_id, (
        amount_points, (
            total_d,
            total_e,
            total_g,
            total_w
        ), (
            mean_d,
            mean_e,
            mean_g,
            mean_w 
        ), (
            deviation_d,
            deviation_e,
            deviation_g,
            deviation_w
        )
    ) in year_stats.items():
        
        if month_id == 12:
            next_month_date = date(year+1, 1, 1)
        else:
            next_month_date = date(year, month_id+1, 1)
            
        days_in_year = 366 if isleap( year_id ) else 365
        
        delta_days = days_in_year - total_d
        
        table_data.append( [
            ( "%d : {:>%ds}" % (year, column_widths[0] - 4 - 3) ).format('Jahreswerte') +NL+ \
                f" {total_d:>3d} Tage" + (" {:>%dd}" % (column_widths[0] - 9 - 1)).format(amount_points) +NL+ \
                ( " {:s}{:>%ds}" % (column_widths[0] - 1 - (DIGIT_LAYOUT_DELTA[0]+DIGIT_LAYOUT_DELTA[1]) - 2) ).format( format_decimal( mean_d, DIGIT_LAYOUT_DELTA ), format_decimal( deviation_d, DIGIT_LAYOUT_DELTA ) ),
            "{:s}\n{:s}     {:s}\n{:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( (*extrapolate_meanOut_data( total_e, mean_e, delta_days ), deviation_e), [DIGIT_LAYOUT_ELECTRICITY]+[DIGIT_LAYOUT_DELTA]*3 ) ] ),
            "{:s}\n{:s}     {:s}\n{:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( (*extrapolate_meanOut_data( total_g, mean_g, delta_days ), deviation_g), [DIGIT_LAYOUT_GAS]        +[DIGIT_LAYOUT_DELTA]*3 ) ] ),
            "{:s}\n{:s}     {:s}\n{:s}".format( *[ format_decimal( val, digits ) for val, digits in zip( (*extrapolate_meanOut_data( total_w, mean_w, delta_days ), deviation_w), [DIGIT_LAYOUT_WATER]      +[DIGIT_LAYOUT_DELTA]*3 ) ] )
        ] )
        
    
    if not year_months: # Database has no entries
        table_data = [["no data"]*len(TABLE_HEADER_READINGS_MONTHS)]
    
    return tabulate(
        table_data,
        headers=TABLE_HEADER_READINGS_MONTHS,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('left', 'center', 'center', 'center')
    )
    
    
def get_tabular_reading_stats( data:list[tuple[date, float, float, float]], tablefmt="grid" ) -> str:
    year_months = readings_organize_data_months( data )
    year_stats = readings_organize_data_years( data )
    
    return readings_tabulate_data( year_months, year_stats, tablefmt="grid" )


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
    
    option:str = input("Action auswählen: ").strip().lower()
    
    if not option.isdigit():
        return
    
    option = int( option ) - 1
    
    if not ( 0 <= option < len(MENU_OPTIONS) ):
        return
    
    cls()
    
    MENU_OPTIONS[option]()
    
    user_to_menu_prompt()

def main() -> None:
    os.system("@echo off")
    set_title_and_icon(APP_NAME, PATH_ICON.as_posix())
    cls()
        
    try:
        while True:
            loop()
    except KeyboardInterrupt as e:
        cls()
        print( TITLE )
        print( " Erfolgreich geschlossen ", NL )
    finally:
        os.system("@echo on")


if __name__ == '__main__':
    main()