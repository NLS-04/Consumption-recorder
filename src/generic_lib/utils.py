from __future__ import annotations

from enum        import Enum, auto
from typing      import NamedTuple, TypeVar, Generic, Iterable

from datetime import date, timedelta
from math     import floor

from colors import ansilen

T = TypeVar("T")


digit_layout_t = NamedTuple( "digit_layout_t", [("pre_point", int), ("post_point", int)] )
stats_t = NamedTuple( "stats_t", [("mean", float), ("median", T), ("variance", float)] )

#-----------#
#  generic  #
#-----------#

def prod( iterable:Iterable[T], /, start:int=0 ) -> T:
    """
    calculate the product of the elements of the `iterable` starting
    at the index `start`

    Args:
        iterable (`Iterable[T]`): sequence of elements their product is to be calculated
        start (`int`, optional): start index of the iterable. Defaults to 0.

    Returns:
        `T`: product of the iterable
    """
    out = 1.0
    for x in iterable[start:]:
        out *= x
    return out

def digit_layout_to_format_specifier( digit_layout:digit_layout_t ) -> str:
    """
    get the string format specifier for the float format of the supplied digit layout

    can be used in format strings to format float to the specified digit layout
    
    Example:
    >>> digit_layout_to_format_specifier( digit_layout_t(2,5) )
    >>> "7.5f"

    Args:
        digit_layout (`digit_layout_t`): (count of pre decimal digits, count of post decimal digits)

    Returns:
        `str`: format specifier
    """
    return f"{digit_layout.pre_point+digit_layout.post_point+1}.{digit_layout.post_point}f"


#-----------------------#
#  string manipulation  #
#-----------------------#

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
    
    res: str = max( list_of_str, key=ansilen )
    
    return res, ansilen(res)

def replace_substring( string_to_be_overwritten:str, at_index:int, substring:str ) -> str:
    # will not work with colorized strings
    assert 0 <= at_index, "at_index must be non negative"
    assert at_index < len(string_to_be_overwritten) - len(substring), "substring does not fit at the supplied index"
    
    return string_to_be_overwritten[:at_index] + substring + string_to_be_overwritten[at_index+len(substring):]


#--------------#
#  statistics  #
#--------------#

