from datetime import date, datetime
from math import floor
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

import msvcrt
import os

from dbHandler import DBSession, PATH_ROOT
from constants import *


SESSION = DBSession()

# from tabulate namespace
PRESERVE_WHITESPACE = True

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
    user_to_menu_prompt()
    
def user_to_menu_prompt():
    input( " --- Eingabe-Taste drücken um in das Menü zurück zukeheren" )
    


def get_date( prefillDateISO:str=date.today().strftime("%d%m%Y"), validRequired:bool=True, prompt_name:str="Datum:" ) -> date or None:
    PLACE_HOLDER = '_'
    
    # data:layout = 'ddmmyyyy'
    #                01234567
    data = ( prefillDateISO + PLACE_HOLDER*8 )[:8] # right padding with place holder chars
    data_ptr = max( 0, len(prefillDateISO) )
    
    console_out = lambda: f"\t{prompt_name} {data[0:2]}.{data[2:4]}.{data[4:8]}" + ' '*30
    
    print( console_out(), end='\r' )
    while True:
        key = str(msvcrt.getwch())
        
        if key == '\r': # enter keycode
            if data == PLACE_HOLDER*8 and not validRequired:
                print( console_out().rstrip() + "\t - REGISTERED EMPTY ENTRY", end='\r' )
                return None
            
            try:
                return date.fromisoformat( '-'.join([data[4:8], data[2:4], data[0:2]]) )
            except ValueError:
                print( console_out().rstrip() + "\t - INVALID ENTRY", end='\r' )
        else:
            if key == '\b': # backspace keycode
                data_ptr = max(0, data_ptr-1)
                data = data[:data_ptr] + PLACE_HOLDER + data[data_ptr+1:]
                
            if key.isdigit():
                data = data[:data_ptr] + key + data[data_ptr+1:]
                data_ptr = min( data_ptr+1, 8 )
            
            print( console_out(), end='\r' )

def get_general( title:str, digit_count:tuple[int, int] ):
    PLACE_HOLDER = '_'
    
    data = PLACE_HOLDER*(digit_count[0]+digit_count[1])
    
    console_out = lambda: f"\t{title} {data[0:digit_count[0]]}.{data[digit_count[0]:]}" + ' '*30
    
    print( console_out(), end='\r' )
    while True:        
        key = str(msvcrt.getwch())
        
        if key == '\r': # enter keycode
            try:
                value = float( f"{data[0:digit_count[0]]}.{data[digit_count[0]:]}".replace(PLACE_HOLDER, '0') )
                data = ("{:>%d.%df}" % (digit_count[0]+digit_count[1]+1, digit_count[1])).format( value ).replace('.', '')
                print( console_out(), end='\r' )
                return value
            except ValueError as e:
                pass
                
            print( console_out().rstrip() + "\t - INVALID ENTRY", end='\r' )
        else:
            if key == '\b': # backspace keycode
                data = PLACE_HOLDER + data[:len(data)-1]
                
            if key.isdigit():
                if data[0] == PLACE_HOLDER:
                    data = data[1:] + key
                    
            print( console_out(), end='\r' )


def visualize_readings():
    print( " --- ABLESUNGEN AUSGEBEN --- ", NL )
    
    data = SESSION.get_reading_all()
    
    table = get_tabular_reading_detail( data )
    
    print( table, NL )
    
    user_to_menu_prompt()

def visualize_persons():
    print( " --- PERSONEN AUSGEBEN --- ", NL )
    
    data = SESSION.get_person_all()
    
    table = get_tabular_person_detail( data )
    
    print( table, NL )
    
    user_to_menu_prompt()


def manipulate_readings():
    print( " --- ABLESUNG HINZUFÜGEN / ÜBERSCHREIBEN --- ", NL )
    #todo: better description
    
    d = get_date();                                         print()
    e = get_general("Strom: ", DIGIT_LAYOUT_ELECTRICITY);   print()
    g = get_general("Gas:   ", DIGIT_LAYOUT_GAS);           print()
    w = get_general("Wasser:", DIGIT_LAYOUT_WATER);         print()
    
    exists, data = SESSION.exists_readings( d, d )
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
    
    print( NL, "Ablesung erstellt und in der Datenbank eingetragen", NL )
    user_to_menu_prompt()

