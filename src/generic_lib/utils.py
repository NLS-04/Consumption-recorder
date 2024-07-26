from datetime import date
from math     import floor


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
        - [1] is the length of [0]; 
        - Will return (None, 0) iff `list_of_strings` is empty, i.e. equates to false
    """
    if not list_of_str:
        return None, 0
    
    res: str = max( list_of_str, key=len )
    
    return res, len(res)


#-----------------#
#  Serialization  #
#-----------------#

def stringify( _l:list[str], / ) -> str:
    """serialize data  to a string, i.e. creating a string of the supplied data"""
    return ''.join( _l )

def str_to_date( data_str:list[str] ) -> date:
    return date.fromisoformat( '-'.join( [ stringify(data_str[4:8]), stringify(data_str[2:4]), stringify(data_str[0:2]) ] ) )

def float_to_data_format( value:float, digit_count:tuple[int, int]) -> list[str]:
    format_str = "{:_>%ds}{:0<%ds}" % (digit_count[0], digit_count[1])
    digits     = ( str( floor(value) ), str( round( value - floor(value), digit_count[1] ) )[2:] )
    
    return [ '' if ch == '_' else ch for ch in format_str.format( *digits ) ]



if __name__ == "__main__":
    print( max_width_of_strings( ["alpha", "beta", "a", "123456789"] ) )