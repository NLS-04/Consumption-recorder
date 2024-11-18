from generic_lib.simpleTUI import *

if __name__ == '__main__':
    from generic_lib.dbHandler import DBSession
    Console.setup( "Focus Test" )
    Console.clear()
    Console.set_cursor( 0, 0 )
    
    but = Button("Testing")
    but.render()
    
    # Console.write_in( ".---------.| Testing |`---------´", (0, 0), (10, 2), True, True )
    
    Console.set_cursor( 0, 5 )