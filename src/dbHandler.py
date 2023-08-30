from constants import *

import sqlite3
import datetime

from platformdirs import user_data_path

  ############
 # SETTABLE #
############

NAME_FILE_DB = "data.db"


  ###############
 # SOURCE CODE #
###############

PATH_DB = user_data_path( APP_NAME, APP_AUTHOR, roaming=False, ensure_exists=True ).joinpath(NAME_FILE_DB)


class DBSession():
    __connection: sqlite3.Connection
    
    def __init__(self) -> None:
        with self as con:
            con.execute( """ CREATE TABLE IF NOT EXISTS readings( date DATE PRIMARY KEY, electricity REAL, gas REAL, water REAL ) """ )
            con.execute( """ CREATE TABLE IF NOT EXISTS persons( nameID TEXT PRIMARY KEY, move_in DATE, move_out DATE ) """ )


    def add_reading( self, date:datetime.date, electricity:float, gas:float, water:float ) -> None:
        with self as con:
            con.execute( """ INSERT OR IGNORE INTO readings(date) VALUES (?) """, (date,) )
            con.execute( """ UPDATE readings SET electricity=?, gas=?, water=? WHERE date=?""", (electricity, gas, water, date) )
    
    def add_person( self, person_name:str, move_in:datetime.date=None, move_out:datetime.date=None ) -> None:
        with self as con:
            con.execute( """ INSERT OR IGNORE INTO persons(nameID) VALUES (?) """, (person_name,) )
            con.execute( """ UPDATE persons SET move_in=?, move_out=? WHERE nameID=?""", (move_in, move_out, person_name) )
    
    
    def remove_readings( self, date_low_bound:datetime.date, date_up_bound:datetime.date, *, additional_condition:str=None ) -> None:
        with self as con:
            con.execute( """ DELETE FROM readings WHERE date BETWEEN ? AND ? AND ? """, (date_low_bound, date_up_bound, additional_condition if additional_condition else True) )
    
    def remove_person( self, person_name:str, *, additional_condition:str=None ) -> None:
        with self as con:
            con.execute( """ DELETE FROM persons WHERE nameID=? AND ? """, (person_name, additional_condition if additional_condition else True) )
    
    
    def get_reading_all(self) -> list[tuple[datetime.date, float, float, float]]:
        with self as con:
            return con.execute( """ SELECT * FROM readings ORDER BY date """ ).fetchall()
        
    def get_reading_where(self, where:str) -> list[tuple[datetime.date, float, float, float]]:
        #! VERY DANGEROUS, BUT MEH
        with self as con:
            return con.execute( f""" SELECT * FROM readings WHERE {where} ORDER BY date """ ).fetchall()
    
    def get_reading_between(self, date_low_bound:datetime.date, date_up_bound:datetime.date) -> list[tuple[datetime.date, float, float, float]]:
        return self.get_reading_where( "date BETWEEN '%s' AND '%s'" % (str(date_low_bound), str(date_up_bound)) )
    
    
    def get_person_all(self) -> list[tuple[str, datetime.date, datetime.date]]:
        with self as con:
            return con.execute( """ SELECT * FROM persons ORDER BY move_in """ ).fetchall()
        
    def get_person_where(self, where:str) -> list[tuple[str, datetime.date, datetime.date]]:
        with self as con:
            return con.execute( f""" SELECT * FROM persons WHERE {where} ORDER BY move_in """ ).fetchall()
    
    
    def exists_readings(self, date_low_bound:datetime.date, date_up_bound:datetime.date, additional_condition:str=None) -> tuple[ bool, list[ tuple[datetime.date, float, float, float] ] ]:
        entry = self.get_reading_where( "date BETWEEN '%s' AND '%s' AND %s" % (str(date_low_bound), str(date_up_bound), additional_condition if additional_condition else 'TRUE'))
        return bool(entry), entry if bool(entry) else None
    
    def exists_person(self, nameID:str, additional_condition:str=None) -> tuple[ bool, list[ tuple[str, datetime.date, datetime.date] ] ]:
        entry = self.get_person_where( "nameID = '%s' AND %s" % ( nameID, additional_condition if additional_condition else 'TRUE') )
        return bool(entry), entry[0] if bool(entry) else None
    
    
    def ping(self) -> tuple[str, bool]:
        try:
            sqlite3.connect( PATH_DB.absolute(), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES ).close()
        except BaseException as e:
            return e, False
        finally:
            return "Succesful connection", True        
        

    def __enter__(self):
        self.__connection = sqlite3.connect( PATH_DB.absolute(), detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES )
        return self.__connection
    def __exit__(self, type, value, traceback):
        self.__connection.commit()
        self.__connection.close()


def fill_dummy_readings( amount:int = 50 ):
    START_VALUE  = ( 14867.2, 1123.158, 38.511 )
    STADY_CHANGE = ( 20.0, 1.5, 1.0 )
    VARIANCE = 5.0
    
    TIMEDELTA = datetime.timedelta(7)
    DATE = datetime.date.today()
    
    SESSION = DBSession()
    
    import random
    rand = lambda: VARIANCE * ( 2*random.random() - 1 )
    
    for i in range(amount):
        SESSION.add_reading(
            DATE+i*TIMEDELTA,
            round( START_VALUE[0]+i*STADY_CHANGE[0]+rand(), 1),
            round( START_VALUE[1]+i*STADY_CHANGE[1]+rand(), 3),
            round( START_VALUE[2]+i*STADY_CHANGE[2]+rand(), 3)
        )
    

if __name__ == '__main__':    
    s = DBSession()
    
    s.add_reading( datetime.date.today(), 1.0, 2.0, 0.0 )
    s.add_reading( datetime.date.fromisocalendar(2023, 20, 7), 2.0, 2.0, 0.0 )
    s.add_reading( datetime.date.today(), 3.0, 3.0, 3.0 )
    
    d1 = datetime.date.fromisoformat("2023-03-21")
    d2 = datetime.date.fromisoformat("2023-03-21")
    d3 = datetime.date.fromisoformat("2023-10-14")
    
    # fill_dummy_readings(50)
    
    with s as con:
        print( con.execute( """ SELECT * FROM readings WHERE date BETWEEN ? AND ? AND ?""", (d1, d2, True) ).fetchall() )
