from __future__ import annotations

from time import sleep

import console.detection
import console.utils
from console.screen import sc

from pynput import keyboard

from constants import *

# TODO Key: add ctrl+'alphabetic' since they are not nicely reconized
class Key():
    """
    ### Keymanager
    
    Handles user inputs.
    
    ---
    - Instance objects of this `Key` class act as a snapshot of the current state of user inputs (key press events) and can be invoked/instantiated by calling `Key.dump()`
    - To alter the internal state of user inputs (key press events) use the classmethods (`Key.press(...)`, `Key.release(...)`) provided as instructed
    - To get general information about a returned `Key` use the `get_char()`, `get_non_printable()`, `get_modifiers()`, `is_alpha_numeric()` instance methods as instructed ( or `info_str()` for 'debuging' )
    - To check (strictly) for a specific Key (-combination) instanciate a new `Key` object with your intended Key (-combination) and compare it with the inbuilt equal operation (`==`).
        Comparing with a `keyboard.Key` or `Keyboard.KeyCode` or `str` works but no modifiers can be supplied
    - To check wether a Key (-combination) is contained inside instanciate a new `Key` object with your intended Key (-combination) and compare it with the inbuilt contains operation (`in`).
        Comparing with a `keyboard.Key` or `Keyboard.KeyCode` or `str` works as well
    
    ---
    Examples:
    >>> k1 = Key(non_printable=keyboard.Key.enter, modifiers={keyboard.Key.ctrl})
    >>> k2 = Key(non_printable=keyboard.Key.enter)
    >>> k2 == k1, k2 in k1
    False, True
    >>> k3 = keyboard.Key.enter
    >>> k3 == k1, k3 in k1
    False, True
    """
    
    __MOD_LIST : list[keyboard.Key] = [
        keyboard.Key.alt,
        keyboard.Key.alt_l,
        keyboard.Key.alt_r,
        keyboard.Key.alt_gr,
        
        keyboard.Key.shift,
        keyboard.Key.shift_l,
        keyboard.Key.shift_r,
        
        keyboard.Key.ctrl,
        keyboard.Key.ctrl_l,
        keyboard.Key.ctrl_r,
        
        keyboard.Key.cmd,
        keyboard.Key.cmd_l,
        keyboard.Key.cmd_r
    ]
    
    # Class variables 
    _MODIFIERS        : set[keyboard.Key] = set()
    _KEY_NON_PRINTABLE: keyboard.Key      = None
    _KEY_ALPHA_NUMERIC: keyboard.KeyCode  = None
    
    
    # instance variables
    _modifiers        : set[keyboard.Key]
    _key_non_printable: keyboard.Key
    _key_alpha_numeric: keyboard.KeyCode
    
    _is_valid        : bool
    _is_alpha_numeric: bool
        
    @classmethod
    def press(cls, key_or_keyCode:object) -> None:
        """
        #### DO NOT USE THIS METHOD UNLESS YOU INTENT TO ALTER THE INTERNAL STATE OF THE KEYMANAGER
        ---

        Callback for pynput for KEY_DOWN events

        decides if pressed key is: 
        - a modifier: adding it to the current `Key.modifiers` set
        - not a modifier: updates its state accordingly to the Key

        Args:
            key_or_keyCode (`keyboard.Key` | `keyboard.KeyCode`): callback parameter from pynput, is either a `Key` or `KeyCode`
        """
        cls.is_alpha_numeric = hasattr( key_or_keyCode, "char" )
        
        if cls.is_alpha_numeric:
            cls._KEY_ALPHA_NUMERIC = key_or_keyCode
            cls._KEY_NON_PRINTABLE = None
            
            # # maybe not bulletproove !? needs further attention
            # cls.is_ctrl_c = cls._KEY_ALPHA_NUMERIC.char == '\x03'
        else:
            if key_or_keyCode in cls.__MOD_LIST:
                cls._MODIFIERS.add( key_or_keyCode )
                return
            
            cls._KEY_NON_PRINTABLE = key_or_keyCode
            cls._KEY_ALPHA_NUMERIC = None
    
    @classmethod
    def release(cls, key_or_keyCode:object) -> None:
        """
        #### DO NOT USE THIS METHOD UNLESS YOU INTENT TO ALTER THE INTERNAL STATE OF THE KEYMANAGER
        ---

        Callback for pynput for KEY_UP events

        decides if pressed key is: 
        - a modifier: removing it from the current `Key.modifiers` set
        - not a modifier: ignors event

        Args:
            key_or_keyCode (`keyboard.Key` | `keyboard.KeyCode`): callback parameter from pynput, is either a `Key` or `KeyCode`
        """
        if hasattr( key_or_keyCode, "char" ):
            return
        
        if key_or_keyCode in cls.__MOD_LIST:
            cls._MODIFIERS.discard( key_or_keyCode )
    
    @classmethod
    def dump(cls) -> Key:
        """
        #### DO NOT USE THIS METHOD UNLESS YOU INTENT TO ALTER THE INTERNAL STATE OF THE KEYMANAGER
        ---

        dumps the current state of the class veriables of `Key` into an imutable `Key` instance for returning to user

        Returns:
            `Key`: instance with attributes of current state
        """
        return Key( alpha_numeric=cls._KEY_ALPHA_NUMERIC, non_printable=cls._KEY_NON_PRINTABLE, modifiers=cls._MODIFIERS )
    
    @classmethod
    def convert(cls, _o:Key|keyboard.Key|keyboard.KeyCode|str) -> Key:
        if isinstance( _o, Key ):
            return _o
        
        if isinstance( _o, (str, keyboard.KeyCode) ):
            return Key( alpha_numeric=_o )
        
        if isinstance( _o, keyboard.Key ):
            return Key( non_printable=_o )
        
        raise TypeError( f"Object of Type {type(_o)} cannot be converted to type {type(Key)}" )
    
    
    def __init__(self, alpha_numeric:keyboard.KeyCode|str=None, non_printable:keyboard.Key=None, modifiers:set[keyboard.Key]=set()) -> None:
        self._is_valid = ( (alpha_numeric) or (non_printable and not non_printable in self.__MOD_LIST) ) and modifiers.issubset(self.__MOD_LIST)
        
        self._is_alpha_numeric  = False
        self._key_alpha_numeric = None
        self._key_non_printable = None
        self._modifiers         = []
        
        if not self._is_valid:
            return
        
        self._is_alpha_numeric  = not bool( non_printable )
        self._key_non_printable = non_printable
        self._modifiers = set( map( Key.canonicalize_modifier, modifiers ) )
    
        if isinstance( alpha_numeric, str ):
            if not alpha_numeric.isalnum() or len(alpha_numeric) != 1:
                self._is_valid = False
                return
                
            if alpha_numeric.isupper(): # adjust modifiers to string
                self._modifiers.add( keyboard.Key.shift ) # does not interfere with normalization
            else: # adjust string to modifiers
                if keyboard.Key.shift in self._modifiers:
                    alpha_numeric = alpha_numeric.upper()
                
            self._key_alpha_numeric = keyboard.KeyCode.from_char(alpha_numeric)
            
        else:
            self._key_alpha_numeric = alpha_numeric
            
    
    def get_char(self) -> str:
        """
        get string representation of bytes if possible, defaults to `''` if bytes represent a non printable string

        Returns:
            `str`: string of Key pressed, defaults to `''`
        """
        return self._key_alpha_numeric.char if self._is_alpha_numeric else ''
    
    def get_non_printable(self) -> keyboard.Key | None:
        """
        get `keyboard.Key` Enum if possible, defaults to `None` if key is alpha numeric

        Returns:
            `keyboard.Key` | `None`: `keyboard.Key` Enum of Key pressed, defaults to `None`
        """
        return self._key_non_printable
    
    def get_modifiers(self) -> list[keyboard.Key]:
        """
        get list of modifiers (`keyboard.Key` Enum) like `keyboard.Key.shift` or `keyboard.Key.alt`

        Returns:
            `list[keyboard.Key]`: list of `keyboard.Key` Enums of modifiers pressed
        """        
        return list( self._modifiers )
    
    def is_alpha_numeric(self) -> bool:
        return self._is_alpha_numeric
    
    def info_str(self) -> str:
        """
        Returns:
            `str`: easy human readable string of modifiers and key representation
        """
        if self._is_alpha_numeric is None:
            return ""
        
        # returns the string concatenated to the right of 'Key.' or the string itself if no 'Key.' is pressent
        rem = lambda x: str(x).removeprefix("Key.")
        
        return f"{'+'.join( map(rem, self._modifiers) )+'+' if len(self._modifiers) != 0 else ''}\'{self._key_alpha_numeric.char if self._is_alpha_numeric else rem(self._key_non_printable)}\'"

    
    @staticmethod
    def canonicalize_modifier(mod:keyboard.Key) -> keyboard.Key:
        """
        Normalizes a modifier `keyboard.Key`

        normalizes left/right modifiers to the general modifier code
        
        >>> Key.canonicalize_modifier(keyboard.Key.shift_l)
        keyboard.Key.shift

        Args:
            mod (`keyboard.Key`): modifier key to be normalized

        Returns:
            `keyboard.Key`: normalized key
        """
        
        if mod in ( keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r ):
            return keyboard.Key.shift
        
        if mod in ( keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r ):
            return keyboard.Key.ctrl
        
        if mod in ( keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r, keyboard.Key.alt_gr):
            return keyboard.Key.alt
        
        if mod in ( keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r ):
            return keyboard.Key.cmd
    
    def __eq__(self, _o:Key|keyboard.Key|keyboard.KeyCode|str) -> bool:
        k = Key.convert( _o )
        
        if not ( self._is_valid and k._is_valid ):
            return False
        
        return  ( self._key_alpha_numeric == k._key_alpha_numeric )\
            and ( self._key_non_printable == k._key_non_printable )\
            and ( not self._modifiers.symmetric_difference(k._modifiers )) # modifiers must be the same
        
    def __contains__(self, _o:Key|keyboard.Key|keyboard.KeyCode|str) -> bool:
        k = Key.convert( _o )
        
        if not ( self._is_valid and k._is_valid ):
            return False
        
        return  ( self._key_alpha_numeric == k._key_alpha_numeric )\
            and ( self._key_non_printable == k._key_non_printable )\
            and ( k._modifiers.issubset( self._modifiers ) )    # self.modifiers must contain (at least) all of k.modifiers
    

