from __future__ import annotations
from typing     import Optional, Sequence, overload, Self, ClassVar, TypeVar
from time       import sleep, time
from enum       import Enum
from contextlib import contextmanager, _GeneratorContextManager

import re
import sys

try:
    from colors import *
except ImportError:
    def is_string(obj)                        : return isinstance( obj, str )
    def color(s, fg=None, bg=None, style=None): return s
    def strip_color(s)                        : return s
    def ansilen(s)                            : return len(s)
    COLORS = []
    STYLES = []

    
    print( "ansicolor is currently not installed" )
    print( "Ansicoloring is now deactivated" )
    print( "consider installing ansicolor via pip:" )
    print( "    pip install ansicolors" )
    print()


import console.detection
import console.utils
from   console.screen import sc, Screen

import pynput.keyboard as keyboard

T = TypeVar("T", int, float)
class Point():
    """ Simple 2-D Point """
    __slots__ = [ "x", "y" ]
    
    x: T
    y: T
    
    def __init__(self, x:T, y:T) -> None:
        self.x    = x
        self.y    = y
        self.col  = x
        self.line = y
    
    @property
    def T(self) -> tuple[T, T]:
        '''alias for (x, y)'''
        return ( self.x, self.y )
    
    
    @property
    def col(self) -> T:
        '''alias for x'''
        return self.x
    @col.setter
    def col(self, value: T) -> None:
        self.x = value
    
    @property
    def line(self) -> T:
        '''alias for y'''
        return self.y
    @line.setter
    def line(self, value: T) -> None:
        self.y = value
    
    
    def __add__(self, _o:tuple[T, T]|Point[T]) -> Point[T]:
        return Point( self.x + _o[0], self.y + _o[1] )
    __radd__ = __add__
    
    def __sub__(self, _o:tuple[T, T]|Point[T]) -> Point[T]:
        return Point( self.x - _o[0], self.y - _o[1] )
    def __rsub__(self, _o:tuple[T, T]|Point[T]) -> Point[T]:
        return self.__neg__().__add__(_o)
    
    def __neg__(self) -> Point[T]:
        return Point( -self.x, -self.y )
    
    def __eq__(self, _o:tuple[T, T]|Point[T]) -> bool:
        return self.x == _o[0] and self.y == _o[1]
    def __neq__(self, _o:tuple[T, T]|Point[T]) -> bool:
        return not self.__eq__(_o)
    
    def __lt__(self, _o:tuple[T, T]|Point[T]) -> bool:
        return self.x <= _o[0] and self.y < _o[1] or self.x < _o[0] and self.y <= _o[1]
    def __gt__(self, _o:tuple[T, T]|Point[T]) -> bool:
        return self.x >= _o[0] and self.y > _o[1] or self.x > _o[0] and self.y >= _o[1]
    
    def __le__(self, _o:tuple[T, T]|Point[T]) -> bool:
        return self.x <= _o[0] and self.y <= _o[1]
    def __ge__(self, _o:tuple[T, T]|Point[T]) -> bool:
        return self.x >= _o[0] and self.y >= _o[1]
    
    
    def __str__(self) -> str:
        return f"P({self.x}, {self.y})"
    def __repr__(self) -> str:
        return f"Point({self.x}, {self.y})"
    
    def __getitem__(self, ind:int) -> T:
        assert 0 <= ind <= 1, IndexError()
        return self.x if ind == 0 else self.y

    def __iter__(self):
        yield self.x
        yield self.y


class STYLE_TYPE( Enum ):
    none      = 'none'
    bold      = 'bold'
    faint     = 'faint'
    italic    = 'italic'
    underline = 'underline'
    blink     = 'blink'
    blink2    = 'blink2'
    negative  = 'negative'
    concealed = 'concealed'
    crossed   = 'crossed'
