import pytermgui as ptg
from pytermgui.pretty import pprint
from pytermgui.input import getch, keys

import msvcrt

while True:
    n = None
    while not n:
        n = msvcrt.getwch()
        if msvcrt.kbhit():
            n += msvcrt.getwch()
    
    k = None
    while not k:
        k = getch()
    
    print( k.encode("unicode_escape").decode("utf-8"), keys.get_name( k ) )
    print( n.encode("unicode_escape").decode("utf-8"), keys.get_name( n ) )