class Console():
    __listener: keyboard.Listener = None
    
    @classmethod
    def setup(cls) -> None:
        """ call setup before using the Console """
        
        console.utils.set_title( APP_NAME, 0 )
        # TODO add icon (for windows at least)

        cls.__listener = keyboard.Listener(
            on_press=Key.press,
            on_release=Key.release
        )
        cls.__listener.start()
        cls.__listener.wait()
    
    @classmethod
    def stop(cls) -> None:
        """ call stop after using the Console """
        cls.__listener.stop()
        
    @classmethod
    def write(cls, *args:str, **kwargs) -> None:
        """ wrapper for bultin function: `print`( *`arggs`, **`kwargs`, `end`='' ) but forces keyword `end` to be `''` """
        kwargs.pop("end", 0)
        print( *args, **kwargs, end='' )
    
    @classmethod
    def writeLine(cls, *args:str, **kwargs) -> None:
        """ basic wrapper for bultin function: `print`( *`arggs`, **`kwargs` ) """
        print( *args, **kwargs )
    
    @classmethod
    def write_at(cls, msg:str, col:int, line:int, absolute:bool=True) -> None:
        """
        write the given string at a specific position in the terminal
        
        Args:
            msg (`str`): text to be printed
            col (`int`): column position (x)
            line (`int`): line position (y)
            absolute (`bool`, optional): interpret (`col`, `line`) as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        c, l = (0, 0) if absolute else cls.get_cursor()
        with sc.location( col + c, line + l ):
            cls.write( msg )
    
    @classmethod
    def get_cursor(cls) -> tuple[int, int]:
        """
        Returns:
            (`column`, `line`): `column` and `line` of the cursor if unsuccessful defaults to (-1, -1)
        """
        return console.detection.get_position(-1, -1)
    
    @classmethod
    def set_cursor(cls, col:int, line:int, absolute:bool=True) -> None:
        """
        move the cursor to a specific position in the terminal
        
        Args:
            col (`int`): column position (x)
            line (`int`): line position (y)
            absolute (`bool`, optional): interpret (`col`, `line`) as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        c, l = (0, 0) if absolute else cls.get_cursor()
        sc.move_to( col + c, line + l )
    
    @classmethod
    def get_key(cls) -> Key:
        """
        Listens to the users input and reconizes different kind of inputs alpha-numeric, functional-/System Keys

        Returns:
            `Key`: static `Key` class
        """
        # only return 'Key' if the user is focused on the terminal
        key_console = console.utils.wait_key()
        if ord(key_console) == 224 or ord(key_console) == 0:
            key_console += console.utils.wait_key()

        return Key.dump()

    # @classmethod
    # def read(cls) -> str:
    #     ...
    
    @classmethod
    def clear(cls) -> None:
        """ clears the terminal screen completely blank """
        console.utils.cls()
    
    # @classmethod
    # def adjust_size(cls, size:tuple[int, int], minSize:tuple[int, int] = (-1, -1), forced:bool=False ) -> None:
    #     ...
    
    @classmethod
    def getConsoleSize(cls) -> tuple[int, int]:
        """
        Returns:
            (`width`, `height`): `width` and `height` of the console if unsuccessful defaults to (-1, -1)
        """
        return console.detection.get_size((-1, -1))
    
    # @classmethod
    # def getWindowRect(cls) -> tuple[int, int, int, int]:
    #     """
    #     Returns:
    #         (left, top, right, bottom): left, top, right, bottom coordinates of the console window if unsuccessful defaults to (-1, -1, -1, -1)
    #     """
    #     return win32gui.GetWindowRect( CONSOLE_HWND )
    
    # @classmethod
    # def getMaxWindowSize(cls) -> tuple[int, int]:
    #     """
    #     calculates maximum window size in screen coordinate (Pixels) based on the current left-top position of the console window and the available screen space the window is currently limited by
        
    #     Returns:
    #         (width_px, height_px): width and height in pixels of the maximum console window size if unsuccessful defaults to (-1, -1)
    #     """
    #     monitor_hwnd = win32api.MonitorFromWindow(CONSOLE_HWND, win32con.MONITOR_DEFAULTTONEAREST)
        
    #     info: dict = win32api.GetMonitorInfo( monitor_hwnd )
        
    #     screen: tuple[int, int, int, int] = info.get('Work', None)
    #     window = getWindowRect()
        
    #     return ( screen[2] - window[0], screen[3] - window[1] )
    
    # @classmethod
    # def getMaxConsoleSize(cls) -> tuple[int, int]:
    #     """
    #     calculates maximum console size in characters based on the current left-top position of the console window and the available screen space the window is currently limited by
        
    #     Returns:
    #         (width_px, height_px): width and height in pixels of the maximum console window size if unsuccessful defaults to (-1, -1)
    #     """
    #     size = getMaxWindowSize()
    #     fontSize = SCREEN_BUFFER.GetConsoleFontSize( SCREEN_BUFFER.GetCurrentConsoleFont(False)[0] )
        
    #     return ( round(SIZE_SCALE_FACTOR * size[0]/fontSize.X), round(SIZE_SCALE_FACTOR * size[1]/fontSize.Y) )