def simple_statistics( data:list[T] ) -> stats_t[T]:
    N = len(data)
    
    if N == 0:
        return stats_t( 0, 0, 0 )
    
    return stats_t(
        mean   := sum( data ) / N,
        median := data[ N//2 ] if N % 2 == 1 else 0.5*(data[ N//2-1 ] + data[ N//2 ]),
        var    := sum( map( lambda x: (x-mean)**2, data) ) / N
    )
def geometric_mean( data:Iterable[T] ) -> T:
    if len(data) == 0:
        return 1
    
    return prod( data ) ** (1/len(data))


#------------------------#
#  Intersection & Dates  #
#------------------------#

def end_of_month_date( _date: date ) -> date:
    return (date( _date.year, _date.month+1, 1 ) if _date.month < 12 else date( _date.year+1, 1, 1 )) - timedelta( days=1 )

class Intersection(Enum):
    """
    Type of intersection between to ranges etc.

    For two ranges A and B and (the pseudocall) `A.intersect(B)`: 
    The returned intersection type is always read left to right i.e. `A <relative to> B`.
    
    meaning that the type:
    - `Intersection.SUB_SET` <=> A is SUB_SET of B;
    
    and vice-versa
    - `Intersection.SUPER_SET` <=> A is SUPER_SET of B
    """
    
    DISJOINT  = 0
    EQUAL     = 1
    SUB_SET   = 2
    SUPER_SET = 3
    
    PARTIAL_OVERLAP_LEFT  = 4
    PARTIAL_OVERLAP_RIGHT = 5

div_t      = NamedTuple("div_t",       [("quotient", int), ("remainder", int)])
calender_t = NamedTuple( "calender_t", [("days", int), ("months", int), ("years", int)] )
class Dates_Delta:
    DAYS_IN_YEAR : float = 365.25
    DAYS_IN_MONTH: float = DAYS_IN_YEAR / 12.0
    
    date_low : date
    date_high: date
    
    days  : int
    months: float
    years : float
    
    as_months_days: div_t

    as_years_days       : div_t
    as_years_months     : div_t
    as_years_months_days: calender_t
    
    
    def __init__(self, date_low: date, date_high: date) -> None:
        self.date_low  = date_low
        self.date_high = date_high
        
        self.days = (self.date_high - self.date_low).days

        self.months         = self.days_to_months( self.days )
        self.as_months_days = self.days_to_months_days( self.days )

        self.years                = self.days_to_years( self.days )
        self.as_years_days        = self.days_to_years_days( self.days )
        self.as_years_months      = self.days_to_years_months( self.days )
        self.as_years_months_days = self.days_to_years_months_days( self.days )
    
    def intersect( self, date_range: Dates_Delta ) -> Intersection:
        if date_range.date_low == self.date_low and date_range.date_high == self.date_high:
            return Intersection.EQUAL
        
        if date_range.date_low < self.date_low:
            # possible intersection => SUB_SET or DISJOINT or PARTIAL_LEFT
            
            if date_range.date_high < self.date_low:
                return Intersection.DISJOINT
            
            if date_range.date_high >= self.date_high:
                return Intersection.SUB_SET
            
            return Intersection.PARTIAL_OVERLAP_LEFT
            
        else: # date_range.date_low >= self.date_low
            # possible intersection => SUPER_SET or DISJOINT or PARTIAL_RIGHT or EQUAL
            
            if date_range.date_low > self.date_high:
                return Intersection.DISJOINT
            
            if date_range.date_high > self.date_high:
                return Intersection.PARTIAL_OVERLAP_RIGHT
            
            return Intersection.SUPER_SET

    
    def is_in_delta( self, date_to_check:date ) -> int:
        """
        check whether a date is inside, earlier or later than this date_delta

        Args:
            date_to_check (`date`): date to check against this date_delta

        Returns:
            - `-1` => date is earlier than the delta
            - ` 0` => date is in between the delta
            - `+1` => date is later than the delta
        """

        if date_to_check < self.date_low:
            return -1
        
        if date_to_check > self.date_high:
            return 1
        
        return 0
    
    
    @classmethod
    def days_to_months( cls, days: int ) -> float:
        return days / cls.DAYS_IN_MONTH
    @classmethod
    def days_to_months_days( cls, days: int ) -> div_t:
        return cls.__int_divmod( days, cls.DAYS_IN_MONTH )
    
    @classmethod
    def days_to_years( cls, days: int ) -> float:
        return days / cls.DAYS_IN_YEAR
    @classmethod
    def days_to_years_days( cls, days: int ) -> div_t:
        return cls.__int_divmod( days, cls.DAYS_IN_YEAR )
    @classmethod
    def days_to_years_months( cls, days: int ) -> div_t:
        years , ydays = cls.days_to_years_days( days )
        months = round( cls.days_to_months( ydays ) )
        
        return div_t( years, months )
    @classmethod
    def days_to_years_months_days( cls, days: int ) -> calender_t:
        years , ydays = cls.days_to_years_days( days )
        months, mdays = cls.days_to_months_days( ydays )
        
        return calender_t( mdays, months, years )
    
    def __str__(self) -> str:
        return f"DD( {str(self.date_low)}, {str(self.date_high)} )"
    
    @staticmethod
    def __to_int( *args ) -> list[int]:
        return [ int(x) for x in args ]
    @staticmethod
    def __int_divmod( x, y ) -> div_t:
        return div_t( *[ int(v) for v in divmod( x, y ) ] )


#-----------------#
#  Serialization  #
#-----------------#

def stringify( _l:list[str], / ) -> str:
    """serialize data  to a string, i.e. creating a string of the supplied data"""
    return ''.join( _l )

def str_to_date( data_str:list[str] ) -> date:
    return date.fromisoformat( '-'.join( [ stringify(data_str[4:8]), stringify(data_str[2:4]), stringify(data_str[0:2]) ] ) )

def float_to_data_format( value:float, digit_count:digit_layout_t) -> list[str]:
    """
    convert a float into a list of chrs respecting the digit layout
    
    values outside of the printable (digit) range are clamped to the associate max/min value

    Example:
    >>> float_to_data_format( 3.14159, digit_layout_t(2,2) )
    >>> ['', '3', '1', '4']
    >>> float_to_data_format( -3.14159, digit_layout_t(2,2) )
    >>> ['-', '3', '1', '4']

    >>> float_to_data_format( 123.456, digit_layout_t(2,2) )
    >>> ['9', '9', '9', '9']
    >>> float_to_data_format( -123.456, digit_layout_t(2,2) )
    >>> ['-', '9', '9', '9']

    Args:
        value (`float`): float value to be converted
        digit_layout (`digit_layout_t`): (count of pre decimal digits, count of post decimal digits)

    Returns:
        `list[str]`: list of the float chr representation
    """
   
    max_val =  10**( digit_count.pre_point   ) - 10**-digit_count.post_point
    min_val = -10**( digit_count.pre_point-1 ) + 10**-digit_count.post_point
    
    clamped_val = max( min_val, min( round( value, digit_count.post_point ), max_val ) )
    
    chrs = list( f"{{:_>{digit_layout_to_format_specifier( digit_count )}}}".format( clamped_val ) )
    
    return [ ('' if c == '_' else c) for c in chrs if c != '.' ]


if __name__ == "__main__":
    print( max_width_of_strings( ["alpha", "beta", "a", "123456789"] ) )
    print( float_to_data_format(  3.14159, digit_layout_t(2,2) ) )
    print( float_to_data_format( -123.456, digit_layout_t(2,2)) )
    print( float_to_data_format(  0.0456 , digit_layout_t(2,2)) )
    print( float_to_data_format( -0.0456 , digit_layout_t(2,2)) )
    print( float_to_data_format(  1.0    , digit_layout_t(2,2)) )