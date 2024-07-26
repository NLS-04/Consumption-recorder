from datetime  import date


from constants import *
import backend_model as model

#------------------------------------#
#  pure standalone helper functions  #
#------------------------------------#

def add_side_note_to_tabular( table:str, side_note:str, row:int ) -> str:
    lines = table.splitlines()
    lines[row] += side_note
    return NL.join( lines )

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


#------------------------------------#
#  specialized formatting functions  #
#------------------------------------#

def __tabulate_data_points( header_row_1: str, frame: model.Frame_statistics, date_column_width:int ) -> list[str]:
    return [
        header_row_1 + NL + 
        readings_format_ddays_stats(
            frame.readings_count,
            frame.days_stats,
            date_column_width
        ) 
    ] + readings_format_values( frame.reading_attributes_stats )

def readings_format_month( year:int, month_data:model.Analyzed_month, date_column_width:int ) -> list[str]:
    """
    format a reading to be appended to a `tabulate` Table of readings statistic

    This function formats a given month statistic for a given year

    Args:
        year (`int`): year to be displayed
        month_data (`model.Organized_month`): statistically analyzed data
        date_column_width (`int`): width of date i.e. 1st column in (printable) characters

    Returns:
        `list[str]`: `tabulate` formatted list of strings
    """
    row1 = date(year, month_data.month, 1).strftime( "%Y : %B" )
    
    return __tabulate_data_points( row1, month_data.points, date_column_width )

def readings_format_year( year:model.Analyzed_year, date_column_width:int ) -> list[str]:
    """
    format a reading to be appended to a `tabulate` Table of readings statistic

    This function formats a given year statistic

    Args:
        year (`model.Analyzed_year`): statistically analyzed data
        date_column_width (`int`): width of date i.e. 1st column in (printable) characters

    Returns:
        `list[str]`: `tabulate` formatted list of strings
    """
    row1 = ( "%d : {:>%ds}" % (year.year, date_column_width - 4 - 3) ).format('Jahreswerte')
    
    return __tabulate_data_points( row1, year.points, date_column_width )

def readings_format_span( point:model.Frame_statistics, date_column_width:int ) -> list[str]:
    """
    format a reading to be appended to a `tabulate` Table of readings statistic

    This function formats a given analyzed point (usually statistics of an user specified time span )

    Args:
        point (`model.Frame_statistics`): statistically analyzed data
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
    
    return __tabulate_data_points( row1, point, date_column_width )


def readings_format_ddays_stats( amount_points:int, days_measurement:model.Measurement, date_column_width:int ) -> str:
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
        days_measurement (`model.Measurement`): statistical data of the analyzed reading days
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

def readings_format_values( reading_attributes:list[model.Measurement] ) -> list[str]:
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
