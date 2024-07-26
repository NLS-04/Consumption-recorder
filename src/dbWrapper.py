
from datetime import date

from generic_lib.dbHandler import DBSession, Reading, Person
from constants import PATH_DB, COUNT_READING_ATTRIBUTES



__SESSION = DBSession( PATH_DB, COUNT_READING_ATTRIBUTES )


def get_DB_handle() -> DBSession:
    return __SESSION


def add_reading( data:Reading ) -> None:
    __SESSION.add_reading( data )
def add_person( data:Person ) -> None:
    __SESSION.add_person( data )

def remove_reading( date: date ) -> None: 
    __SESSION.remove_readings( date, date )
def remove_readings( date_low: date, date_high:date ) -> None: 
    __SESSION.remove_readings( date_low, date_high )
def remove_person( name:str ) -> None: 
    __SESSION.remove_person( name )

def get_all_readings() -> list[Reading]:
    return __SESSION.get_reading_all()
def get_all_persons() -> list[Person]: 
    return __SESSION.get_person_all()

def get_data_between( date_low: date, date_high: date ) -> tuple[list[Reading], list[Person]]:
    readings = __SESSION.get_reading_between( date_low, date_high )
    persons  = __SESSION.get_person_where( "move_in <= '%s' OR move_out >= '%s'" % (str(date_high), str(date_low)) )
    return readings, persons

def exist_reading( date:date ) -> tuple[bool, list[Reading]]:
    return __SESSION.exists_readings( date, date )
def exist_readings( date_low:date, date_high:date ) -> tuple[bool, list[Reading]]:
    return __SESSION.exists_readings( date_low, date_high )

def exist_person( name ) -> tuple[bool, list[Person]]:
    return __SESSION.exists_person( name )
def exist_persons( date_low:date, date_high:date ) -> tuple[bool, list[Person]]:
    return __SESSION.exists_person( '*', "move_in <= '%s' OR move_out >= '%s'" % (str(date_high), str(date_low)) )


def get_all_reading_dates() -> list[str]:
    """
     fetches all individual reading dates in database

    Returns:
        `list[str]`: dates of person in database
    """
    return [ r.date for r in get_all_readings() ]

def get_all_names() -> list[str]:
    """
    fetches all individual names of persons in database

    Returns:
        `list[str]`: names of person in database
    """    
    return [ p.name for p in get_all_persons() ]

