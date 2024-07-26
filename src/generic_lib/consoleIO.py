from   __future__ import annotations

from   typing import Optional, Sequence, overload

from   time import time

import sys
from   contextlib import contextmanager, _GeneratorContextManager

import console.detection
import console.utils
from   console.screen import sc, Screen

import pynput.keyboard as keyboard


# TODO Key: add ctrl+'alphabetic' since they are not nicely recognized
# TODO Key: integrate pynput.keyboard into Key class
class Key():
    """
    # Key-manager
    
    Handles user inputs.
    
    ---
    - Instance objects of this `Key` class act as a snapshot of the current state of user inputs (key press events) and can be invoked/instantiated by calling `Key.dump()`
    - To alter the internal state of user inputs (key press events) use the classmethods (`Key.press(...)`, `Key.release(...)`) provided as instructed
    - To get general information about a returned `Key` use the `get_char()`, `get_non_printable()`, `get_modifiers()`, `is_alpha_numeric()` instance methods as instructed ( or `info_str()` for 'debugging' )
    - To check (strictly) for a specific Key (-combination) instantiate a new `Key` object with your intended Key (-combination) and compare it with the inbuilt equal operation (`==`).
        Comparing with a `keyboard.Key` or `Keyboard.KeyCode` or `str` works but no modifiers can be supplied
    - To check wether a Key (-combination) is contained inside instantiate a new `Key` object with your intended Key (-combination) and compare it with the inbuilt contains operation (`in`).
        Comparing with a `keyboard.Key` or `Keyboard.KeyCode` or `str` works as well
    
    ## Structural Pattern Matching:
    Use the following keywords for structural pattern matching:
        - `np`   of type [`keyboard.Key` | `None`]      : Non Printable alias for `get_non_printable()`
        - `an`   of type [`str` | `None`]               : Alpha Numeric alias for `get_char()`
        - `mods` of type [`list[keyboard.Key]` | `None`]: Modifiers alias for `get_modifiers()`
    
    ---
    ## Modifiers
    the following `keyboard.Key` objects are valid modifiers:
    - `keyboard.Key.alt`
    - `keyboard.Key.shift`
    - `keyboard.Key.ctrl`
    - `keyboard.Key.cmd`
    
    the following `keyboard.Key` objects are also valid modifiers but are unnecessarily precise, preferably use the above mentioned modifiers:
    - `keyboard.Key.alt_l`
    - `keyboard.Key.alt_r`
    - `keyboard.Key.alt_gr`, instead use `keyboard.Key.ctrl` + `keyboard.Key.alt`
    
    - `keyboard.Key.shift_l`
    - `keyboard.Key.shift_r`
    
    - `keyboard.Key.ctrl_l`
    - `keyboard.Key.ctrl_r`
    
    - `keyboard.Key.cmd_l`
    - `keyboard.Key.cmd_r`
    
    ---
    ## Examples:
    >>> k1 = Key(keyboard.Key.enter, keyboard.Key.ctrl)
    >>> k2 = Key(keyboard.Key.enter)
    >>> k2 == k1, k2 in k1
    False, True
    >>> k3 = keyboard.Key.enter
    >>> k3 == k1, k3 in k1
    False, True
    >>> k4 = Key(keyboard.Key.up, keyboard.Key.ctrl, keyboard.Key.alt)
    >>> k4.info_str()
    ctrl+alt+'up'
    
    ---
    #
    >>> match inputted_key:
    >>>     case Key( np=keyboard.Key.enter ):
    >>>         '''matches all Keys where the non-printable is the `enter-key` and all modifiers'''
    >>>     case Key( np=keyboard.Key.enter, mods=[] ):
    >>>         '''only matches Keys where the non-printable is the `enter-key` and no modifiers'''
    >>>     case Key( an="c", mods=[] ):
    >>>         '''only matches Keys where the alpha-numeric is the `"c"` character and no modifiers'''
    """
    __match_args__ = ("np", "an", "mods")
    
    @property
    def np(self) -> keyboard.Key | None:
        '''Non Printable: matching-alias for `get_non_printable()`'''
        return self.get_non_printable()
    @property
    def an(self) -> str | None:
        '''Alpha Numeric: matching-alias for `get_char()`'''
        return self.get_char()
    @property
    def mods(self) -> list[keyboard.Key] | None:
        '''Modifiers: matching-alias for `get_modifiers()`'''
        return self.get_modifiers()
    

    # Class variables 
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
        #### DO NOT USE THIS METHOD UNLESS YOU INTENT TO ALTER THE INTERNAL STATE OF THE KEY-MANAGER
        ---

        Callback for pynput for KEY_DOWN events

        decides if pressed key is: 
        - a modifier: adding it to the current `Key.modifiers` set
        - not a modifier: updates its state accordingly to the Key

        Args:
            key_or_keyCode (`keyboard.Key` | `keyboard.KeyCode`): callback parameter from pynput, is either a `Key` or `KeyCode`
        """
        is_alpha_numeric = hasattr( key_or_keyCode, "char" )
        
        if is_alpha_numeric:
            cls._KEY_ALPHA_NUMERIC = key_or_keyCode
            cls._KEY_NON_PRINTABLE = None
        else:
            if key_or_keyCode in cls.__MOD_LIST:
                cls._MODIFIERS.add( key_or_keyCode )
                return
            
            cls._KEY_NON_PRINTABLE = key_or_keyCode
            cls._KEY_ALPHA_NUMERIC = None
    
    @classmethod
    def release(cls, key_or_keyCode:object) -> None:
        """
        #### DO NOT USE THIS METHOD UNLESS YOU INTENT TO ALTER THE INTERNAL STATE OF THE KEY-MANAGER
        ---

        Callback for pynput for KEY_UP events

        decides if pressed key is: 
        - a modifier: removing it from the current `Key.modifiers` set
        - not a modifier: ignores event

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
        #### DO NOT USE THIS METHOD UNLESS YOU INTENT TO ALTER THE INTERNAL STATE OF THE KEY-MANAGER
        ---

        dumps the current state of the class variables of `Key` into an immutable `Key` instance for returning to user

        Returns:
            `Key`: instance with attributes of current state
        """
        return Key( cls._KEY_ALPHA_NUMERIC if cls._KEY_ALPHA_NUMERIC else cls._KEY_NON_PRINTABLE, *cls._MODIFIERS )
    
    @classmethod
    def convert(cls, _o:Key|keyboard.Key|keyboard.KeyCode|str, /) -> Key:
        """
        Convert object of types `Key`, `keyboard.Key`, `keyboard.KeyCode`, `str` into a `Key` object

        Args:
            _o (`Key` | `keyboard.Key` | `keyboard.KeyCode` | `str`): object to be converted to a `Key` object

        Raises:
            `TypeError`: if the object was none of the above mentioned types

        Returns:
            `Key`: the converted object
        """
        if isinstance( _o, Key ):
            return _o
        
        return Key( _o )
    
    
    @overload
    def __init__(self, _o:keyboard.Key, /, *mods:list[keyboard.Key]): ...
    @overload
    def __init__(self, _o:keyboard.KeyCode, /, *mods:list[keyboard.Key]): ...
    @overload
    def __init__(self, _o:str, /, *mods:list[keyboard.Key]): ...
    def __init__(self, _o:keyboard.Key|keyboard.KeyCode|str|None=None, /, *mods:list[keyboard.Key]):
        """
        Instantiated an Key object with pressed-key-event from object of types `keyboard.Key`, `keyboard.KeyCode`, `str` and modifiers of type `keyboard.Key`

        Args:
            _o (`keyboard.Key` | `keyboard.KeyCode` | `str`): object to be converted to a `Key` object
            *_m (`list`[`keyboard.Key`]): objects to be added as modifiers to converted `Key` object

        Raises:
            `TypeError`: if the pressed-key-event was none of the above mentioned types or the supplied modifiers are not valid

        Returns:
            `Key`: the converted object
        """
        if _o is None:
            return self._set_init()
        
        m = set( mods )
        if not m.issubset( self.__MOD_LIST ):
            raise TypeError( f"{m.difference( self.__MOD_LIST )} are not valid modifiers, see documentation for valid modifiers" )
        
        if isinstance( _o, keyboard.KeyCode ):
            return self._set_init( alpha_numeric_keyCode=_o, modifiers=m )
        
        if isinstance( _o, str ):
            return self._set_init( alpha_numeric_str=_o, modifiers=m )
        
        if isinstance( _o, keyboard.Key ):
            return self._set_init( non_printable=_o, modifiers=m )
        
        raise TypeError( f"Key can not be instantiated with object of Type {type(_o)}" )
    
    def _set_init(self, alpha_numeric_keyCode:keyboard.KeyCode=None, alpha_numeric_str:str=None, non_printable:keyboard.Key=None, modifiers:set[keyboard.Key]=set()) -> None:
        """
        backend method to initialize an instance `Key` object with the given parameters
        
        Args:
            alpha_numeric_keyCode (`keyboard.KeyCode`, optional): `keyCode` to set for this `Key`. Defaults to `None`.
            alpha_numeric_str (`str`, optional): `str` as alpha numeric value to set for this `Key`. Defaults to `None`.
            non_printable (`keyboard.Key`, optional): `keyboard.Key` to set for this `Key`. Defaults to `None`.
            modifiers (`set`[`keyboard.Key`], optional): `keyboard.Key` modifiers to set for this `Key`. Defaults to `set()`.
        """
        self._is_alpha_numeric  = False
        self._key_alpha_numeric = None
        self._key_non_printable = None
        self._modifiers         = []
        
        
        if non_printable in self.__MOD_LIST:
            non_printable = None
        
        self._is_valid = ( alpha_numeric_keyCode or alpha_numeric_str or non_printable ) and modifiers.issubset( self.__MOD_LIST )
        
        if not self._is_valid:
            return
        
        
        self._is_alpha_numeric  = not bool( non_printable )
        self._key_non_printable = non_printable
        self._modifiers = set( map( Key.canonicalize_modifier, modifiers ) )
    

        if not alpha_numeric_str:
            self._key_alpha_numeric = alpha_numeric_keyCode
            return
        
        
        if len(alpha_numeric_str) != 1:
            self._is_valid = False
            return
            
        if alpha_numeric_str.isupper(): # adjust modifiers to string
            self._modifiers.add( keyboard.Key.shift ) # does not interfere with normalization
        else: # adjust string to modifiers
            if keyboard.Key.shift in self._modifiers:
                alpha_numeric_str = alpha_numeric_str.upper()
            
        self._key_alpha_numeric = keyboard.KeyCode.from_char(alpha_numeric_str)
    
    
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
        if self._is_valid is None:
            return ""
        
        rem = lambda x: str(x).removeprefix("Key.")
        
        return f"{'+'.join( map(rem, self._modifiers) )+'+' if len(self._modifiers) != 0 else ''}\'{self._key_alpha_numeric.char if self._is_alpha_numeric else rem(self._key_non_printable)}\'"

    
    @staticmethod
    def canonicalize_modifier( mod:keyboard.Key ) -> keyboard.Key:
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
        match mod:
            case keyboard.Key.shift | keyboard.Key.shift_l | keyboard.Key.shift_r:
                return keyboard.Key.shift

            case keyboard.Key.ctrl | keyboard.Key.ctrl_l | keyboard.Key.ctrl_r:
                return keyboard.Key.ctrl
            
            case keyboard.Key.alt | keyboard.Key.alt_l | keyboard.Key.alt_r | keyboard.Key.alt_gr:
                return keyboard.Key.alt
            
            case keyboard.Key.cmd | keyboard.Key.cmd_l | keyboard.Key.cmd_r:
                return keyboard.Key.cmd

            case _:
                return mod
    
    def __eq__(self, _o:Key|keyboard.Key|keyboard.KeyCode|str|Sequence[keyboard.Key|keyboard.KeyCode|str], /) -> bool:
        k = Key.convert( _o )
        
        if not ( self._is_valid and k._is_valid ):
            return False
        
        return  ( self._key_alpha_numeric == k._key_alpha_numeric )\
            and ( self._key_non_printable == k._key_non_printable )\
            and ( not self._modifiers.symmetric_difference(k._modifiers )) # modifiers must be the same
    
    def __contains__(self, _o:Key|keyboard.Key|keyboard.KeyCode|str, /) -> bool:
        k = Key.convert( _o )
        
        if not ( self._is_valid and k._is_valid ):
            return False
        
        return  ( self._key_alpha_numeric == k._key_alpha_numeric )\
            and ( self._key_non_printable == k._key_non_printable )\
            and ( k._modifiers.issubset( self._modifiers ) )    # self.modifiers must contain (at least) all of k.modifiers

class Console():
    __listener: keyboard.Listener = None
    
    __is_virtual   : bool = False
    __virtual_depth: int  = 0
    
    __screen_lt: tuple[int, int] = (0, 0)
    __screen_rb: tuple[int, int] = None
    
    @classmethod
    def setup(cls, title:Optional[str]=None) -> None:
        """ call setup before using the Console """
        
        console.utils.set_title( title, 0 )

        cls.__is_virtual    = False
        cls.__virtual_depth = 0
        
        cls.__screen_lt = (0, 0)
        cls.__screen_rb = cls.get_console_size()
        
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
        cls.show_cursor()
    
    
    @classmethod
    def write(cls, *args:object, sep:str=" ") -> None:
        """ writes to terminal at current cursor position """
        
        str_args = sep.join( map(str, args) )
        arg_lines = str_args.splitlines()
        
        # normally '\n' at the beginning of a string will be kept
        # if str_args.startswith('\n'):
        #     arg_lines = [''] + arg_lines
        
        if str_args.endswith('\n'):
            arg_lines += ['']
        
        if not cls.__is_virtual: # simply use stdout
            for line in arg_lines:
                cls.__stdout( line + '\n' )
            return
        
        
        width, height = cls.get_console_size()
        for i, line in enumerate(arg_lines):
            buffer = line
            
            while True:
                cls.__stdout( buffer[:width-cls.get_cursor()[0]] )

                if len(buffer) <= width:
                    break
                
                if cls.get_cursor()[0] == width:
                    cls.__set_cursor_no_clamp( 0, cls.get_cursor()[1]+1 )
                
                buffer = buffer[width:]
            
            if i != len(arg_lines) - 1:
                cls.__set_cursor_no_clamp( 0, cls.get_cursor()[1]+1 )
    
    @classmethod
    def write_line(cls, *args:str, sep:str=" ") -> None:
        """ writes to terminal at current cursor position and starts a new line """
        cls.write( *args, "\n", sep=sep )
    
    @classmethod
    def write_at(cls, msg:str, col:int, line:int, absolute:bool=True) -> None:
        """
        write the given string at the specified position in the terminal
        
        Args:
            msg (`str`): text to be printed
            col (`int`): column position (x)
            line (`int`): line position (y)
            absolute (`bool`, optional): interpret (`col`, `line`) as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        c, l = (0, 0) if absolute else cls.get_cursor()
        
        col, line = cls._transform_local_2_global( col + c, line + l )
        
        with sc.location( line, col ):
            cls.write( msg )
    
    @classmethod
    def write_in(cls, msg:str, col:int, line:int, end_col:int=None, end_line:int=None, absolute:bool=True, clear_area:bool=True) -> None:
        """
        write the given string at the specified position in the terminal, but clear the area from (col, line) to (end_col, end_line) before writing
        
        if end_col and end_line are `None`: 
        - end_col will be set to the most right column position of the terminal
        - end_line will be set to the same line as specified
        
        Args:
            msg (`str`): text to be printed
            col (`int`): column position (x)
            line (`int`): line position (y)
            end_line (`int`): area end line position (y). Defaults to `None`
            end_col (`int`): area end column position (x). Defaults to `None`
            absolute (`bool`, optional): interpret (`col`, `line`) as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        c, l  = (0, 0) if absolute else cls.get_cursor()
        col  += c
        line += l
        
        end_col  = end_col  + c if not absolute and end_col  else end_col 
        end_line = end_line + l if not absolute and end_line else end_line
        
        end_col  = end_col  if end_col  else cls.get_console_size()[0]
        end_line = end_line if end_line else line
        
        with cls.virtual_area( (col, line), (end_col, end_line) ):
            if clear_area:
                cls.clear()
            cls.write(msg)
    
    
    @classmethod
    def get_cursor(cls, *, true_cursor_pos:bool=False) -> tuple[int, int]:
        """
        left upper corner is (0, 0)
        
        Returns:
            (`column`, `line`): `column` and `line` of the cursor if unsuccessful defaults to (0, 0)
        """
        c, l = console.detection.get_position()
        c, l = c-1, l-1
        
        if true_cursor_pos:
            return c, l
        
        return cls._transform_global_2_local( c, l )
    
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

        col, line = cls._transform_local_2_global( col + c, line + l )
        
        cls.__stdout( sc.move_to( col, line ) )
    
    @classmethod
    def hide_cursor(cls) -> None:
        """ hide the blinking cursor symbol on the screen """
        cls.__stdout( sc.hide_cursor )
    
    @classmethod
    def show_cursor(cls) -> None:
        """ show the blinking cursor symbol on the screen """
        cls.__stdout( sc.show_cursor )
    
    
    @classmethod
    def get_key(cls) -> Key:
        """
        Listens to the users input and recognizes different kind of inputs alpha-numeric, functional-/System Keys

        Returns:
            `Key`: static `Key` class
        """
        
        # only return 'Key' if the user is focused on the terminal
        # this variable only fulfills the purpose to register key inputs on the terminal and to let the Key class read all strokes of e.g. an compounded Key like enter
        _k = console.utils.wait_key()
        if ord(_k) == 224 or ord(_k) == 0:
            _k += console.utils.wait_key()

        return Key.dump()
    
    @classmethod
    def get_input(cls, prompt:str="", col:int=None, line:int=None, absolute:bool=True ) -> str:
        """
        Listens to the users input(alpha-numeric) and returns string after pressing the enter-Key 

        Returns:
            `str`: user inputted string
        """
        cur = Console.get_cursor()
        Console.set_cursor( col if col else cur[0], line if line else cur[1], absolute )
        
        res = ''
        try:
            res = input( prompt )
        except EOFError or KeyboardInterrupt:
            res = ''
        finally:
            Console.set_cursor( *cur, True )
            return res

    @classmethod
    def await_key(cls, *keys:Key|keyboard.Key|keyboard.KeyCode|str, timeout:int=None) -> bool:
        """
        block until the the Console detected the specified key (non strictly)

        if timeout is supplied this method only blocks at maximum as long as timeout, otherwise block indefinitely

        Args:
            key (`Key` | `keyboard.Key` | `keyboard.KeyCode` | `str`): key representative to be compared with the inputted `Key`
            timeout (`int`, optional): maximum time in seconds to block. Defaults to None.

        Returns:
            `bool`: `True` if supplied key was pressed within the timeout time (if provided), `False` if timeout was exceeded and the supplied key was not pressed
        """
        t0 = time()
        
        while (not timeout) or (time() - t0 <= timeout):
            k = cls.get_key()
            if any( key in k for key in keys ) :
                return True
        
        return False
    
    
    @classmethod
    @contextmanager
    def virtual_area(cls, left_top:tuple[int, int], right_bottom:tuple[int, int]=None, reset_cursor_on_exit:bool=True):
        """
        Virtually limit the terminal screen to a specific area
        
        On entering the context the cursor gets set to (0, 0) on the virtual terminal. On exiting the context the cursor gets restored to the position before entering iff `reset_cursor_on_exit` is set to `True`

        ---
        All methods of `Console` work as you'd expect but with the limited area
        
        e.g. writing at (0, 0) would actually write at the `left_top` position on the screen

        Args:
            left_top (`tuple`[`int`, `int`]): left-top position of virtual area (inclusive)
            right_bottom (`tuple`[`int`, `int`], optional): right-bottom position of virtual area (inclusive). Defaults to the console size.
            do_reset_cursor_on_exit (`bool`, optional): on exiting the virtual area set the cursor to the position it was on when entering the virtual area. Defaults True.

        Returns:
            `contextmanager`: `contextmanager`
        """
        right_bottom = right_bottom if right_bottom else cls.get_console_size()
        
        assert left_top[0] <= right_bottom[0] and left_top[1] <= right_bottom[1], f"incompatible corners: left_top must be smaller or equal to right_bottom"
        assert left_top[0] >= 0 and left_top[1] >= 0, f"incompatible left_top corner: left_top corner coordinates are {left_top[0]}, but both must be non-negative"
        
        col, line = cls.get_cursor()
        
        prev_screen_lt, prev_screen_rb = cls._get_screen_lt(), cls._get_screen_rb()
        
        # shift from local (virtual) coordinates to global
        left_top     = cls._transform_local_2_global( *left_top     )
        right_bottom = cls._transform_local_2_global( *right_bottom )
        
        cls.__screen_lt, cls.__screen_rb = left_top, right_bottom
        cls.__is_virtual = True
        cls.__virtual_depth += 1
        cls.set_cursor(0, 0)
        
        try:
            yield cls
        finally:
            cls.__screen_lt  = prev_screen_lt
            cls.__screen_rb  = prev_screen_rb

            cls.__virtual_depth -= 1
            cls.__is_virtual = cls.__virtual_depth > 0
            
            if reset_cursor_on_exit:
                cls.set_cursor( col, line, True )
    
    @classmethod
    def hidden_cursor(cls) -> _GeneratorContextManager[Screen]:
        """ Context Manager that hides the cursor and restores it on exit. """
        return sc.hidden_cursor()
    
    
    @classmethod
    def clear(cls) -> None:
        """ clears the terminal screen completely blank """
        if cls.__is_virtual:
            cls.clear_rectangle( cls._get_screen_lt(), cls._get_screen_rb() )
            return
        
        console.utils.cls()
    
    @classmethod
    def clear_rectangle(cls, left_top:tuple[int, int], right_bottom:tuple[int, int]) -> None:
        """
        clears a specified rectangular area

        left_top and right_bottom coordinates are inclusive, meaning they are part of the area to be cleared

        Args:
            left_top (`tuple`[`int`, `int`]): left-top corner of rectangle (in screen coordinates)
            right_bottom (`tuple`[`int`, `int`]): right-bottom corner of rectangle (in screen coordinates)
        """
        # clamp area to active area
        left_top, right_bottom = cls.clamp_area( left_top, right_bottom, (0, 0), cls.get_console_size() )
        
        width  = right_bottom[0] - left_top[0] + 1
        height = right_bottom[1] - left_top[1] + 1
        
        width  = max( 0, width )
        height = max( 0, height )
        
        empty_line = ' ' * width
        
        for line in range(height):
            cls.write_at( empty_line, left_top[0], left_top[1] + line, True )
    
    
    @classmethod
    def get_console_size(cls, *, true_terminal_size:bool=False) -> tuple[int, int]:
        """
        get the size of the printable area
        
        to get the absolute terminal size set true_terminal_size=True.
        It is recommended not to set this flag unless you absolutely intend to
        
        Returns:
            (`width`, `height`): `width` and `height` of the console if unsuccessful defaults to (-1, -1)
        """
        if true_terminal_size:
            return tuple( [v-1 for v in console.detection.get_size((1, 1))] )
        return (
            cls._get_screen_rb()[0] - cls._get_screen_lt()[0] + 1,
            cls._get_screen_rb()[1] - cls._get_screen_lt()[1] + 1,
        )
    
    
    @classmethod
    def _transform_local_2_global(cls, col:int, line:int) -> tuple[int, int]:
        """
        transform positions from the virtualized/local console-scope to the actual console-scope

        will clamp the position into the available space.
        
        Note: 
            if no virtual_area is active, the resulting position is the same as the inputted (clamped to the available console space)

        Args:
            col (`int`): column of the local position
            line (`int`): line of the local position

        Returns:
            `tuple[int, int]`: column, line in global coordinates
        """
        return cls.clamp_point( (col + cls._get_screen_lt()[0], line + cls._get_screen_lt()[1]), cls._get_screen_lt(), cls._get_screen_rb() )
    
    @classmethod
    def _transform_global_2_local(cls, col:int, line:int) -> tuple[int, int]:
        """
        transform positions from the global console-scope to the virtualized/local console-scope

        will clamp the position into the available space.
        
        Note: 
            if no virtual_area is active, the resulting position is the same as the inputted (clamped to the available console space)

        Args:
            col (`int`): column of the global position
            line (`int`): line of the global position

        Returns:
            `tuple[int, int]`: column, line in local coordinates
        """
        return cls.clamp_point( (col - cls._get_screen_lt()[0], line - cls._get_screen_lt()[1]), (0,0), cls.get_console_size() )

    
    @classmethod
    def _get_screen_lt(cls) -> tuple[int, int]:
        return cls.__screen_lt if cls.__is_virtual else (0, 0)

    @classmethod
    def _get_screen_rb(cls) -> tuple[int, int]:
        return cls.__screen_rb if cls.__is_virtual else cls.get_console_size(true_terminal_size=True)
    
    
    @staticmethod
    def clamp_point( point:tuple[int, int], bound_lt:tuple[int, int], bound_rb:tuple[int, int] ) -> tuple[int, int]:
        return (
            max( bound_lt[0], min( point[0], bound_rb[0] ) ),
            max( bound_lt[1], min( point[1], bound_rb[1] ) )
        )
    
    @staticmethod
    def clamp_area( area_lt:tuple[int, int], area_rb:tuple[int, int], bound_lt:tuple[int, int], bound_rb:tuple[int, int] ) -> tuple[ tuple[int, int], tuple[int, int] ]:
        return (
            Console.clamp_point( area_lt, bound_lt, bound_rb ),
            Console.clamp_point( area_rb, bound_lt, bound_rb ),
        )

    @classmethod
    def __set_cursor_no_clamp(cls, col:int, line:int, absolute:bool=True) -> None:
        """
        move the cursor to a specific position in the terminal w/o clamping the position
        
        Args:
            col (`int`): column position (x)
            line (`int`): line position (y)
            absolute (`bool`, optional): interpret (`col`, `line`) as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        c, l = (0, 0) if absolute else cls.get_cursor()

        col, line = col + c + cls._get_screen_lt()[0], line + l + cls._get_screen_lt()[1]
        
        assert col >= 0 and line >= 0, f"requested cursor position of ({col}, {line}) is invalid"
        
        cls.__stdout( sc.move_to( col, line ) )

    @classmethod
    def __stdout(cls, code:str) -> None:
        sys.stdout.write( code )
        sys.stdout.flush()