class Style:
    """
    colorize and stylize text with ansi escape codes

    Features the ability to handle encapsulated stylized strings correctly
    
    Example:
    >>> blue_Black = Style( "blue", "#000000" )
    >>> red_underline = Style( "red", styles=STYLE_TYPE.underline )
    >>> text = "normal " + blue_Black.apply( "blue, ", red_underline.apply("red, "), "blue again, " ) + "normal again"
    >>> Console.write( text )
    """
    _colors_regex: ClassVar[re.Pattern] = re.compile( r"((\x1b|\033)\[\d{1,3}(;\d{1,3})*m)[\s\S]+?((\x1b|\033)\[0m)" )
    _csi_regex   : ClassVar[re.Pattern] = re.compile( r"\x1b\[(K|.*?m)" )

    csi_reset : ClassVar[str] = "\x1b[0m"
    csi_format: str
    
    fg    : Optional[ int | str ]
    bg    : Optional[ int | str ]
    styles: Optional[ STYLE_TYPE | list[STYLE_TYPE] ]
    
    @staticmethod
    def default() -> Style:
        """default Style, i.e. the ansi code which does unset all styles and colors and sets the terminals default"""
        return Style(styles=STYLE_TYPE.none)
    
    
    def __init__(self, fg:int|str=None, bg:int|str=None, styles:STYLE_TYPE|list[STYLE_TYPE]=None):
        """
        create a style of a foreground and background color and special style type

        colors can be either:
        - an `int` as an index into the terminals (3-bit/8-bit) color palette; or
        - a 24-bit RGB color of the format `#RRGGBB`

        Args:
            fg (`int | str`, optional): foreground color. Defaults to the terminals default color.
            bg (`int | str`, optional): background color. Defaults to the terminals default color.
            styles (`STYLE_TYPE | list[STYLE_TYPE]`, optional): combination or none special effects/styles. Defaults to no style.
        """
        # https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
        self.fg = fg
        self.bg = bg
        self.styles = styles
        self.csi_format = Style.csi_code( fg, bg, styles, True )
    
    def apply(self, *strings:str, sep:str=' ') -> str:
        """
        applies the coloring and stylizing to a set of strings.

        style codes inside the supplied strings are detected and correctly encoded
        in the surrounding style

        Returns:
            `str`: a stylized string of the supplied strings
        """
        text = sep.join( map( str, strings ) )
        
        formatted_text = text
        
        for match in Style._colors_regex.finditer( text ):
            # not yet optimized; necessary?
            formatted_text = text.replace( match.group(), match.group()[:-4] + self.csi_format, 1 )
        
        return self.csi_format + formatted_text + Style.csi_reset
    
    @staticmethod
    def csi_code( fg:int|str=None, bg:int|str=None, styles:STYLE_TYPE|list[STYLE_TYPE]=None, force_clean:bool=False ) -> str:
        """
        Generates the escape code sequence for the specified styling and color scheme

        the generated escape sequence can directly be written to the terminal

        Args:
            fg (`int | str`, optional): foreground color. Defaults to the default foreground color.
            bg (`int | str`, optional): background color. Defaults to the default background color.
            styles (`str`, optional): selection of styles of `STYLES`. Defaults to no style.
            force_clean (`bool`, optional): put a reset csi code before the formatted csi, to force a clean csi formatting.

        Raises:
            ValueError: if any of the supplied `styles` is not equal to one of the predefined `STYLES`

        Returns:
            `str`: escape code sequence to be printed to the terminal
        """
        sty: str = None
        
        if   isinstance( styles, STYLE_TYPE ): sty = styles.value
        elif isinstance( styles, list ):  sty = '+'.join( [ s.value for s in styles ] )
        else:                             sty = styles
        
        escaped = color( "", fg, bg, sty )
        
        # add reset code to csi code
        if force_clean:
            # csi already contains reset code
            if escaped[:3] == "\x1b[0":
                return escaped
            else:
                escaped = escaped[:2] + "0;" + escaped[2:]
        
        # color adds a reset escape sequence of 4 bytes at the end, which we remove
        return escaped[ :-4 ]

    @staticmethod
    def truncate_printable( color_coded_text:str, printable_width:int ) -> str:
        """
        truncate a string with style codes to a given width of printable characters

        useful to truncate a stylized text to fit in a given width in the terminal

        Args:
            color_coded_text (`str`): (stylized) string to be truncated
            printable_width (`int`): width to be filled with printable characters

        Returns:
            `str`: stylized truncated string
        """
        printable_text:str = Style._csi_regex.sub( '', color_coded_text )
        
        if len(printable_text) <= printable_width:
            return color_coded_text
        
        out_str = printable_text[:printable_width]
        matches = list( Style._csi_regex.finditer( color_coded_text ) )
        
        width_add = 0
        for m in matches:
            if m.start() > printable_width + width_add:
                break
            
            out_str = out_str[:m.start()] + m.group() + out_str[m.start():]
            width_add += len( m.group() )
        
        return out_str


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
    __listener: ClassVar[ keyboard.Listener ] = None
    
    __is_virtual   : ClassVar[ bool ] = False
    __virtual_depth: ClassVar[ int  ] = 0
    
    __screen_lt: ClassVar[ Point[int] ] = Point(0, 0)
    __screen_rb: ClassVar[ Point[int] ] = None
    
    __applied_style: ClassVar[ Style ] = Style.default
    
    @classmethod
    def setup(cls, title:Optional[str]=None) -> None:
        """ call setup before using the Console """
        
        console.utils.set_title( title, 0 )

        cls.__is_virtual    = False
        cls.__virtual_depth = 0
        
        cls.__screen_lt = Point(0, 0)
        cls.__screen_rb = cls.get_console_size()
        
        cls.__applied_style = Style.default
        
        cls.__listener = keyboard.Listener(
            on_press=Key.press,
            on_release=Key.release
        )
        cls.__listener.start()
        cls.__listener.wait()
        
        cls.rest_style()
    
    @classmethod
    def stop(cls) -> None:
        """ call stop after using the Console """
        cls.rest_style()
        cls.__listener.stop()
        cls.show_cursor()
    
    
    #---------------------#
    #  Writing functions  #
    #---------------------#
    @classmethod
    def write(cls, *args:object, sep:str=" ") -> None:
        """ writes to terminal at current cursor position """
        
        if cls.__applied_style.csi_format != Style.csi_reset:
            str_args = cls.__applied_style.apply( *args, sep=sep )
        else:
            str_args = sep.join( map(str, args) )
        
        arg_lines = str_args.splitlines()
        
        if not cls.__is_virtual: # simply use stdout
            cls.__stdout( str_args, True )
            return
        
        
        # normally '\n' at the beginning of a string will be kept
        # if str_args.startswith('\n'):
        #     arg_lines = [''] + arg_lines
        
        if str_args.endswith('\n'):
            arg_lines += ['']
        
        width, height = cls.get_console_size().T
        for i, line in enumerate(arg_lines):
            line_buffer = line
            
            while True:
                avail_width = width - cls.get_cursor().col
                
                out_str = Style.truncate_printable( line_buffer, avail_width )
                
                cls.__stdout( out_str )

                if cls.get_cursor().col == width:
                    # cls.__set_cursor_no_clamp( 0, cls.get_cursor()[1]+1 ) # should be wrong
                    cls.set_cursor( 0, cls.get_cursor().line+1 )
                
                line_buffer = line_buffer[len(out_str):]
                
                if not line_buffer:
                    break
            
            if i != len(arg_lines) - 1:
                # cls.__set_cursor_no_clamp( 0, cls.get_cursor()[1]+1 ) # should be wrong
                cls.set_cursor( 0, cls.get_cursor().line+1 )
        
        cls.__flush()
    
    @classmethod
    def write_line(cls, *args:str, sep:str=" ") -> None:
        """ writes to terminal at current cursor position and starts a new line """
        cls.write( sep.join( map(str, args) ), "\n", sep='' )
    
    @classmethod
    def write_at(cls, msg:str, col_line:tuple[int, int]|Point[int], absolute:bool=True) -> None:
        """
        write the given string at the specified position in the terminal
        
        Args:
            msg (`str`): text to be printed
            col_line (`tuple[int, int]|Point[int]`): position
            absolute (`bool`, optional): interpret (`col`, `line`) as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        p = Point(0, 0) if absolute else cls.get_cursor()
        
        col_line = cls._transform_local_2_global( Point(*col_line) + p )
        
        with sc.location( col_line.line, col_line.col ):
            cls.write( msg )
    
    @classmethod
    def write_in(cls, msg:str, col_line:tuple[int, int]|Point[int], end_col_line:tuple[int, int]|Point[int]=None, absolute:bool=True, clear_area:bool=True) -> None:
        """
        write the given string at the specified position in the terminal, but clear the area from (col, line) to (end_col, end_line) before writing
        
        if end_col_line is `None`: 
        - end_col_line[0] will be set to the most right column position of the terminal
        - end_col_line[1] will be set to the same line as specified
        
        Args:
            msg (`str`): text to be printed
            col_line (`Point[int]`): area start position
            end_col_line (`Point[int]`): area end position
            absolute (`bool`, optional): interpret (`col`, `line`) as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        p  = Point(0, 0) if absolute else cls.get_cursor()
        col_line = Point(*col_line) + p
        
        if not absolute and end_col_line:
            end_col_line = Point(*end_col_line) + p
        
        end_col_line = Point(*end_col_line) if end_col_line else Point( cls.get_console_size().col, col_line.line )
        
        with cls.virtual_area( col_line, end_col_line ):
            if clear_area:
                cls.clear()
            cls.write(msg)
    
    
    #---------------------#
    #  Styling functions  #
    #---------------------#
    @classmethod
    @overload
    def set_style(cls, style: Style ) -> Self:
        """
        Set the style of the cursor to be applied for all strings written to the Console after this
        
        Args:
            style (`Style`): predefined style

        Returns:
            `Self`: returns itself for monad programming style
        """
        ...
    @classmethod
    @overload
    def set_style(cls, fg:int|str=None, bg:int|str=None, styles:STYLE_TYPE|list[STYLE_TYPE]=None ) -> Self: 
        """
        Set the style of the cursor to be applied for all strings written to the Console after this

        colors can be either:
            - an `int` as an index into the terminals (3-bit/8-bit) color palette; or
            - a 24-bit RGB color of the format `#RRGGBB`

        Args:
            fg (`int | str`, optional): foreground color. Defaults to the terminals default color.
            bg (`int | str`, optional): background color. Defaults to the terminals default color.
            styles (`STYLE_TYPE | list[STYLE_TYPE]`, optional): combination or none special effects/styles. Defaults to no style.
        
        Returns:
            `Self`: returns itself for monad programming style
        """
        ...
    @classmethod
    def set_style(cls, fg_or_style:int|str|Style=None, bg:int|str=None, styles:STYLE_TYPE|list[STYLE_TYPE]=None ) -> Self:
        if isinstance( fg_or_style, Style ):
            cls.__applied_style = fg_or_style
        elif fg_or_style == None and bg == None and styles == None:
            pass
        else:
            cls.__applied_style = Style( fg_or_style, bg, styles )
        
        return cls

    @classmethod
    def rest_style(cls) -> Self:
        """ resets the style to the terminals default style """
        return cls.set_style( Style.default() )

    @classmethod
    @contextmanager
    @overload
    def stylized(cls, style: Style ):
        """
        Context which applies a style to all strings written to `Console` inside of the context

        restores the previous style after on leaving the context

        Args:
            style (`Style`): predefined style to be applied in the context
        """
        ...
    @classmethod
    @contextmanager
    @overload
    def stylized(cls, fg:int|str=None, bg:int|str=None, styles:STYLE_TYPE|list[STYLE_TYPE]=None):
        """
        Context which applies a style to all strings written to `Console` inside of the context

        restores the previous style after on leaving the context

        Args:
            fg (`int | str`, optional): foreground color. Defaults to the terminals default color.
            bg (`int | str`, optional): background color. Defaults to the terminals default color.
            styles (`STYLE_TYPE | list[STYLE_TYPE]`, optional): combination or none special effects/styles. Defaults to no style.
        """
        ...
    @classmethod
    @contextmanager
    def stylized(cls, fg_or_style:int|str|Style=None, bg:int|str=None, styles:STYLE_TYPE|list[STYLE_TYPE]=None):
        old_style = cls.__applied_style
        cls.set_style( fg_or_style, bg, styles )
        try:
            yield cls
        finally:
            # cls.rest_style() # prob unnecessary
            cls.set_style( old_style )
    
    
    #-----------------------------#
    #  Cursor position functions  #
    #-----------------------------#
    @classmethod
    def get_cursor(cls, *, true_cursor_pos:bool=False) -> Point[int]:
        """
        left upper corner is (0, 0)
        
        Returns:
            `Point[int]`: position of the cursor if unsuccessful defaults to Point(0, 0)
        """
        p = Point( *console.detection.get_position() )
        p = p - (1,1)
        
        if true_cursor_pos:
            return p
        
        return cls._transform_global_2_local( p )
    
    @classmethod
    def set_cursor(cls, col:int, line:int, *, absolute:bool=True) -> None:
        """
        move the cursor to a specific position in the terminal
        
        Args:
            col (`int`): cursor column position
            line (`int`): cursor line position
            absolute (`bool`, optional): interpret (`col`, `line`) as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        ...
    @classmethod
    def set_cursor(cls, col_line:Point[int], *, absolute:bool=True) -> None:
        """
        move the cursor to a specific position in the terminal
        
        Args:
            col_line (`Point[int]`): cursor position
            absolute (`bool`, optional): interpret the cursor position as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        ...
    @classmethod
    def set_cursor(cls, col_point:int|Point[int], line:int=None, *, absolute:bool=True) -> None:
        """ move the cursor to a specific position in the terminal """
        
        col_line: Point
        if isinstance( col_point, int ) and isinstance( line, int ):
            col_line = Point( col_point, line )
        elif isinstance( col_point, Point ):
            col_line = col_point
        else:
            raise TypeError( f"Arguments of types ({type(col_point), type(line)}) are an invalide combination" )
        
        p = Point(0, 0) if absolute else cls.get_cursor()

        col_line = cls._transform_local_2_global( col_line + p )
        
        cls.__stdout( sc.move_to( *col_line.T ), True )
    
    @classmethod
    def hide_cursor(cls) -> None:
        """ hide the cursor symbol on the screen """
        cls.__stdout( sc.hide_cursor, True )
    
    @classmethod
    def show_cursor(cls) -> None:
        """ show the cursor symbol on the screen """
        cls.__stdout( sc.show_cursor, True )
    
    
    #--------------#
    #  Key events  #
    #--------------#
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
        Console.set_cursor( col if col else cur.col, line if line else cur.line, absolute=absolute )
        
        res = ''
        try:
            res = input( prompt )
        except EOFError or KeyboardInterrupt:
            res = ''
        finally:
            Console.set_cursor( cur, absolute=True )
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
    def virtual_area(cls, left_top:tuple[int,int], right_bottom:tuple[int,int]=None, reset_cursor_on_exit:bool=True):
        """
        Virtually limit the terminal screen to a specific area
        
        On entering the context the cursor gets set to (0, 0) on the virtual terminal. On exiting the context the cursor gets restored to the position before entering iff `reset_cursor_on_exit` is set to `True`

        ---
        All methods of `Console` work as you'd expect but with the limited area
        
        e.g. writing at (0, 0) would actually write at the `left_top` position on the screen

        Args:
            left_top (`tuple[int,int]`): left-top position of virtual area (inclusive)
            right_bottom (`tuple[int,int]`, optional): right-bottom position of virtual area (inclusive). Defaults to the console size.
            do_reset_cursor_on_exit (`bool`, optional): on exiting the virtual area set the cursor to the position it was on when entering the virtual area. Defaults True.

        Returns:
            `contextmanager`: `contextmanager`
        """
        ...
    @classmethod
    @contextmanager
    def virtual_area(cls, left_top:Point[int], right_bottom:Point[int]=None, reset_cursor_on_exit:bool=True):
        """
        Virtually limit the terminal screen to a specific area
        
        On entering the context the cursor gets set to (0, 0) on the virtual terminal. On exiting the context the cursor gets restored to the position before entering iff `reset_cursor_on_exit` is set to `True`

        ---
        All methods of `Console` work as you'd expect but with the limited area
        
        e.g. writing at (0, 0) would actually write at the `left_top` position on the screen

        Args:
            left_top (`Point[int]`): left-top position of virtual area (inclusive)
            right_bottom (`Point[int]`, optional): right-bottom position of virtual area (inclusive). Defaults to the console size.
            do_reset_cursor_on_exit (`bool`, optional): on exiting the virtual area set the cursor to the position it was on when entering the virtual area. Defaults True.

        Returns:
            `contextmanager`: `contextmanager`
        """
        ...
    @classmethod
    @contextmanager
    def virtual_area(cls, left_top:Point[int]|tuple[int,int], right_bottom:Point[int]|tuple[int,int]=None, reset_cursor_on_exit:bool=True):
        """
        Virtually limit the terminal screen to a specific area
        
        On entering the context the cursor gets set to (0, 0) on the virtual terminal. On exiting the context the cursor gets restored to the position before entering iff `reset_cursor_on_exit` is set to `True`

        ---
        All methods of `Console` work as you'd expect but with the limited area
        
        e.g. writing at (0, 0) would actually write at the `left_top` position on the screen
        """
        left_top     = Point( *left_top )
        right_bottom = Point( *right_bottom ) if right_bottom else cls.get_console_size()
        
        assert left_top.col <= right_bottom.col and left_top.line <= right_bottom.line, f"incompatible corners: left_top must be smaller or equal to right_bottom"
        assert left_top.col >= 0 and left_top.line >= 0, f"incompatible left_top corner: left_top corner coordinates are {left_top}, but both must be non-negative"
        
        cursor = cls.get_cursor()
        
        prev_screen_lt, prev_screen_rb = cls._get_screen_lt(), cls._get_screen_rb()
        
        # shift from local (virtual) coordinates to global
        left_top     = cls._transform_local_2_global( left_top     )
        right_bottom = cls._transform_local_2_global( right_bottom )
        
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
                cls.set_cursor( cursor, absolute=True )
    
    @classmethod
    def hidden_cursor(cls) -> _GeneratorContextManager[Screen]:
        """ Context Manager that hides the cursor and restores it on exit. """
        return sc.hidden_cursor()
    
    
    @classmethod
    def clear(cls) -> None:
        """ clears the terminal screen completely blank """
        if cls.__is_virtual:
            cs = cls.get_console_size()
            cls.clear_rectangle( Point(0,0), cs - (1,1) )
            return
        
        console.utils.cls()
    
    @classmethod
    def clear_rectangle(cls, left_top:Point[int], right_bottom:Point[int]) -> None:
        """
        clears a specified rectangular area

        left_top and right_bottom coordinates are inclusive, meaning they are part of the area to be cleared

        Args:
            left_top (`Point[int]`): left-top corner of rectangle (in screen coordinates)
            right_bottom (`Point[int]`): right-bottom corner of rectangle (in screen coordinates)
        """
        # clamp area to active area
        cs = cls.get_console_size()
        left_top, right_bottom = cls.clamp_area( left_top, right_bottom, Point(0, 0), cs - (1,1) )
        
        delta = right_bottom - left_top
        width  = max( 0, delta.col  + 1 )
        height = max( 0, delta.line + 1 )
        
        empty_line = ' ' * width
        
        for line in range(height):
            cls.write_at( empty_line, left_top + (0, line), True )
    
    
    @classmethod
    def get_console_size(cls, *, true_terminal_size:bool=False) -> Point[int]:
        """
        get the size of the printable area
        
        to get the absolute terminal size set true_terminal_size=True.
        It is recommended not to set this flag unless you absolutely intend to
        
        Returns:
            `Point[int]`: size of the console if unsuccessful defaults to Point(-1, -1)
        """
        if true_terminal_size:
            return Point( *console.detection.get_size((1, 1)) ) - (1,1)
        
        return cls._get_screen_rb() - cls._get_screen_lt() + (1,1)
    
    
    #-----------------------------#
    #  helper and util functions  #
    #-----------------------------#
    
    @classmethod
    def _transform_local_2_global(cls, col_line:Point[int]) -> Point[int]:
        """
        transform positions from the virtualized/local console-scope to the actual console-scope

        will clamp the position into the available space.
        
        Note: 
            if no virtual_area is active, the resulting position is the same as the inputted (clamped to the available console space)

        Args:
            col_line (`Point[int]`): position in local coordinates
        
        Returns:
            `Point[int]`: position in global coordinates
        """
        return cls.clamp_point(
            col_line + cls._get_screen_lt(),
            cls._get_screen_lt(),
            cls._get_screen_rb()
        )
    @classmethod
    def _transform_global_2_local(cls, col_line:Point[int]) -> Point[int]:
        """
        transform positions from the global console-scope to the virtualized/local console-scope

        will clamp the position into the available space.
        
        Note: 
            if no virtual_area is active, the resulting position is the same as the inputted (clamped to the available console space)

        Args:
            col_line (`Point[int]`): position in global coordinates
        
        Returns:
            `Point[int]`: position in local coordinates
        """
        return cls.clamp_point(
            col_line - cls._get_screen_lt(),
            Point(0,0),
            cls.get_console_size()
        )

    
    @classmethod
    def _get_screen_lt(cls) -> Point[int]:
        return cls.__screen_lt if cls.__is_virtual else Point(0, 0)
    @classmethod
    def _get_screen_rb(cls) -> Point[int]:
        return cls.__screen_rb if cls.__is_virtual else cls.get_console_size(true_terminal_size=True)
    
    
    @staticmethod
    def clamp_point( point:Point[int], bound_lt:Point[int], bound_rb:Point[int] ) -> Point[int]:
        """
        clamp a given 2D point inside a defined bound-box

        Args:
            point (`Point[int]`): point to be clamped
            bound_lt (`Point[int]`): bound-box left-top corner position
            bound_rb (`Point[int]`): bound-box right-bottom corner position

        Returns:
            `Point[int]`: clamped point
        """
        return Point(
            max( bound_lt.col , min( point.col , bound_rb.col  ) ),
            max( bound_lt.line, min( point.line, bound_rb.line ) )
        )
    @staticmethod
    def clamp_area( area_lt:Point[int], area_rb:Point[int], bound_lt:Point[int], bound_rb:Point[int] ) -> tuple[ Point[int], Point[int] ]:
        """
        clamp a given rectangular area inside a defined bound-box

        Args:
            area_lt (`Point[int]`): rectangular areas left-top corner to be clamped
            area_rb (`Point[int]`): rectangular areas right-bottom corner to be clamped
            bound_lt (`Point[int]`): bound-box left-top corner position
            bound_rb (`Point[int]`): bound-box right-bottom corner position

        Returns:
            `tuple[ Point[int], Point[int] ]`: clamped area
        """
        return (
            Console.clamp_point( area_lt, bound_lt, bound_rb ),
            Console.clamp_point( area_rb, bound_lt, bound_rb ),
        )

    @classmethod
    def __set_cursor_no_clamp(cls, col_line:Point[int], absolute:bool=True) -> None:
        """
        move the cursor to a specific position in the terminal w/o clamping the position
        
        Args:
            col_line (`Point[int]`): cursor position
            absolute (`bool`, optional): interpret (`col`, `line`) as `absolute` position in the Console or as relative (`not absolute`) positions to the current cursor position. Defaults to True.
        """
        p = Point(0, 0) if absolute else cls.get_cursor()

        col_line = col_line + p + cls._get_screen_lt()
        
        assert col_line.col >= 0 and col_line.line >= 0, f"requested cursor position of {col_line} is invalid"
        
        cls.__stdout( sc.move_to( *col_line ), True )

    @classmethod
    def __flush(cls) -> None:
        sys.stdout.flush()
    @classmethod
    def __stdout(cls, code:str, flush:bool=False) -> None:
        sys.stdout.write( code )
        
        if flush:
            cls.__flush()