if __name__ == "__main__":
    # for i in range( 0, 1 + 2**13 ):
    #     print( ('\\'+hex(i)), i, chr(i),  )
    # while 1:
    #     key = console.utils.wait_key()
        
    #     print( key, end='\t' )
    #     print( ord(key), end='\t' )
    #     print( chr(ord(key)), end='\t' )
    #     print( key.encode("ansi", "ignore") )
        
    #     if key == "\x03":
    #         break
    
    # Testing Key listener
    Console.setup()
    Console.clear()
    
    k1 = Key(non_printable=keyboard.Key.enter, modifiers={keyboard.Key.ctrl})
    kA = Key(alpha_numeric="a", modifiers={keyboard.Key.shift})
    kB = Key(alpha_numeric="b")
    kc = "C"
    
    print( k1.info_str(), kA.info_str(), kB.info_str(), kc, sep="\t|\t" )
    
    while 1:
        sleep(0.01)
        key = Console.get_key()
        
        l = [
              k1 in key
            , kA in key
            , kB in key
            , kc in key
            , key.get_non_printable()
            , key.get_char()
            , key.info_str()
            , key.get_modifiers()
        ]
        
        print( (" {!s:>10s} |"*len(l)).format( *l ) )
        
        if key == "q":
            break
    
    Console.stop()