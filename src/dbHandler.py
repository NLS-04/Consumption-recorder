from dataclasses import dataclass, field
from typing import Optional
from contextlib import contextmanager
from pathlib import Path
from platformdirs import user_data_path

import sqlite3
import datetime

from constants import *

  ############
 # SETTABLE #
############

NAME_FILE_DB = "data.db"


  ###############
 # SOURCE CODE #
###############

PATH_ROOT = Path(__file__).parent
PATH_DB = user_data_path( APP_NAME, APP_AUTHOR, roaming=False, ensure_exists=True ).joinpath(NAME_FILE_DB)

@dataclass
class Reading:
    date: datetime.date
    attributes: list[ float|int|None ] =  field( default=lambda:[None]*COUNT_READING_ATTRIBUTES ) 
    
    def assert_validity(self) -> Optional[AssertionError]:
        assert isinstance(self.date, datetime.date), "date is not of type datetime.date"
        assert len(self.attributes) >= COUNT_READING_ATTRIBUTES, f"length of attributes is less than {COUNT_READING_ATTRIBUTES}"
        assert all( map(lambda x: isinstance(x, (float, int, None)), self.attributes ) ), "some attributes are not of type float|int"

@dataclass
class Person:
    name: str
    move_in : datetime.date | None = None
    move_out: datetime.date | None = None
    
    def assert_validity(self) -> Optional[AssertionError]:
        assert isinstance( self.name, str ), "name is not of type str"
        assert isinstance( self.move_in, (datetime.date, None) ), "move_in is not of type datetime.time"
        assert isinstance( self.move_out, (datetime.date, None) ), "move_out is not of type datetime.time"

class DBSession():
    __connection: sqlite3.Connection
    __db_path: Path
    
    def __init__(self, path_to_db:Optional[Path]=PATH_DB) -> None:
        self.__db_path = path_to_db
        with self.__connect() as con:
            con.execute( """ CREATE TABLE IF NOT EXISTS readings( date DATE PRIMARY KEY, electricity REAL, gas REAL, water REAL ) """ )
            con.execute( """ CREATE TABLE IF NOT EXISTS persons( nameID TEXT PRIMARY KEY, move_in DATE, move_out DATE ) """ )


    def add_reading( self, reading: Reading ) -> None:
        reading.assert_validity()
        
        with self.__connect() as con:
            con.execute( """ INSERT OR IGNORE INTO readings(date) VALUES (?) """, (reading.date,) )
            con.execute( """ UPDATE readings SET electricity=?, gas=?, water=? WHERE date=?""", (*reading.attributes, reading.date) )
    
    def add_person( self, person: Person ) -> None:
        person.assert_validity()
        
        with self.__connect() as con:
            con.execute( """ INSERT OR IGNORE INTO persons(nameID) VALUES (?) """, (person.name,) )
            con.execute( """ UPDATE persons SET move_in=?, move_out=? WHERE nameID=?""", (person.move_in, person.move_out, person.name) )
    
    
    def remove_readings( self, date_low_bound:datetime.date, date_up_bound:datetime.date, *, additional_condition:str=None ) -> None:
        with self.__connect() as con:
            con.execute( """ DELETE FROM readings WHERE date BETWEEN ? AND ? AND ? """, (date_low_bound, date_up_bound, additional_condition if additional_condition else True) )
    
    def remove_person( self, person_name:str, *, additional_condition:str=None ) -> None:
        with self.__connect() as con:
            con.execute( """ DELETE FROM persons WHERE nameID=? AND ? """, (person_name, additional_condition if additional_condition else True) )
    
    
    def get_reading_all(self) -> list[ Reading ]:
        with self.__connect() as con:
            out = con.execute( """ SELECT * FROM readings ORDER BY date """ ).fetchall()
            return [ Reading( r[0], r[1:] ) for r in out ]
    
    def get_reading_where(self, where:str) -> list[ Reading ]:
        #! VERY DANGEROUS, BUT MEH NOT A PROBLEM NOW :)
        with self.__connect() as con:
            out = con.execute( f""" SELECT * FROM readings WHERE {where} ORDER BY date """ ).fetchall()
            return [ Reading( r[0], r[1:] ) for r in out ]
    
    def get_reading_between(self, date_low_bound:datetime.date, date_up_bound:datetime.date) -> list[ Reading ]:
        return self.get_reading_where( "date BETWEEN '%s' AND '%s'" % (str(date_low_bound), str(date_up_bound)) )
    
    
    def get_person_where(self, where:str) -> list[ Person ]:
        with self.__connect() as con:
            out =  con.execute( f""" SELECT * FROM persons WHERE {where} ORDER BY move_in """ ).fetchall()
            return [ Person( *p ) for p in out ]
    
    def get_person_all(self) -> list[ Person ]:
        return self.get_person_where( 'TRUE' )
    
    def exists_readings(self, date_low_bound:datetime.date, date_up_bound:datetime.date, additional_condition:str=None) -> tuple[ bool, list[ Reading ] ]:
        entry = self.get_reading_where( "date BETWEEN '%s' AND '%s' AND %s" % (str(date_low_bound), str(date_up_bound), additional_condition if additional_condition else 'TRUE'))
        return bool(entry), entry if bool(entry) else None
    
    def exists_person(self, nameID:str, additional_condition:str=None) -> tuple[ bool, list[ Person ] ]:
        entry = self.get_person_where( "nameID = '%s' AND %s" % ( nameID, additional_condition if additional_condition else 'TRUE') )
        return bool(entry), entry if bool(entry) else None
    
    
    def ping(self) -> tuple[str, bool]:
        try:
            sqlite3.connect( PATH_DB.absolute(), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES ).close()
        except BaseException as e:
            return e, False
        finally:
            return "Successful connection", True
    
    @contextmanager
    def __connect(self):
        try:
            self.__connection = sqlite3.connect( self.__db_path.absolute(), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES )
            yield self.__connection
        finally:
            self.__connection.commit()
            self.__connection.close()