if __name__ == "__main__":
    Console.setup( "GUI Test" )
    Console.clear()
    Console.set_cursor( 0, 0 )
    
    # Testing Colors =================================================================================================
    # Console.write_line( "This is default" )
    # Console.set_style( "black", "white" )
    # Console.write_line( "This is inverted" )
    # Console.write_line( Style("black", "white").apply("This is also inverted") )
    # Console.rest_style()
    
    # with Console.virtual_area( (5,5), (25, 20) ):
    #     with Console.stylized( "white", "#00aaaa" ): Console.clear()
    #     with Console.stylized( styles=STYLE_TYPE.negative )              : sleep(1); Console.write_line( "This is inverted" )
    #     with Console.stylized( "green", None, STYLE_TYPE.bold )          : sleep(1); Console.write_line( "This is in bold green" )
    #     with Console.stylized( "blue", None, STYLE_TYPE.crossed )        : sleep(1); Console.write_line( "This is in crossed blue", Style("yellow", "black", STYLE_TYPE.blink).apply(", this is blinking yellow"), " and this is crossed blue again" )
    #     with Console.stylized( "red", None, STYLE_TYPE.underline )       : sleep(1); Console.write_line( "This is in underlined red" )
    #     with Console.stylized( "#ff00ff", "black", STYLE_TYPE.underline ): sleep(1); Console.write_line( "This is in underlined bold magenta" )
    
    # Console.set_cursor( 0, 20 )
    # Console.write_line( "This is default" )
    
    # Testing Console =================================================================================================
    with Console.virtual_area( (0,0), (10,2), False ):
        w, h = Console.get_console_size()
        Console.write( w, h, sep="" )
        for l in range(h):
            for c in range(w):
                Console.set_cursor( c, l, absolute=True )
                Console.write( Console.get_key().get_char() )
    
    
    # Testing code snippets ===========================================================================================
    
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