if __name__ == "__main__":
    Console.setup( "GUI Test" )
    Console.clear()
    Console.set_cursor( 0, 0 )
    
    # Testing Console =================================================================================================
    with Console.virtual_area( (1,1), (5,5), False ):
        w, h = Console.get_console_size()
        for l in range(h+1):
            for c in range(w+1):
                Console.set_cursor( c, l, True )
                Console.write( Console.get_key().get_char() )
    
    
    # Testing code snippets ============================================================================================
    
    # Testing Key listener ============================================================================================
    # from time import sleep
    
    # print( " === Quit with pressing > q < === ", '\n' )
    
    # k1 = Key( keyboard.Key.enter, keyboard.Key.ctrl )
    # kA = Key("a", keyboard.Key.shift )
    # kB = Key( "b" )
    # kc = "C"
    
    # while 1:
    #     sleep(0.01)
    #     key = Console.get_key()
        
    #     l = [
    #           k1 in key
    #         , kA in key
    #         , kB in key
    #         , kc in key
    #         , key.get_non_printable()
    #         , key.get_char()
    #         , key.info_str()
    #         , key.get_modifiers()
    #     ]
        
    #     print( (" {!s:>10s} |"*len(l)).format( *l ) )
        
    #     if key == "q":
    #         break

    Console.stop()