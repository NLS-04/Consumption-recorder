from typing    import Callable
from tabulate  import tabulate, PRESERVE_WHITESPACE
from datetime  import date

from constants         import *
from generic_lib.utils import *

import dbWrapper     as db
import formatter     as fmt
import backend_model as model

# from tabulate namespace
PRESERVE_WHITESPACE = True



class TX_func_factory():
    @staticmethod
    def name_2_dates( get_move_out:bool ) -> Callable[ [list[str]], tuple[bool, list[str]] ]:
        def f( name:list[str] ) -> tuple[bool, list[str]]:
            exists, data = db.exist_person( stringify(name) )
            person = data[0] if exists else db.Person( None, None, None )
            
            # raw date size
            res = [''] * 8
            
            if not get_move_out:
                _date = person.move_in
            else:
                _date = person.move_out
            
            if _date:
                res = list( _date.strftime("%d%m%Y") )
            
            return exists, res
        return f
    
    @staticmethod
    def date_2_value( index_reading_attribute:int ) -> Callable[ [list[str]], tuple[bool, list[str]] ]:
        assert 0 <= index_reading_attribute < len(LIST_DIGIT_OBJ_LAYOUTS), f"supplied return_index must be greater or equal to 0 and less than {len(LIST_DIGIT_OBJ_LAYOUTS)}(the amount of value_objects)"
        
        def f( date_:list[str] ) -> tuple[bool, list[str]]:
            res = [''] * sum( LIST_DIGIT_OBJ_LAYOUTS[index_reading_attribute] )
            try:
                d = str_to_date( date_ )
                
                exists, data = db.exist_reading( d )
                val = data[0].attributes[index_reading_attribute] if exists else None
                
                if val:
                    res = float_to_data_format( val, LIST_DIGIT_OBJ_LAYOUTS[index_reading_attribute] )
                
                return exists, res
            except ValueError:
                return False, res
        return f


#--------------------#
# TABULATE - PERSONS #
#--------------------#
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

