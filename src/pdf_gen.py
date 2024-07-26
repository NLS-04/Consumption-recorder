# helpful docs and guides for reportlab, since i couldn't find any original nice documentation by them
# https://www.reportlab.com/docs/reportlab-reference.pdf
# https://www.reportlab.com/docs/reportlab-userguide.pdf
from reportlab.pdfgen             import canvas
from reportlab.lib.pagesizes      import A4
from reportlab.lib.units          import cm, mm
from reportlab.pdfbase.pdfmetrics import stringWidth

import webbrowser

from math     import floor
from datetime import datetime, date, UTC

from generic_lib.utils import *
from constants import *

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
    canv.drawString( 1*cm, canv._pagesize[1]-2*mm, f"PDF created {datetime.now(UTC).strftime('%x %X')}" )
    
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

def export_to_pdf(
    table_readings_raw  : str,
    table_readings_stats: str,
    table_persons       : str,
    output_path         : Path = PATH_PDF,
    name                : str = "export_%s.pdf" % date.today().strftime("%Y%m%d"),
    ) -> None:
    #todo: better description
    
    TABLE_CONTINUE_STR = '. . .'
    
    # (210mm, 297mm)
    # (595pt, 842pt)
    WIDTH, HEIGHT = A4
    
    file_name = output_path.joinpath( str(name) )
    
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
    
    draw_pdf_page( table_readings_raw, c, WIDTH, HEIGHT, RX, RY, 80, PDF_FONT_TABLE, TABLE_CONTINUE_STR )
    
    # statistics readings
    c.setFont( PDF_FONT_TABLE, 16 )
    c.drawString( RX, RY-20, "Statistiken:" )
    
    draw_pdf_page( table_readings_stats, c, WIDTH, HEIGHT, RX, RY, 0, PDF_FONT_TABLE, TABLE_CONTINUE_STR )

     
      ###########
     # PERSONS #
    ###########
    c.setFont( PDF_FONT_TABLE, 16 )
    c.drawString( RX, RY-20, "Personen:" )
    
    draw_pdf_page( table_persons, c, WIDTH, HEIGHT, RX, RY, 0, PDF_FONT_TABLE, TABLE_CONTINUE_STR )
    
    
    c.save()
    
    webbrowser.open_new( file_name.as_uri() )