if __name__ == '__main__':
    dummy_db_path = PATH_ROOT.joinpath( "test_dummy.db" )
    
    def fill_dummy_readings( path:Path=dummy_db_path, amount:int = 50 ):
        START_VALUE   = ( 14867.2, 1123.158, 38.511 )
        STEADY_CHANGE = ( 20.0, 1.5, 1.0 )
        VARIANCE = 5.0

        TIMEDELTA = datetime.timedelta(7)
        DATE = datetime.date.today()

        SESSION = DBSession( path )

        import random
        rand = lambda: VARIANCE * ( 2*random.random() - 1 )

        for i in range(amount):
            SESSION.add_reading(
                Reading(
                    DATE+i*TIMEDELTA,
                    [
                        round( START_VALUE[0]+i*STEADY_CHANGE[0]+rand(), 1),
                        round( START_VALUE[1]+i*STEADY_CHANGE[1]+rand(), 3),
                        round( START_VALUE[2]+i*STEADY_CHANGE[2]+rand(), 3)
                    ]
                )
            )
    
    s = DBSession( dummy_db_path )
    
    s.add_reading( Reading( datetime.date.today(), [ 1.0, 2.0, 0.0 ] ) )
    s.add_reading( Reading( datetime.date.fromisocalendar(2023, 20, 7), [ 2.0, 2.0, 0.0 ] ) )
    s.add_reading( Reading( datetime.date.today(), [ 3.0, 3.0, 3.0 ] ) )
    
    d1 = datetime.date.fromisoformat("2023-03-21")
    d2 = datetime.date.fromisoformat("2023-03-21")
    d3 = datetime.date.fromisoformat("2023-10-14")
    
    fill_dummy_readings( dummy_db_path, 50 )
    
    print( *s.get_reading_all(), sep="\n" )