def get_tabular_person_simple( persons:list[ db.Person ], tablefmt="psql" ) -> str:
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
        persons (`list[ db.Person ]`): list of persons to be tabulated
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "psql".

    Returns:
        `str`: string of table
    """
    persons = [ [p.name, p.move_in, p.move_out] for p in persons ]
    return tabulate(
        persons, 
        headers=TABLE_HEADER_PERSONS_SIMPLE, 
        tablefmt=tablefmt, 
        colalign=('right', 'center', 'center'), 
        maxcolwidths=[15, None, None, None]
    )

def get_tabular_person_detail( persons:list[ db.Person ], tablefmt="grid" ) -> str:
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
        persons (`list[ db.Person ]`): list of persons to be tabulated
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
def get_tabular_reading_simple( readings:list[ db.Reading ], tablefmt="psql" ) -> str:
    """
    generate simple `tabulate` table of readings

    Args:
        readings (`list[db.Reading]`): list of readings to be tabulated
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "grid".

    Returns:
        `str`: string of table
    """
    readings = [
        [
            r.date.strftime( DATE_STR_FORMAT ),
            *[
                fmt.format_decimal( r.attributes[k], LIST_DIGIT_OBJ_LAYOUTS[k] ) for k in range(COUNT_READING_ATTRIBUTES)
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


def generate_printout_readings_all( readings:list[ db.Reading ], use_years_for_stats_section:bool=True ) -> str:
    """
    generate string of readings to be displayed

    consists of two parts:
    1. Table of each individual readings + statistical information
    2. Table of readings grouped and summarized by [optional](year and) month with additional statistical information

    Args:
        readings (`list[ db.Reading ]`): raw data directly from database
        use_years_for_stats_section (`bool`, optional): if `True` groups readings in `Table 2` by year and months, `False` groups only by months. Defaults to `True`.

    Returns:
        str: Tables of readings formatted to be printed on screen or pdf
    """
    table_raw = generate_printout_readings_detail( readings )
    table_stats = generate_printout_readings_statistics( readings, use_years_for_stats_section )
    
    return ''.join([table_raw, NL, NL, table_stats, NL])

def generate_printout_readings_detail( readings:list[ db.Reading ], tablefmt="grid" ) -> str:
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
        readings (`list[ db.Reading ]`): raw data directly from database
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
            fmt.format_decimal( readings[0].attributes[k], LIST_DIGIT_OBJ_LAYOUTS[k] ) +NL+\
            fmt.format_decimal( None, DIGIT_LAYOUT_DELTA ) +" "+ fmt.format_decimal( None, LIST_DIGIT_OBJ_LAYOUTS[k] )
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
                    fmt.format_decimal( None, LIST_DIGIT_OBJ_LAYOUTS[k] ) +NL+\
                    fmt.format_decimal( None, DIGIT_LAYOUT_DELTA ) +" "+ fmt.format_decimal( None, LIST_DIGIT_OBJ_LAYOUTS[k] )
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
                fmt.format_decimal( r.attributes[k], LIST_DIGIT_OBJ_LAYOUTS[k] ) +NL+\
                fmt.format_decimal( delta[k]/ddays if delta[k] else None, DIGIT_LAYOUT_DELTA ) +" "+ fmt.format_decimal( delta[k], LIST_DIGIT_OBJ_LAYOUTS[k] )
            )
    
    return tabulating( table_data )

def generate_printout_readings_statistics( readings:list[ db.Reading ], use_years_for_stats_section:bool=True, tablefmt="grid" ) -> str:
    """
    generate string of table of readings grouped and summarized by [optional](years and) months

    --- 
    #### Table layout will be according to the layout found in `readings_tabulate_data(...)`
    
    ---
    Args:
        readings (`list[ db.Reading ]`): raw data directly from database
        use_years_for_stats_section (`bool`, optional): if `True` groups readings in `Table 2` by year and months, `False` groups only by months. Defaults to `True`.
        tablefmt (`str`, optional): table format to be used by the `tabulate` module. Defaults to "grid".

    Returns:
        str: Table of readings grouped and summarized by [optional](year and) month with additional statistical information to be printed on screen or pdf
    """
    
    ana_reading = model.Analyze_Reading( readings )
    years = ana_reading.monthly()
    
    if use_years_for_stats_section:
        stats = ana_reading.yearly()
    else:
        stats = ana_reading.completely()
    
    return readings_tabulate_data( years, stats, use_years_for_stats_section, tablefmt )


def readings_tabulate_data(
    years: list[ model.Analyzed_year_month ],
    stats: list[ model.Analyzed_year ] | model.Frame_statistics,
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
        months (`list[ Analyzed_year_month ]`): monthly grouped and statistically analyzed
        stats  (`list[ model.Analyzed_year ] | Frame_statistics`): if `use_years_for_stats_section`==`True` then yearly grouped and statistically analyzed else grouped and statistically analyzed
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
    
    assert use_years_for_stats_section == isinstance( stats, list ), \
        f"stats type is {type(stats)} but must be list if use_years_for_stats_section is set to true"
    assert not use_years_for_stats_section == isinstance( stats, model.Frame_statistics ), \
        f"stats type is {type(stats)} but must be model.Frame_statistics if use_years_for_stats_section is set to false"
    
    # get the maximum width of each columns header
    column_widths = [ max( map( len, lines.splitlines() ) ) for lines in TABLE_HEADER_READINGS_STATS ]
    
    table_data = []
    
    for year_group in years:
        for month in year_group.months:
            table_data.append( fmt.readings_format_month( year_group.year, month, column_widths[0] ) )
    
    # add spacing for years
    table_data.append( [ "- "*(column_widths[i]//2) for i in range(len(TABLE_HEADER_READINGS_STATS)) ] )
    
    if use_years_for_stats_section:
        for year in stats:
            table_data.append( fmt.readings_format_year( year, column_widths[0] ) )
    else:
        table_data.append( fmt.readings_format_span( stats, column_widths[0] ) )
    
    
    if not years: # Database has no entries
        table_data = [["no data"]*len(TABLE_HEADER_READINGS_STATS)]
    
    
    return tabulate(
        table_data,
        headers=TABLE_HEADER_READINGS_STATS,
        tablefmt=tablefmt,
        disable_numparse=True,
        colalign=('left', 'center', 'center', 'center')
    )