def manipulate_persons():
    print( " --- PERSON HINZUFÜGEN / ÜBERSCHREIBEN --- ", NL )
    #todo: better description
    
    while True:
        nameID = input( "\tName:  " ).strip().lower()
        
        if not nameID:
            print( "Ungültiger Name, bitte anderen Namen wählen: ", NL )
            continue
        
        break
    
    exists, data = SESSION.exists_person( nameID )
    
    d1, d2 = None, None
    
    if exists:
        try: d1 = data[1].strftime("%d%m%Y")
        except (AttributeError, IndexError): pass
        
        try: d2 = data[2].strftime("%d%m%Y")
        except (AttributeError, IndexError): pass
    
    move_in  = get_date( d1 if d1 else "", False ); print()
    move_out = get_date( d2 if d2 else "", False ); print()
    
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
    
    print( NL, "Person in die Datenbank eingetragen", NL )
    user_to_menu_prompt()


def delete_reading():
    print( " --- ABLESUNG ENTFERNEN --- ", NL )
    
    # sub menu management
    tab = tabulate( [
        [ "1)", "Einen Eintrag entfernen" ],
        [ "2)", "Mehrere Einträge entfernen" ],
        SEPARATING_LINE,
        [ "3-9)", "Zum Menü zurück kehren" ],
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
            user_to_menu_prompt()
        
        print( add_side_note_to_tabular( get_tabular_reading_simple( data ), " <-- Entfernen ", -2 ), NL )
        
        decision:str = input( "Wollen Sie diesen Eintrag entfernen [Y/N]: " )
        
        if not decision in ["Y", "y"]: # User declined to override
            print()
            user_decline_prompt()
            return
    
        SESSION.remove_readings( d, d )
        
        print( NL, "Eintrag aus der Datenbank entfernt", NL )
        
    if option == 2: # removing multiple entries
        print( "Daten für Zeitinterval der zu entfernenden Einträge eingeben", NL )
        d_from = get_date( "", True, "Datum ab: " ); print()
        d_till = get_date( "", True, "Datum bis:" ); print()

        exists, data = SESSION.exists_readings( d_from, d_till )
        sleep(KEYBOARD_SLEEP_TIME)
        print()
        
        if not exists:
            print( f"Keine Einträge gefunden im Zeitraum: {d_from.strftime( DATE_STR_FORMAT )} - {d_till.strftime( DATE_STR_FORMAT )}", NL )
            user_to_menu_prompt()
        
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
        
        print( NL, "Einträge aus der Datenbank entfernt", NL, sep='' )
        
    user_to_menu_prompt()

def delete_person():
    print( " --- PERSON ENTFERNEN --- ", NL )
    
    print( "Name des zu entfernenden Eintrags eingeben", NL )
    
    while True:
        nameID = input( "\tName:  " ).strip().lower()
        
        if not nameID:
            print( "Ungültiger Name, bitte anderen Namen wählen: ", NL )
            continue
        
        break
    
    exists, data = SESSION.exists_person( nameID )
    sleep(KEYBOARD_SLEEP_TIME)
    print()
    
    if not exists:
        print( f"Kein Eintrag gefunden mit dem Namen: {nameID}", NL )
        user_to_menu_prompt()
        return
    
    print( add_side_note_to_tabular( get_tabular_person_simple( [data] ), " <-- Entfernen ", -2 ), NL )
    
    decision:str = input( "Wollen Sie diesen Eintrag entfernen [Y/N]: " )
    
    if not decision in ["Y", "y"]: # User declined to override
        print()
        user_decline_prompt()
        return

    SESSION.remove_person( nameID )
    
    print( NL, "Eintrag aus der Datenbank entfernt", NL, sep='' )
    user_to_menu_prompt()


def do_invoice():
    print( " --- ABRECHNUNG DURCHFÜHREN --- ", NL )
    print( "INOP" )
    
    user_to_menu_prompt()

def export_to_pdf():
    print( " --- PROTOKOLL EXPORTIEREN - PDF --- ", NL )
    
    exportName = "export_%s.pdf" % date.today().strftime("%Y%m%d")
    
    # (210mm, 297mm)
    # (595pt, 842pt)
    WIDTH, HEIGHT = A4
    
    file_name = user_documents_path().joinpath( exportName )
    
    file_name.unlink(True)
    file_pdf = file_name.open("xb")
    
    c = canvas.Canvas( file_pdf, A4, 0 )
    
    # TITLE
    c.setFont( PDF_FONT_TITLE, 20 )
    c.drawCentredString( WIDTH/2, 50, "Verbrauchsprotokollator" )
    c.drawCentredString( WIDTH/2, 70, "Übersicht vom %s" % date.today().strftime( DATE_STR_FORMAT ) )
    c.line( 100, 80, WIDTH-100, 80 )
    c.line( 100, 82, WIDTH-100, 82 )
    
    # READINGS
    c.setFont( PDF_FONT_TABLE, 16 )
    c.drawString( 50, 120, "Ablesungen:" )
    
    TABLE_CONTINUE_STR = '. . .'
    RX, RY, OFFSET_RY_PAGE1 = 50, 50, 130
    
    # draw table over pages
    data = SESSION.get_reading_all()
    table = get_tabular_reading_detail( data )
    
    
    RW, RH = WIDTH-2*RX, HEIGHT-OFFSET_RY_PAGE1-RX
     
    FONT_SIZE = find_fitting_fontsize( len( table.splitlines()[0] ), RW )
    
    ROWS = floor( RH / FONT_SIZE )
    ENTRIES_PER_PAGE = floor( (ROWS-1-1) / 3 ) # (ROWS - LINE_UPPER_SEPARATOR - SPACE_BOTTOM) / LINES_PER_ENTRY
    
    textObj = c.beginText( RX, OFFSET_RY_PAGE1 )
    textObj.setFont( PDF_FONT_TABLE, FONT_SIZE, FONT_SIZE )
    
    lines_idx = 0
    for line in table.splitlines():
        if lines_idx == 3 * ENTRIES_PER_PAGE:     # ENTRIES_PER_PAGE = 3 * REQUIRED_LINES_PER_PAGE
            lines_idx = 0
            
            RH = HEIGHT-RY-RX 
            ROWS = floor( RH / FONT_SIZE )
            ENTRIES_PER_PAGE = floor( (ROWS-1-1) / 3 )
            
            textObj.moveCursor( ( RW - FONT_SIZE*len(TABLE_CONTINUE_STR) )//2, 0 )
            textObj.textOut( TABLE_CONTINUE_STR )
            
            c.drawText( textObj )
            
            # finalize this page and initiate new page
            add_info_pdf_page(c)
            c.showPage()
            
            
            textObj = c.beginText( RX, RY )
            textObj.setFont( PDF_FONT_TABLE, FONT_SIZE, FONT_SIZE )
            
        lines_idx+=1
        textObj.textLine(line)
        
    c.drawText( textObj )

    # finalize this page and initiate new page
    add_info_pdf_page(c)
    c.showPage()
    
    # PERSONS
    c.setFont( PDF_FONT_TABLE, 16 )
    c.drawString( 50, 30, "Personen:" )
    
    data = SESSION.get_person_all()
    table = get_tabular_person_detail( data )
    
    RX, RY = 50, 50
    RW, RH = WIDTH-2*RX, HEIGHT-RY-RX
    
    FONT_SIZE = find_fitting_fontsize( len( table.splitlines()[0] ), RW )
    ROWS = floor( RH / FONT_SIZE )
    
    textObj = c.beginText( RX, RY )
    textObj.setFont( PDF_FONT_TABLE, FONT_SIZE, FONT_SIZE )
    
    
    lines_idx = 0
    for line in table.splitlines():
        if lines_idx == ROWS:
            lines_idx = 0
            
            textObj.moveCursor( ( RW - FONT_SIZE*len( TABLE_CONTINUE_STR ) )//2, 0 )
            textObj.textOut( TABLE_CONTINUE_STR )
            
            c.drawText( textObj )
            
            # finalize this page and initiate new page
            add_info_pdf_page(c)
            c.showPage()
            
            textObj = c.beginText( RX, RY )
            textObj.setFont( PDF_FONT_TABLE, FONT_SIZE, FONT_SIZE )
            
        lines_idx+=1
        textObj.textLine(line)
        
    c.drawText( textObj )
    
    # finalize this page and initiate new page
    add_info_pdf_page(c)
    c.showPage()
    
    
    c.save()
    
    print( '\t', f"Protokoll am {date.today().strftime( DATE_STR_FORMAT )} über alle Werte wurde erstellt" )
    print( '\t', f"und als \"{exportName}\" in Ihrem Dokumenten-Ordner \"{user_documents_path()}\" gespeichert", NL )
    
    user_to_menu_prompt()



def format_decimal( value:float, digit_layout:tuple[int, int], alignement_format:str='>', format_size:int=None ) -> str:
    # to clamp the value to the specified digit_layout: abs_max = 10**digit_layout[0] - 10**(-digit_layout[1])
    # 
    # example:
    # >>> digit_layout = (2,3)
    # abs_max = 10**digit_layout[0] - 10**(-digit_layout[1]) = 100 - 0.001 = 99.999
    
    # sum(digit_layout) + 1 + 1
    # ^^^                 ^   ^
    # number of digits   '.' '-' or ' '
    
    abs_max = 10**digit_layout[0] - 10**(-digit_layout[1])
    formated_digits = ( "{: >%d.%df}" % ( sum(digit_layout) + 1 + 1, digit_layout[1] ) ).format( max( -abs_max, min( value, abs_max ) ) )
    
    if not format_size:
        return formated_digits
    
    return ( "{:%s%ds}" % ( alignement_format, format_size ) ).format( formated_digits )
        

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
        disable_numparse=False,
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
            d.strftime( DATE_STR_FORMAT ) + NL + f"    Tage:{delta_d:>3d}",
            #todo: make aligne first row
            format_decimal( e, DIGIT_LAYOUT_ELECTRICITY ) +NL+ format_decimal( delta_e/delta_d if delta_d else 0, DIGIT_LAYOUT_DELTA ) +" "+ format_decimal( delta_e, DIGIT_LAYOUT_ELECTRICITY ),
            format_decimal( g, DIGIT_LAYOUT_GAS         ) +NL+ format_decimal( delta_g/delta_d if delta_d else 0, DIGIT_LAYOUT_DELTA ) +" "+ format_decimal( delta_g, DIGIT_LAYOUT_GAS ),
            format_decimal( w, DIGIT_LAYOUT_WATER       ) +NL+ format_decimal( delta_w/delta_d if delta_d else 0, DIGIT_LAYOUT_DELTA ) +" "+ format_decimal( delta_w, DIGIT_LAYOUT_WATER ),
        ])
    
    # return tabulate( table_data, headers=TABLE_HEADER_READINGS_DETAIL, tablefmt=tablefmt, disable_numparse=True, colalign=('left', 'decimal', 'decimal', 'decimal') )
    return tabulate(
        table_data,
        headers=TABLE_HEADER_READINGS_DETAIL,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('left', 'center', 'center', 'center')
    )

def get_tabular_person_detail( data:list[tuple[str, date, date]], tablefmt="grid" ) -> str:
    table_data = []
    
    for i, (n, din, dout) in enumerate( data ):
        effective_months_str = None
        invoices = None
        
        if din:
            artifical_dout = (dout if dout else date.today())
            delta = artifical_dout - din
            effective_months_str = str( round( delta.days / 30 ) )
            effective_months_str += NL + din.strftime("%b%y") + ' - ' + artifical_dout.strftime("%b%y")
            invoices = NL.join( [ str(year) for year in range(din.year, artifical_dout.year+1, 1) ] )
        
        table_data.append( [
            n,
            din.strftime(  DATE_STR_FORMAT ) if din  else None,
            dout.strftime( DATE_STR_FORMAT ) if dout else None,
            effective_months_str,
            invoices
        ])
    
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
    canv.drawString( 1*cm, canv._pagesize[1]-2*mm, f"PDF created {datetime.utcnow().strftime('%Y-%m-%m %H:%M:%S')}" )
    
    canv.setFont( f, fs, lead )
    
def perform_debug() -> None:
    #! highly dangerous should be removed on distribution !!!!
    
    cls()
    os.system("@echo on")
    
    print( PATH_ROOT )
    print( PATH_ROOT.absolute() )
    print( "console:" )
    
    while True:
        inputStr = input()
        
        if inputStr.strip().lower() == "exit":
            break
        
        os.system( inputStr )
        
    os.system("@echo off")


MENU_OPTIONS = [
    visualize_readings,
    visualize_persons,
    manipulate_readings,
    manipulate_persons,
    delete_reading,
    delete_person,
    do_invoice,
    export_to_pdf,
]

def loop():
    flush_menu()
    
    option:str = input("Action auswählen: ").strip().lower()
    
    if option == "-d":
        perform_debug()
        return
    
    if not option.isdigit():
        return
    
    option = int( option ) - 1
    
    if not ( 0 <= option < len(MENU_OPTIONS) ):
        return
    
    print()
    
    MENU_OPTIONS[option]()

def main() -> None:
    os.system("@echo off")
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