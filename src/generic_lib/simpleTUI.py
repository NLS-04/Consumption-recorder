from __future__      import annotations
from collections.abc import Mapping
from typing          import Self, Protocol, Callable, Sequence, Optional, \
                            TypeVar, Final, final, runtime_checkable, overload, Any

from enum     import Enum, auto
from math     import floor, sqrt
from datetime import date
from textwrap import fill

import inspect


from generic_lib.logger    import get_logger, logging
from generic_lib.consoleIO import Console, Key, keyboard
from generic_lib.utils     import *
from constants             import *


#----------------------------------------------------------------------------------------------------------------------
# Manage Logging
#----------------------------------------------------------------------------------------------------------------------

class _adapter( logging.LoggerAdapter ):
    lines_to_class_name: dict[ tuple[int, int], str ]
    
    def __init__(self, logger: Any, extra: Mapping[str, object] | None = {}) -> None:
        super().__init__(logger, extra)
        self.lines_to_class_name = dict()
    
    def process(self, msg, kwargs):
        # Debug print
        # print( *[ "{:>4d} | {:>25s} | {:>10s} | {:s}".format(fi.lineno, '\\'.join(fi.filename.split('\\')[-2:]), fi.function, fi.code_context[0].strip()) for fi in inspect.stack()], sep='\n', end='\n\n' )
        
        frame = inspect.currentframe().f_back.f_back.f_back
        
        class_name = self.get_class_name( frame.f_lineno )
        del frame
        
        if class_name:
            class_name += '.'
        
        # self.extra can be used to communicate information from adapters to the logger
        self.extra['class_name'] = class_name
        
        return super().process( msg, kwargs )
    
    def get_class_name( self, line:int ) -> str:
        out: list[ tuple[tuple[int, int], str] ] = list( filter( lambda items: items[0][0] <= line <= items[0][1], self.lines_to_class_name.items() ) )
        
        return out.pop(0)[1] if out else ""

    def remember_class(self, cls):
        lines, start_index = inspect.getsourcelines( cls )
        
        self.lines_to_class_name |= { (start_index+1, start_index+len(lines)-1): cls.__name__ }
        
        return cls

LOGGER = get_logger( PATH_LOGS, "debug_Frames", _adapter, identifier = lambda r: r.class_name + r.funcName )


#----------------------------------------------------------------------------------------------------------------------
# Code - Library
#----------------------------------------------------------------------------------------------------------------------
# Helper #
#--------#
T = TypeVar("T", int, float)
class Point():
    __slots__ = [ "x", "y", "col", "line" ]
    
    x: T
    y: T
    
    col : T
    '''alias for x'''
    line: T
    '''alias for y'''
    
    def __init__(self, x:T, y:T) -> None:
        self.x    = x
        self.y    = y
        self.col  = x
        self.line = y
    
    @property
    def T(self) -> tuple[T, T]:
        '''alias for (x, y)'''
        return ( self.x, self.y )
    
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

@LOGGER.remember_class
class Result():
    __success: bool
    
    __data: dict[str, Optional[object]]
    
    def __init__(self, success:bool, _name_results_dict:dict[str, Optional[object]]) -> None:
        self.__success = success
        self.__data  = _name_results_dict
        
        LOGGER.info( self.__str__() )
    
    @property
    def success(self) -> bool:
        return self.__success
    
    @property
    def data(self) -> list[Optional[object]]:
        return list( self.__data.values() )
    
    def __iter__(self):
        for val in self.__data.values():
            yield val
    
    def __getitem__(self, name_or_index:str|int) -> Optional[object]:
        assert isinstance( name_or_index, (str, int) ), f"key must be of type `int` or `str` and not of type {type(name_or_index)}"
        
        if isinstance( name_or_index, str ):
            assert name_or_index in self.__data, f"Interactable of name: \"{name_or_index}\" is not part of this Manager's result. All Valid names are: {[k for k in self.__data]}"
            return self.__data[name_or_index]

        return self.__data[ list(self.__data.keys())[name_or_index] ]

    def __str__(self) -> str:
        max_width = max_width_of_strings( self.__data.keys() )[1]
        fmt = "{:>%ds} | {:}" % ( max_width )
        return\
            f"successful = {self.__success}"\
            + "\n\t".join(
                ['', fmt.format("Names", "Results")] 
                + [
                    "\n\t".join( [fmt.format(k, str(v).splitlines()[0])] + [fmt.format("", vv) for vv in str(v).splitlines()[1:]] )
                    for k, v 
                    in (self.__data.items() if self.__data else [('None', 'None')] )
                ]
            )

    __repr__ = __str__
#---------------------#
# Registerable helper #
#---------------------#
@final
@LOGGER.remember_class
class Register():
    # why use id instead of the index? 
    #   ==> Security! It is safer since only objects that call with the correct object instance can set a value for that object. 
    #       YES! It is still possible to get around this barrier, but it is definitely not like to happen on accident
    
    __id_manager: int = -1

    __frames: list[Registerable] = []
    
    __lookup_frames: dict[int, Registerable] = dict()
    '''dict[ id, registerable_of_id ]'''
    
    
    __register: dict[int, object] = dict()
    '''dict[ id, data ]'''
    
    __rule_set: dict[int, list[tuple[int, object]]] = dict()
    '''dict[ id_tx: list[ (id_rx, func) ] ]'''

    __revert_register: dict[int, dict[int, list[str]]] = dict()
    '''dict[ id_tx: list[ (id_rx, data_list) ] ]'''
    

    @classmethod
    def set_rule(cls, transceiver:int|str, receiver:int|str, tx_transform_function: Callable[[list[str]], tuple[bool, list[str]]]) -> Register:
        """
        set transceive and receive instructions 
        
        set these instructions *after* at least the `transceiver` and `receiver` `Focus_Input` objects are appended to the `Focus_Manager`

        Args:
            receiver (`int`|`str`): index or prompt title name of the receiving focus
            transceiver (`int`|`str`): index or prompt title name of the transceiving focus
            tx_transform_function (`(list[str]) -> tuple[bool, list[str]]`): takes the backend data (the `list`[`str`]) as parameter and should return a `tuple`[should_send:`bool`, transformed_data_for_receiver:`list`[`str`] ]

        Returns:
            `Register`: monad design
        """
        foc_tx = cls.__frames[ cls._map_to_index( transceiver ) ]
        foc_rx = cls.__frames[ cls._map_to_index( receiver ) ]
        
        test_run = tx_transform_function( foc_tx.get_data() )
        assert isinstance(test_run, tuple)      \
           and isinstance(test_run[0], bool)    \
           and all( [ isinstance(char, str) for char in test_run[1] ] ), \
           f"func returns: {type(test_run)} instead of `tuple`[`bool`, `list`[`str`]]"
        
        id_tx = id(foc_tx)
        id_rx = id(foc_rx)
        
        if not id_tx in cls.__rule_set:
            cls.__rule_set |= { id_tx: [] }
            
        cls.__rule_set[id_tx].append( (id_rx, tx_transform_function) )
        
        LOGGER.debug(f"new rule {transceiver} -> {receiver}")
        return cls
    
    @classmethod
    def transceive(cls, caller_frame:Registerable) -> None:
        """ transceive to all previously set Focuses where the transceiver is same as the caller_focus, except for the Focus_Manager he can initiate all transceivings """
        id_foc = id(caller_frame)
        
        if id_foc == cls.__id_manager:
            for id_tx in cls.__rule_set.keys():
                cls.__transmit_rule( id_tx )
        
        elif id_foc in cls.__rule_set:
            cls.__transmit_rule( id_foc )
        
    
    @classmethod
    def revert(cls, caller_frame:Registerable) -> None:
        """ revert/undo all previously set data-lists of the Focuses where the transceiver is same as the caller_focus, except for the Focus_Manager he can revert all Focuses """
        id_foc = id(caller_frame)
        
        if id_foc == cls.__id_manager:
            for id_tx in cls.__rule_set.keys():
                cls.__revert_rule( id_tx )
            return
        
        if id_foc in cls.__rule_set:
            cls.__revert_rule( id_foc )
        
    
    @classmethod
    def reset(cls) -> None:
        cls.__id_manager      = -1
        cls.__frames          = []
        cls.__lookup_frames   = dict()
        cls.__register        = dict()
        cls.__rule_set        = dict()
        cls.__revert_register = dict()
        LOGGER.info( "rested to default values" )
    
    @classmethod
    def set_manager(cls, manager:Manager) -> None:
        assert isinstance( manager, Manager ), f"the supplied manager was of type {type(manager)} but MUST be of type Manager"
        assert cls.__id_manager == -1, "An manager has already been set"
        
        cls.__id_manager = id( manager )
    
    @classmethod
    def append(cls, focus:Registerable) -> None:
        """
        ! should only be used by `Focus_Manager` !

        append a focus to the Register
        
        Focuses must be append in the same order like they were to the `Focus_Manager`

        Args:
            focus (`Focus_Input`): focus
        """
        cls.__frames.append( focus )
        cls.__lookup_frames |= { id(focus): focus }
        cls.__register      |= { id(focus): None }
    
    @classmethod
    def set( cls, focus:Registerable, data:object ) -> None:
        """
        ! should only be used by objects and children of `Focus_Input` !
        
        set a value for a specific focus

        must call with actual focus instance for authentication

        Args:
            focus (`Focus_Input`): _description_
            data (`object`): _description_
        """
        cls.__register[ id(focus) ] = data
    
    @classmethod
    def get( cls, focus:int|str ) -> object:
        """
        ! should only be used by objects and children of `Focus_Input` !
        
        get the data in the register of the focus with the specified index or name

        (ordered by `.append` hierarchy in the Manager)

        Args:
            index (`int`|`str`): focus with the specified index or name

        Returns:
            `object`: data in the registry of the specified focus. Defaults to None
        """
        return cls.__register.get( id(cls.__frames[cls._map_to_index(focus)]), None )
    
    @classmethod
    def info_str(cls) -> str:
        return '{\n' + '\n'.join( [ f"{k:>10d}: {str(v) if v else ''}" for k, v in cls.__register.items() ] ) + '\n}'
    
    @classmethod
    def _map_to_index(cls, foc:int|str) -> int:
        list_of_focus_names = list(map( lambda f: f.get_name(), cls.__frames ))
        
        assert isinstance( foc, int ) and 0 <= foc <= len(cls.__frames) or isinstance(foc, str) and foc in list_of_focus_names, f"supplied focus reference (= {foc}) is either of wrong type or incorrect value"
        
        return foc if isinstance(foc, int) else next( i for i, n in enumerate(list_of_focus_names) if n == foc )

    @classmethod
    def __transmit_rule(cls, id_tx:int) -> None:
        assert id_tx in cls.__rule_set.keys(), "The supplied id has no registered rule to transmit"
        
        for id_rx, func in cls.__rule_set[id_tx]:
            foc_tx = cls.__lookup_frames[id_tx]
            foc_rx = cls.__lookup_frames[id_rx]
            
            do_send, data_list_str = func( foc_tx.get_data() )
            
            if not do_send:
                return
            
            if not id_tx in cls.__revert_register:
                cls.__revert_register |= { id_tx: dict() }
            
            if not id_rx in cls.__revert_register[id_tx]:
                cls.__revert_register[id_tx][id_rx] = foc_rx.get_data()
            
            foc_rx.set_data( data_list_str )

    @classmethod
    def __revert_rule(cls, id_tx:int) -> None:
        if not id_tx in cls.__revert_register:
            return
        
        for id_rx, data in cls.__revert_register.pop(id_tx).items():
            cls.__lookup_frames[id_rx].set_data( data )

@runtime_checkable
class Registerable( Protocol ):
    def get_name(self) -> str: ...
    def get_data(self) -> list[str]: ...
    def set_data(self, data:list[str]) -> None: ...
    def get_parsed_data(self) -> tuple[bool, object]: ...


#----------------------------------------------------------------------------------------------------------------------
# Manager stuffs
#----------------------------------------------------------------------------------------------------------------------
class Status(Enum):
    IDLE            = 0
    INPUT_ERROR     = 1
    USER_INTERRUPT  = 2
    COMPLETED_EMPTY = 3
    COMPLETED       = 4


@LOGGER.remember_class
class Manager():
    # reserved-ish Keys: 
    # - keyboard.Key.tab (+ keyboard.Key.shift)
    # - keyboard.Key.esc
    # - keyboard.Key.enter
    
    __frames: list[Frame]
    
    __interactables: list[Interactable]
    __confirmation : Confirmation
    
    __bound_lt: Point[int]
    __bound_rb: Point[int]
    
    __active_interactable      : Interactable
    __active_interactable_index: int
    
    __interactable_forward: Interactable
    
    __move_enter: bool
    __move_arrow: bool
    
    __status: Status
    
    __read_key: Key
    
    def __init__(self, use_enter_key_movement:bool=True, use_up_down_key_movement:bool=False) -> None:
        self.__frames = []
        self.__interactables = []
        self.__confirmation = None
        
        self.__bound_lt = Console.get_cursor()
        self.__bound_rb = Console.get_cursor()
        
        self.__active_interactable = None
        self.__active_interactable_index = -1
        
        self.__interactable_forward = None
        
        self.__move_enter = use_enter_key_movement
        self.__move_arrow = use_up_down_key_movement
        
        self.__status = Status.IDLE
        
        self.__read_key = None
        
        Register.reset()
        Register.set_manager( self )
        
        LOGGER.info( '='*120 )
    
    #----------------------------------------------------------------------------------------------------------------------
    # For frontend users
    #----------------------------------------------------------------------------------------------------------------------
    def set_position_left_top(self, col:int, line:int, absolute:bool=True) -> Self:
        self.__bound_lt = Point(col, line) if absolute else Point(col+Console.get_cursor()[0], line+Console.get_cursor()[1])
        return self
    
    @overload
    def append(self, _o:Interactable, /) -> Self: ...
    @overload
    def append(self, _o:Registerable, /) -> Self: ...
    @overload
    def append(self, _o:Confirmation, /) -> Self: ...
    def append(self, _o:Frame, /) -> Self:
        assert isinstance(_o, Frame), f"given object {_o} does not implement Frame"
        
        _o.manager = self
        self.__frames.append( _o )
        
        types: list[str] = []
        if isinstance( _o, Interactable ):
            types.append( "Interactable" )
            self.__append_Interactable( _o )
        
        if isinstance( _o, Registerable ):
            types.append( "Registerable" )
            self.__append_Registerable( _o )
        
        if isinstance( _o, Confirmation ):
            types.append( "Confirmation" )
            self.__append_confirmation_focus( _o )

        LOGGER.debug(f"Appended Frame: {_o} {types}")
        
        return self

    def append_rule(self, transceiver:int|str, receiver:int|str, tx_transform_function: Callable[[list[str]], tuple[bool, list[str]]]) -> Self:
        """
        ### Thin wrapper for the Register.set_tx_rx( transceiver_index, receiver_index, tx_transform_function ) classmethod
        
        ---
        
        set transceive and receive instructions 
        
        set these instructions *after* at least the `transceiver` and `receiver` `Focus_Input` objects are appended to the `Focus_Manager`

        Args:
            receiver (`int`|`str`): index or prompt title name of the receiving focus
            transceiver (`int`|`str`): index or prompt title name of the transceiving focus
            tx_transform_function (`(list[str]) -> tuple[bool, list[str]]`): takes the backend data (the `list`[`str`]) as parameter and should return a `tuple`[should_send:`bool`, transformed_data_for_receiver:`list`[`str`] ]

        Returns:
            `Register`: monad design
        """
        Register.set_rule( transceiver, receiver, tx_transform_function )
        
        return self
    
    
    def join(self, entry_point_index:int=0) -> Result:
        assert self.__frames, "No Interactable Frame objects had been appended"
        assert self.__status == Status.IDLE, "A Manager instance can only be joined once"
        
        LOGGER.info('- '*60)
        
        self.__init_interactables( entry_point_index )
        self.__calc_bbox_and_frame_positions()
        
        self._log_debug()
        
        with Console.virtual_area( self.__bound_lt, self.__bound_rb ):
            Console.hide_cursor()
            
            self.__render_all_frames()
            self.__awake_all()
            
            self.__active_interactable.enter_via_enter()
            
            while True:
                self.__awake()
                
                self.__read_key = Console.get_key()
                Console.hide_cursor()
                
                self.__pre_forward_key()
                self.__forward_key()
                
                if self.__status == Status.COMPLETED\
                or self.__status == Status.USER_INTERRUPT:
                    break
                
                self.__post_forward_key()
        
        Console.show_cursor()
        Console.set_cursor( 0, self.__bound_rb[1]+1, True )
        
        LOGGER.info("finished: returning results")
        
        return self.get_result()
    
    def get_result(self) -> Result:
        return Result( self.__status == Status.COMPLETED, { f.get_name(): f.result() for f in self.__interactables_no_confirm } )
    
    
    def get_bbox(self) -> tuple[ tuple[int, int], tuple[int, int] ]:
        return (self.__bound_lt.T, self.__bound_rb.T)
    
    def get_dimensions(self) -> tuple[int, int]:
        return (self.__bound_rb - self.__bound_lt + Point(1,1)).T
    
    
    #----------------------------------------------------------------------------------------------------------------------
    # For backend users implementing own classes
    #----------------------------------------------------------------------------------------------------------------------
    def request_unfiltered_forward(self, caller_frame:Interactable) -> bool:
        if not isinstance(caller_frame, Interactable):
            LOGGER.warning( f"{caller_frame} tried to request forward but is not of type {type(Interactable)}" )
            return False

        if self.__interactable_forward:
            LOGGER.warning( f"{caller_frame} tried to request forward but {self.__interactable_forward} has already forward request" )
            return False
        
        LOGGER.debug( f"{caller_frame} has now acquired unfiltered forward" )
        self.__interactable_forward = caller_frame
        return True
    
    def release_unfiltered_forward(self, caller_frame:Interactable) -> bool:
        if not isinstance(caller_frame, Interactable):
            LOGGER.warning( f"{caller_frame} has tried to release forward but is not of type {type(Interactable)}" )
            return False

        if not self.__interactable_forward:
            LOGGER.warning( f"{caller_frame} tried to release forward but no Interactable had requested forward before" )
            return False
        
        if self.__interactable_forward != caller_frame:
            LOGGER.warning( f"{caller_frame} tried to release forward but is not the Interactable ({self.__interactable_forward}) that requested the forward" )
            return False
        
        LOGGER.debug( f"{caller_frame} has now released unfiltered forward" )
        self.__interactable_forward = None
        return True
    
    
    #----------------------------------------------------------------------------------------------------------------------
    # private methods
    #----------------------------------------------------------------------------------------------------------------------
    # initialization and setup #
    #--------------------------#
    def __append_Interactable(self, _o:Interactable, /) -> Self:
        self.__interactables.append( _o )
        return self
    
    def __append_Registerable(self, _o:Registerable, /) -> Self:
        Register.append( _o )
        return self
    
    def __append_confirmation_focus(self, _o:Confirmation, /) -> Self:
        assert self.__confirmation is None, "Only ONE Confirmation Frame per Manager can be appended"
        self.__confirmation = _o
        self.__confirmation.set_callback( self.__check_statuses )
        return self
    
    @property
    def __interactables_no_confirm(self) -> list[Interactable]:
        return self.__interactables[:-1] if self.__confirmation else self.__interactables
    
    
    def __init_interactables(self, entry_point_index:int=0) -> None:
        if not self.__interactables:
            return
        
        assert 0 <= entry_point_index < len(self.__interactables), f"entry point index out of bounds. Must be in the range of 0 to {len(self.__interactables)-1}"
        
        # assure that the confirmation module is at the bottom of all interactables
        if self.__confirmation:
            LOGGER.info( f"Confirmation module is present: {self.__confirmation}" )
            
            self.__interactables.remove( self.__confirmation )
            self.__interactables.append( self.__confirmation )
            
            self.__frames.remove( self.__confirmation )
            self.__frames.append( self.__confirmation )
        
        self.__active_interactable_index = entry_point_index
        self.__active_interactable = self.__interactables[self.__active_interactable_index]
        
        self.__calc_interactable_internal_positions()
    
    def __calc_bbox_and_frame_positions(self) -> None:
        max_width = max( map(lambda frame: frame.get_dimensions()[0], self.__frames) )
        
        for i in range(1, len(self.__frames)):
            pos   = Point( 0, self.__frames[i-1].bounding.line + 1 )
            bound = pos + ( max_width, self.__frames[i].get_dimensions()[1]-1 )
            self.__frames[i].set_position( pos, bound )
        
        self.__bound_rb = self.__bound_lt + ( max_width, self.__frames[-1].bounding.line )

    def __calc_interactable_internal_positions(self) -> None:
        name_sizes: list[int]        = []
        dimensions: list[Point[int]] = []
        
        for foc in self.__interactables_no_confirm:
            name_sizes.append( foc.get_required_name_size() )
            dimensions.append( foc.get_required_dimensions() )
        
        max_len_title, validation_column_offset = Manager._setup_interactable_titles( name_sizes, dimensions )
        
        # set positions of focuses (relative to the virtual screen coordinates)
        for foc in self.__interactables:
            foc.set_offsets( max_len_title, (validation_column_offset, 0) )

    def _log_debug(self) -> None:
        max_size_type_name = max( 4, max_width_of_strings( map( lambda f: f.__class__.__name__, self.__frames) )[1] )
        
        fmt        = "               [ {:>5d}, {:>11s} ] ( {:>3d}, {:>3d} ) ( {:>3d}, {:>3d} ) | {:>%ds} | {:s}" % max_size_type_name
        fmt_header = "Frames: indices[frames, interactable]     position     bounding | " + ' '*(max_size_type_name-4) + "type | extra"
        
        LOGGER.debug(
            f"Position: {self.__bound_lt.T}, Bounding: {self.__bound_rb.T}, Dimensions: {self.get_dimensions()}, Frames Count: {len(self.__frames)}, has confirmation module: {bool(self.__confirmation)}\n" +
            '\t' + fmt_header + '\n\t' + 
            '\n\t'.join( [
                fmt.format(
                    index_frame,
                    str(self.__interactables.index(frame)) if frame in self.__interactables else '---',
                    *frame.position,
                    *frame.bounding,
                    frame.__class__.__name__,
                    frame.get_name() if isinstance(frame, Interactable) else ''
                ) for index_frame, frame in enumerate(self.__frames)
            ] )
        )
    
    #---------------------#
    # general loop stuffs #
    #---------------------#
    def __pre_forward_key(self) -> None:
        # prefilter input key
        
        match self.__read_key:
            # break loop since user interrupted the flow
            case Key( np=keyboard.Key.esc ):
                self.__status = Status.USER_INTERRUPT
                self.__read_key = Key()
            
            case Key( np=keyboard.Key.enter, mods=[] ) if not self.__confirmation and self.__active_interactable_index == len(self.__interactables)-1:
                self.__check_statuses()
                self.__read_key = Key()
    
    def __post_forward_key(self) -> None:
        # manage focus and switches it if necessary
        
        if self.__interactable_forward:
            return
        
        match (self.__read_key, self.__move_enter, self.__move_arrow):
            case ( Key( np=keyboard.Key.enter, mods=[] ), True, _ ) | ( Key( np=keyboard.Key.down ), _, True ):
                self.__active_interactable_index += 1
            
            case ( Key( np=keyboard.Key.enter, mods=[keyboard.Key.shift] ), True, _ ) | ( Key( np=keyboard.Key.up ), _, True ):
                self.__active_interactable_index -= 1
        
        self.__active_interactable_index = ( len(self.__interactables) + self.__active_interactable_index ) % len(self.__interactables)
        self.__active_interactable = self.__interactables[self.__active_interactable_index]
        
        match (self.__read_key, self.__move_enter, self.__move_arrow):
            case ( Key( np=keyboard.Key.enter, mods=[] ) | Key( np=keyboard.Key.enter, mods=[keyboard.Key.shift] ), True, _):
                self.__active_interactable.enter_via_enter()
            
            case ( Key( np=keyboard.Key.down ) | Key( np=keyboard.Key.up ), _, True ):
                self.__active_interactable.enter_via_arrow( *Console.get_cursor() )

    
    def __check_statuses(self) -> bool:
        '''
        returning True indicates to the confirmation module that it can release its focus
        
        returning False indicates to the confirmation module that it should reset its confirmation button and expect an other user input (in the future)
        '''
        fmt = "\t{:>%ds} | {:>%ds} | {:s}, {:s}\n" % ( max_width_of_strings( [x.get_name() for x in self.__interactables_no_confirm] )[1], max_width_of_strings( [s.name for s in Status] )[1] )
        debug_msg = f"Checking statuses: current internal status: {self.__status}\n"
        
        if self.__status == Status.USER_INTERRUPT:
            LOGGER.debug( debug_msg + "=== INTERRUPT-ESC KEY ===" )
            return True
        
        if self.__confirmation and not self.__confirmation.result():
            LOGGER.debug( debug_msg + "=== INTERRUPT-BUTTON ===" )
            self.__status = Status.USER_INTERRUPT
            return True
        
        
        debug_msg += fmt.format( "names", "status", "result object", "Optional[data_array]" )
        for focus in self.__interactables_no_confirm:
            focus.validate()
            
            if not focus.status in (Status.COMPLETED, Status.COMPLETED_EMPTY):
                self.__status = Status.INPUT_ERROR
            
            res = str(focus.result()).splitlines()
            optional = stringify(focus.data) if isinstance(focus, Input) else "---"
            
            debug_msg += fmt.format(
                focus.get_name(),
                focus.status.name,
                res[0],
                optional if len(res) == 1 else ""
            )
            
            for s in res[1:]:
                debug_msg += fmt.format( "", "", s, "" )
            
            if len(res) > 1:
                debug_msg += fmt.format( "", "", "", optional )
            
        
        
        if self.__status != Status.INPUT_ERROR:
            LOGGER.debug( debug_msg + "=== ACCEPTED ===" )
            self.__status = Status.COMPLETED
            return True
        
        LOGGER.debug( debug_msg + "=== REJECTED ===" )
        self.__status = Status.IDLE
        return False

    def __render_all_frames(self) -> None:
        for frame in self.__frames:
            frame.render()

    def __forward_key(self) -> None:
        self.__active_interactable.forward_key( self.__read_key )
        
        if not isinstance( self.__active_interactable, Registerable ):
            return
        
        success, res = self.__active_interactable.get_parsed_data()
        if success:
            Register.set( self.__active_interactable, res )

    def __awake(self) -> None:
        self.__active_interactable.clear()
        self.__active_interactable.render()
        self.__active_interactable.awake()

    def __awake_all(self) -> None:
        Register.transceive( self )
        for focus in self.__interactables:
            self.__active_interactable = focus
            self.__awake()
        self.__active_interactable = self.__interactables[self.__active_interactable_index]

    #------------------#
    # Helper functions #
    #------------------#
    @staticmethod
    def _setup_interactable_titles( list_of_titles_sizes:list[int], list_of_sizes:list[Point[int]] ) -> tuple[int, int]:
        max_len_title = max( list_of_titles_sizes ) if list_of_titles_sizes else 0
        
        validation_column_offset = SIZE_TAB + max( map( lambda s: s.col, list_of_sizes ) ) if list_of_sizes else SIZE_TAB

        return max_len_title, validation_column_offset


#----------------#
# Generic Frames #
#----------------#
@runtime_checkable
class Frame( Protocol ):
    manager: Manager
    '''reference to manager instance'''
    
    position: Point[int]
    '''left-top corner position of Focus_Input (is inclusive)'''
    
    bounding: Point[int]
    '''right-bottom corner position of Focus_Input, defaults to the end of line of Console (is inclusive)'''
    
    def render(self) -> None:
        ...
    
    def clear(self, *, force:bool=False) -> None:
        """clear printable area of this focus, can be overridden but must always clear the whole assigned area when flag forced is set"""
        Console.clear_rectangle( self.position.T, self.bounding.T )
    
    def get_bbox(self) -> tuple[ tuple[int, int], tuple[int, int] ]:
        """
        get bounding box of frame

        Returns:
            `tuple`[ `tuple`[`int`, `int`], `tuple`[`int`, `int`] ]: ( (left, top), (right, bottom) )
        """
        return ( self.position.T, self.bounding.T )

    def get_dimensions(self) -> tuple[ int, int ]:
        """
        get the dimensions of the frame as character-sizes

        Returns:
            `tuple`[`int`, `int`]: ( width, height )
        """
        return ( self.bounding - self.position + Point(1, 1) ).T

    def set_position(self, pos:tuple[int, int], bound:Optional[tuple[int,int]]=None) -> None:
        pos = Point( *pos )
        
        if bound is None:
            self.bounding = Point( *self.bounding ) + ( pos - self.position )
        else:
            self.bounding = Point( *bound )
        
        self.position = pos

@LOGGER.remember_class
class Plain_Text( Frame ):
    text: str

    def __init__(self, text:str, *, force_width:Optional[int]=None) -> None:
        self.position = Point( 0, 0 )
        self.bounding = Point( 0, 0 )
        
        self.text = text
        
        if force_width is not None:
            self.text = fill( self.text, force_width )
        
        self.bounding = Point( max_width_of_strings( self.text.splitlines() )[1]-1, len(self.text.splitlines())-1 )
        
        LOGGER.debug( f"new Plain_Text with bounding {str(self.bounding)}" )
    
    def render(self) -> None:
        Console.write_in( self.text, *self.position, *self.bounding )
    
    def set_position(self, pos:tuple[int, int], bound:Optional[tuple[int,int]]=None) -> None:
        before_pos_bound = self.position, self.bounding
        super().set_position( pos, bound )
        self = Plain_Text( self.text, force_width=self.get_dimensions()[0] )
        
        LOGGER.debug( "repositioned Plain_Text: [pos=(%3d, %3d), bound=(%3d, %3d)] -> [pos=(%3d, %3d), bound=(%3d, %3d)]", *before_pos_bound[0], *before_pos_bound[1], *self.position, *self.bounding )


#---------------------#
# Interactable Frames #
#---------------------#
@runtime_checkable
class Interactable( Frame, Protocol ):
    # cspell:disable
    MSG_VALID   : Final[str] = "- Eingabe AKZEPTIERT"
    MSG_INVALID : Final[str] = "- Eingabe UNGÜLTIG"
    MSG_EMPTY   : Final[str] = "- Eingabe AKZEPTIERT - Leer"
    MSG_MAX_SIZE: Final[int] = max( map( len, (MSG_VALID, MSG_INVALID, MSG_EMPTY) ) )
    # cspell:enable
    
    status: Status
    
    def awake(self) -> None: ...
    def forward_key(self, key: Key) -> None: ...
    
    def validate(self) -> None: ...
    def result(self) -> Optional[object]: ...
    
    def enter_via_arrow(self, cursor_col:int, cursor_line:int) -> None: ...
    def enter_via_enter(self) -> None: ...

    def set_offsets(self, name_format_shift:int, validate:Optional[tuple[int, int]]=None) -> None:
        """ 
        set specific sizes and offsets to align all interactables vertically

        Args:
            name_format_shift (`int`): is the maximum length of all interactable names
            validate (`tuple`[`int`, `int`], optional): offset is relative to `pos_input`. Offset for the `pos_validate` (starting position for validation messages). Defaults to the end of the input length plus a `SIZE_TAB`.
        """
        ...
    
    def get_name(self) -> str: ...
    def get_required_name_size(self) -> int: ...
    def get_required_dimensions(self) -> Point[int]: ...

@LOGGER.remember_class
class Input( Interactable, Registerable ):
    pos_input: Point[int]
    '''starting position for user input writing'''
    
    pos_validate: Point[int]
    '''starting position for validation messages'''
    
    DELIMITER: Final[str] = ": "
    formatted_name  : str
    
    name    : str
    data    : list[str]
    data_ptr: int
    
    input_size  : int
    accept_empty: bool
    
    result_object: str
    
    def __init__(
                 self,
                 prompt_name   : str,
                 accept_empty  : bool = False,
                 prefill       : str  = "",
                 input_size    : int  = 32
                 ) -> None:
        self.pos_input    = Point(0, 0)
        self.pos_validate = Point(0, 0)
        
        self.name = prompt_name
        self.formatted_name = ("{:>%ds}" % len(self.name)).format( self.name ) + Input.DELIMITER
        
        self.status       = Status.IDLE
        self.input_size   = max( 0, input_size )
        self.accept_empty = accept_empty
        
        self.data     = self.right_fill( list(prefill) )
        self.data_ptr = max( 0, len(prefill) )
        
        self.position = Point(0, 0)
        self.bounding = self.get_required_dimensions()
        
        self.result_object = None

    
    #----------------------------------------------------------------------------------------------------------------------
    # following methods are intended to be overridden by and extended the user to suite their needs
    #----------------------------------------------------------------------------------------------------------------------
    def cursor(self, override_data_ptr:Optional[int]=None, get_max_position:bool=False) -> Point[int]:
        """
        determine and return the cursor position for the current data_ptr or optionally the given data_ptr

        Args:
            override_data_ptr (`Optional`['int'], optional): if not `None` take this value instead of the instance data_ptr. Defaults to `None`.
            get_max_position (bool, optional): if `True`. Defaults to `False`.

        Returns:
            `tuple`[ `int`, `int` ]: cursor position (col, line)
        """
        if get_max_position:
            return Point( self.input_size, 0 )
        
        return Point( override_data_ptr if override_data_ptr is not None else self.data_ptr, 0 )
    
    def transform(self) -> object:
        """
        Method should transform the data as `list`[`str`] to an object of the Focus'S needs
        
        the `object` this method returns is the input for the predicate(...) method

        Returns:
            `object`: transformed object
        """
        return stringify( self.data )
    
    def predicate(self, transformed_data:object) -> bool:
        """
        predicate for the transformed data

        should return `True` if the transformed data is valid to be returned as the user input, `False` otherwise

        Args:
            transformed_data (`object`): the object returned from transform()

        Returns:
            `bool`: predicate result
        """
        return True

    
    #----------------------------------------------------------------------------------------------------------------------
    # predefined methods
    # These can be extended by the user but they do not have to be
    #----------------------------------------------------------------------------------------------------------------------
    def awake(self) -> None:
        self.reset_cursor()
        
        Console.set_cursor( *self.cursor(), False )
        Console.show_cursor()
    
    def forward_key(self, key: Key) -> None:
        LOGGER.debug( f"Input: dptr={self.data_ptr:>2}, key={key.info_str()}" )
        
        match key:
            case Key( np=keyboard.Key.space ) if self.data_ptr < self.input_size:
                self.data[self.data_ptr] = ' '
                self.data_ptr = min( self.data_ptr+1, self.input_size )


            # remove input to the left
            case Key( np=keyboard.Key.backspace, mods=[] ):
                self.data_ptr = max(0, self.data_ptr-1)
                self.data[self.data_ptr] = ''

            # remove input completely to the left
            case Key( np=keyboard.Key.backspace, mods=[keyboard.Key.ctrl] ):
                self.data[:self.data_ptr] = [''] * self.data_ptr
                self.data_ptr = 0

            # remove input to the right
            case Key( np=keyboard.Key.delete, mods=[] ) if self.data_ptr < self.input_size:
                self.data.pop(self.data_ptr)
                self.data.append('')
            
            # remove input completely to the right
            case Key( np=keyboard.Key.delete, mods=[keyboard.Key.ctrl] ) if self.data_ptr < self.input_size:
                self.data[self.data_ptr:] = [''] * ( self.input_size - ( self.data_ptr ) )
            
            # move the cursor left
            case Key( np=keyboard.Key.left ):
                self.data_ptr = max(0, self.data_ptr-1)
            
            # move the cursor right
            case Key( np=keyboard.Key.right ):
                self.data_ptr = min( self.data_ptr+1, self.input_size )
            
            
            # move the cursor to front
            case Key( np=keyboard.Key.home ):
                self.data_ptr = 0
            
            # move the cursor to end
            case Key( np=keyboard.Key.end ):
                self.data_ptr = self.input_size
            
            
            case Key( np=None, an=ch ) if self.data_ptr < self.input_size:
                # if there is a free space left to the current data_ptr position then insert there the character
                # - rendered data: abc_efg
                #                     ^
                #             data_ptr-position
                # - user pressed: 'd' and it gets inserted
                # - rendered data afterwards: abcdefg
                #                                 ^
                #                         data_ptr-position
                if self.data[self.data_ptr] and not self.data[self.input_size-1]:
                    self.data[ self.data_ptr : ] = [ch] + self.data[ self.data_ptr : self.input_size-1 ]
                    return
                
                # otherwise override the character at the current data_ptr position
                self.data[self.data_ptr] = ch
                self.data_ptr = min( self.data_ptr+1, self.input_size )

        Register.transceive(self)
    
    
    def render(self) -> None:
        self.reset_cursor()
        self.render_name()

        self.render_background()
        self.render_foreground()
    
    def render_foreground(self) -> None:
        for i in range(self.input_size):
            Console.write_at( self.data[i], *self.cursor(i), False )
    
    def render_background(self) -> None:
        for i in range(self.input_size):
            Console.write_at( PLACE_HOLDER, *self.cursor(i), False )
    
    
    def validate(self) -> None:
        self.render()
        self.reset_cursor()
        
        Console.set_cursor( *self.pos_validate, True )
        # check for empty entry (if accept_empty)
        if self.data == self.right_fill([]) and self.accept_empty:
            Console.write( self.MSG_EMPTY )
            self.status = Status.COMPLETED_EMPTY
            self.result_object = None
            return
        
        
        # otherwise parse the user input
        success, res = self.get_parsed_data()
        
        if not success:
            Console.write( self.MSG_INVALID )
            self.status = Status.INPUT_ERROR
            return
        
        Console.write( self.MSG_VALID )
        self.status = Status.COMPLETED
        self.result_object = res
    
    def result(self) -> object | None:
        return self.result_object

    
    def enter_via_arrow(self, cursor_col:int, cursor_line:int) -> None:
        """find a suitable data_ptr for the given cursor position and if possible set the data_ptr accordingly"""
        rel_col, rel_line = Console.clamp_point( (cursor_col, cursor_line) - self.pos_input, (0, 0), self.cursor( get_max_position=True ) )
        
        for i in range(0, self.input_size+1):
            if ( rel_col, rel_line ) == self.cursor(i):
                self.data_ptr = i
                return
    
    def enter_via_enter(self) -> None:
        self.enter_via_arrow( *(self.pos_input + self.cursor( get_max_position=True )) )


    #----------------------------------------------------------------------------------------------------------------------
    # following methods are predefined and final
    # These are not inherently intended to be altered / extended / overridden
    # Overridden one of the following methods can lead to loss of functionality of this Input-Interactable
    #----------------------------------------------------------------------------------------------------------------------
    # Registerable Override #
    #-----------------------#
    @final
    def get_name(self) -> str:
        return self.name
    @final
    def get_data(self) -> list[str]:
        return self.data
    @final
    def set_data(self, data:list[str]) -> None:
        if len(data) == self.input_size:
            self.data = data
            self.render()
    @final
    def get_parsed_data(self) -> tuple[bool, object]:
        """
        parse the the internal state (data array)

        transform data to an object and supply it to the predicate

        Returns:
            `tuple`[`bool`, `object`]: [0] is `True` if 
        """
        try:
            res = self.transform()
        
            if not self.predicate( res ):
                raise ValueError()
            
            return True, res
        except ValueError:
            return False, None
    
    #----------------#
    # Frame Override #
    #----------------#
    @final
    def set_position(self, pos:tuple[int, int], bound:Optional[tuple[int,int]]=None) -> None:
        shift = Point( *pos ) - self.position
        self.pos_input += shift
        self.pos_validate += shift
        super().set_position(pos, bound)
    
    #-----------------------#
    # Interactable Override #
    #-----------------------#
    @final
    def get_required_name_size(self) -> str:
        return len( self.formatted_name )
    @final
    def get_required_dimensions(self) -> Point[int]:
        return self.cursor( get_max_position=True )
    
    #-------------------#
    # Own final methods #
    #-------------------#
    @final
    def render_name(self) -> None:
        Console.write_at( self.formatted_name, *self.position, True )
    
    @final
    def set_offsets(self, name_format_shift:int, validate:Optional[tuple[int, int]]=None) -> None:
        self.formatted_name = ("{:>%ds}" % max( 0, name_format_shift - len(Input.DELIMITER) )).format( self.name ) + Input.DELIMITER
        self.pos_input = self.position + ( len(self.formatted_name), 0 )
        
        pos_valid_off     = validate if validate else ( self.cursor( get_max_position=True ).col + SIZE_TAB, 0 )
        self.pos_validate = self.pos_input + pos_valid_off
        
        self.bounding = max( self.pos_validate, self.pos_input + self.cursor( get_max_position=True ) ) + Point(self.MSG_MAX_SIZE, 0)
    
    @final
    def reset_cursor(self) -> None:
        """
        set cursor to the input starting position of this Focus_Input
        """
        Console.set_cursor( *self.pos_input, True )
    
    @final
    def right_fill(self, data_to_fit:list[str]) -> str:
        """ right fills supplied `data` to predetermined `input_size` """
        return (data_to_fit + ['']*self.input_size)[:self.input_size]

@LOGGER.remember_class
class Date( Input ):
    #? data:layout   = 'ddmmyyyy'
    #?     :indexing    01234567
    
    in_select_mode: bool
    select_index  : int
    select_dates  : list[date]

    must_be_listed: bool
    
    dates: list[str]
    
    def __init__(
                 self,
                 prompt_name     : str,
                 accept_empty    : bool      = False,
                 prefill_date_ISO: str       = date.today().strftime("%d%m%Y"),
                 predicate       : object    = lambda d: True,
                 must_be_listed  : bool      = False,
                 preset_dates    : list[str] = []
                ) -> None:
        super().__init__(prompt_name, accept_empty, prefill_date_ISO, 8)
        
        self.in_select_mode = False
        self.select_index   = -1
        self.select_dates   = []
        
        if must_be_listed:
            self.predicate = lambda x: predicate(x) and x in self.dates
        else:
            self.predicate = predicate
        
        self.must_be_listed = must_be_listed
        self.dates = preset_dates
    
    def render_foreground(self) -> None:
        Console.write_at( '.', 2, 0, False )
        Console.write_at( '.', 5, 0, False )
        
        super().render_foreground()
    
    def cursor(self, override_data_ptr:Optional[int]=None, get_max_position:bool=False) -> Point[int]:
        dptr = override_data_ptr if override_data_ptr is not None else self.data_ptr
        
        if get_max_position:
            return Point( 10, 0 )
        
        return Point( dptr + (dptr >= 2) + (dptr >= 4), 0 )
    
    def transform(self) -> date:
        return str_to_date( self.data )
    
    def forward_key(self, key: Key) -> None:
        match key:
            # Guards
            case Key( np=None, an=ch ) if not ch.isdigit():
                return
            case Key( np=keyboard.Key.space ):
                return
            
            # tab selecting case
            case Key( np=keyboard.Key.tab, mods=[] | [keyboard.Key.shift] ) if self.dates:
                self.init_selecting()
            
                self.select_index += -1 if keyboard.Key.shift in key.get_modifiers() else 1

                self.select_index = ( len(self.select_dates) + self.select_index ) % len(self.select_dates)
                
                self.data = self.select_dates[self.select_index]
                self.enter_via_enter() # set cursor to the right position of the selected name

                # is select_index at the original user input
                if self.select_index == len(self.select_dates)-1:
                    Register.revert(self)
                    return
                
                Register.transceive(self)
            
            case Key( np=None, an=ch ) if ch.isdigit():
                self.in_select_mode = False
                super().forward_key( key )
                
            case _:
                self.in_select_mode = False
                super().forward_key( key )
    
    def init_selecting(self) -> None:
        LOGGER.debug( f"in select mode: {self.in_select_mode}" )
        if self.in_select_mode:
            return
        
        self.in_select_mode = True
        self.select_index   = -1
        
        
        # select all dates that have the same digits at the same locations like the user pre-typed input
        # e.g:  user writes: __.12.___
        #       select all dates from the preset_dates list that are in December
        self.select_dates = [
            list( d.strftime("%d%m%Y") )
            for d 
            in self.dates
            if all(
                    map(
                        lambda chrs: chrs[0] == chrs[1] or not chrs[1],
                        zip( list(d.strftime("%d%m%Y")), self.data )
                    )
                )
            ] + [ self.data ]
    
    def enter_via_enter(self) -> None:
        super().enter_via_arrow( *(self.pos_input + self.cursor(len( stringify( self.data ) ))) )

@LOGGER.remember_class
class Value( Input ):
    digit_count    : tuple[int, int]
    sum_digit_count: int
    
    def __init__(
                 self,
                 prompt_name : str,
                 accept_empty: bool            = False,
                 prefill     : float           = None,
                 digit_count : tuple[int, int] = (0, 0)
                ) -> None:
        self.digit_count     = digit_count
        self.sum_digit_count = sum( self.digit_count )
        
        super().__init__(prompt_name, accept_empty, "", digit_count[0] + digit_count[1] )
        
        self.data_ptr = self.input_size
        self.data     = [''] * self.input_size
        
        if not prefill:
            return
        
        # assure prefill is a correctly float type formatted string
        prefill = float(prefill)

        self.data = float_to_data_format( prefill, self.digit_count )

    
    def data_format_to_float_str(self) -> str:
        return stringify( map( lambda ch: ch if ch else '0', ( *(self.data[:self.digit_count[0]]), '.', *(self.data[self.digit_count[0]:]) ) ) )
    
    def render_foreground(self) -> None:
        Console.write_at( '.', self.digit_count[0], 0, False )
        
        val = self.transform()
        
        if val:
            self.data = float_to_data_format( val, self.digit_count )
        
        super().render_foreground()
    
    def cursor(self, override_data_ptr:Optional[int]=None, get_max_position:bool=False) -> Point[int]:
        dptr = override_data_ptr if override_data_ptr is not None else self.data_ptr
        
        if get_max_position:
            return Point( self.sum_digit_count + 1, 0 )
        
        return Point( dptr + ( dptr >= self.digit_count[0] ), 0 )
    
    def transform(self) -> float:
        if self.data == self.right_fill([]):
            return None
        return float( self.data_format_to_float_str() )
    
    def predicate(self, transformed_data: object) -> bool:
        return transformed_data is not None
    
    def forward_key(self, key: Key) -> None:
        non_zero_before = self.is_none_or_zero()
        
        match key:
            case Key( np=None, an=ch ) if not ch.isdigit():
                return
            case Key( np=keyboard.Key.space ):
                return
            
            # remove input to the left
            case Key( np=keyboard.Key.backspace, mods=[] ) if self.data_ptr == self.input_size:
                self.data = [''] + self.data[:self.input_size-1]

            # remove input completely to the left
            case Key( np=keyboard.Key.backspace, mods=[keyboard.Key.ctrl] ):
                self.data     = [''] * self.input_size
                self.data_ptr = self.input_size

            # reposition the cursor and the typed input so that they line up with the decimal separator in screen
            case Key( np=None, an='.'|',' ):
                delta = self.data_ptr - self.digit_count[0]
                
                # cursor left of decimal separator
                if delta < 0:
                    delta = -delta
                    
                    self.data = ( ['']*delta + self.data )[:self.input_size]
                    
                # cursor right of decimal separator
                elif delta > 0:
                    self.data = ( self.data + ['']*delta )[delta:self.input_size]
                
                self.data_ptr = self.digit_count[0]
            
            case Key( np=None, an=ch ) if (self.data_ptr == self.input_size) and (ch.isdigit()) and (self.data[0] == ''):
                # left shift data array and append user input (key) at end, if data has empty leading slots
                self.data = self.data[1:] + [key.get_char()]

            case _:
                super().forward_key( key )
        
        # clear data if input went from a non zero or non empty float to an zero or empty float
        if not non_zero_before and self.is_none_or_zero():
            self.data = self.right_fill([])

    def is_none_or_zero(self) -> bool:
        return not any( map( lambda ch: not ( ch == '' or ch == '0'), self.data ) )

@LOGGER.remember_class
class String( Input ):
    def __init__( 
                 self,
                 prompt_name : str,
                 accept_empty: bool = False,
                 prefill     : str = "",
                 input_size  : int = 32
                 ) -> None:
        super().__init__(prompt_name, accept_empty, prefill, input_size)
    
    def forward_key(self, key: Key) -> None:
        match key:
            # do not move the cursor right
            case Key( np=keyboard.Key.right ) if self.data_ptr < self.input_size and not self.data[self.data_ptr]:
                pass
            
            case _:
                super().forward_key(key)
     
    def enter_via_arrow(self, cursor_col:int, cursor_line:int) -> None:
        super().enter_via_arrow( min( cursor_col, self.pos_input.col + len( stringify( self.data ) ) ), cursor_line )

@LOGGER.remember_class
class Name( String ):
    in_select_mode: bool
    select_prefix : str
    select_index  : int
    select_names  : list[str]

    must_be_listed: bool
    
    names: list[str]
    
    def __init__( 
                 self,
                 prompt_name   : str,
                 accept_empty  : bool = False,
                 input_size    : int = 32,
                 must_be_listed: bool = False,
                 preset_names  : list[str] = []
                 ) -> None:
        super().__init__(prompt_name, accept_empty, "", input_size)

        self.in_select_mode = False
        self.select_prefix  = ""
        self.select_index   = -1
        self.select_names   = []
        
        self.must_be_listed = must_be_listed
        
        self.names = list( map( self.normalize, preset_names ) )
    
    def forward_key(self, key: Key) -> None:
        match key:
            case Key( np=keyboard.Key.tab, mods=[]|[keyboard.Key.shift] ):
                self.init_selecting()

                self.select_index += -1 if keyboard.Key.shift in key.get_modifiers() else 1

                self.select_index = ( len(self.select_names) + self.select_index ) % len(self.select_names)

                self.data = self.select_names[self.select_index]
                self.enter_via_enter() # set cursor to the right position of the selected name

                Register.transceive(self)

            case _:
                self.in_select_mode = False
        
                super().forward_key(key)
    
    def transform(self) -> object:
        return self.normalize( stringify(self.data) )
    
    def init_selecting(self) -> None:
        if self.in_select_mode:
            return
        
        self.in_select_mode = True
        self.select_prefix  = stringify(self.data)
        self.select_index   = -1
        
        prefix = self.canonicalize( self.select_prefix )
        
        none_leading = filter( lambda n: ( n:=self.canonicalize(n), prefix in n and not n.startswith( prefix ) )[1], self.names )
        leading      = filter( lambda n: ( n:=self.canonicalize(n),                     n.startswith( prefix ) )[1], self.names )
        
        leading      = sorted( leading )
        none_leading = sorted( none_leading )
        
        self.select_names = [ self.right_fill( list(n) ) for n in leading + none_leading + [self.select_prefix] ]
    
    def predicate(self, transformed_data: str) -> bool:
        return (transformed_data in self.names) if (self.must_be_listed) else (bool(transformed_data))
    
    @classmethod
    def normalize(cls, name:str ) -> str:
        return name.strip()
    
    @classmethod
    def canonicalize(cls, name:str ) -> str:
        return cls.normalize( name ).lower()


#-------------------------------------#
# Button and Button Management Frames #
#-------------------------------------#
@LOGGER.remember_class
class Button( Frame ):
    #                         lt   rt   lb   rb
    CORNER_idle             = ".", ".", "`", "´"
    CORNER_selected         = "+"
    CORNER_pressed          = "*"
    CORNER_selected_pressed = "+"
    
    LINE_H_idle             = "-"
    LINE_H_selected         = "="
    LINE_H_pressed          = "-"
    LINE_H_selected_pressed = "="
    
    LINE_V_idle             = "|"
    LINE_V_selected         = "|"
    LINE_V_pressed          = "|"
    LINE_V_selected_pressed = "|"
    
    FILLER_idle             = " "
    FILLER_selected         = " "
    FILLER_pressed          = "#"
    FILLER_selected_pressed = "#"

    inner_spacing: Point[int]
    
    prompt_name: str
    
    selected: bool
    pressed : bool
    
    function_callback: Callable[[bool], None]

    def __init__(self, prompt_name:str, inner_spacing:tuple[int, int]=(1, 0), callback:Optional[Callable[[bool], None]] = None) -> None:
        self.position = None
        self.bounding = None

        assert inner_spacing[0] >= 0 and inner_spacing[1] >= 0, "inner_spacing values must be positive"
        
        self.inner_spacing = Point( *inner_spacing )
        
        self.prompt_name = prompt_name
        
        self.selected = False
        self.pressed  = False
        
        self.function_callback = callback if callback else (lambda x: None)
        
        #preliminarily set a position so that the button manager can read the dimensions
        self.set_position(0, 0)
    
    def render(self) -> None:
        assert self.position and self.bounding, "Position of Button is not set: use method set_position() to set the position"
        
        Console.write_in( '\n'.join(self.create_button()), self.position.col, self.position.line, self.bounding.col, self.bounding.line, True, True )
    
    def forward_key(self, key:Key) -> None:
        match key:
            case Key( np=keyboard.Key.enter ):
                self.pressed = not self.pressed
                self.render()
                self.function_callback( self.pressed )
    
    def set_in_focus(self, has_focus:bool) -> None:
        self.selected = has_focus
    
    def is_pressed(self) -> bool:
        return self.pressed
    
    def create_button(self) -> list[str]:
        corner, line_h, line_v, filler = Button.CORNER_idle, Button.LINE_H_idle, Button.LINE_V_idle, Button.FILLER_idle
        
        match (self.selected, self.pressed):
            case (True, False):
                corner, line_h, line_v, filler = Button.CORNER_selected, Button.LINE_H_selected, Button.LINE_V_selected, Button.FILLER_selected

            case (False, True):
                corner, line_h, line_v, filler = Button.CORNER_pressed, Button.LINE_H_pressed, Button.LINE_V_pressed, Button.FILLER_pressed

            case (True, True):
                corner, line_h, line_v, filler = Button.CORNER_selected_pressed, Button.LINE_H_selected_pressed, Button.LINE_V_selected_pressed, Button.FILLER_selected_pressed
        
        if isinstance(corner, tuple) and len( corner ) == 4:
            c_lt, c_rt, c_lb, c_rb = corner
        else:
            c_lt, c_rt, c_lb, c_rb = corner, corner, corner, corner
            
        bound_top    = c_lt + "%s" + c_rt
        bound_bottom = c_lb + "%s" + c_rb
        
        if self.inner_spacing.col > 1:
            middle = f"{line_v}{filler*(self.inner_spacing.col-1)} {self.prompt_name} {filler*(self.inner_spacing.col-1)}{line_v}"
        else:
            middle = f"{line_v}{filler*self.inner_spacing.col}{self.prompt_name}{filler*self.inner_spacing.col}{line_v}"

        middle_filler = f"{line_v}{filler*(2*self.inner_spacing.col+len(self.prompt_name))}{line_v}"
        
        bound_top    = bound_top    % ( line_h*(len(middle)-(len(c_lt)+len(c_rt))) )
        bound_bottom = bound_bottom % ( line_h*(len(middle)-(len(c_lb)+len(c_rb))) )
        
        return [
            bound_top,
            *[middle_filler]*self.inner_spacing.line,
            middle,
            *[middle_filler]*self.inner_spacing.line,
            bound_bottom
        ]

    def calc_bound(self) -> None:
        bounds:list[list[str]] = []
        
        for iter_statuses in self:
            bounds.append( self.create_button() )
        
        self.bounding = self.position + max( map( lambda button_list: Point( len(button_list[0])-1, len(button_list)-1 ), bounds ) )

    def set_position(self, col:int, line:int ) -> None:
        self.position = Point( col, line )
        self.calc_bound()
    
    def __iter__(self):
        s, p = self.selected, self.pressed

        self.selected, self.pressed = False, False
        yield self

        self.selected, self.pressed = True, False
        yield self

        self.selected, self.pressed = False, True
        yield self

        self.selected, self.pressed = True, True
        yield self
        
        self.selected, self.pressed = s, p

class Alignment( Enum ):
    LEFT_TOP    = auto()
    LEFT_CENTER = auto()
    LEFT_BOTTOM = auto()
    
    CENTER_TOP    = auto()
    CENTER_CENTER = auto()
    CENTER_BOTTOM = auto()
    
    RIGHT_TOP    = auto()
    RIGHT_CENTER = auto()
    RIGHT_BOTTOM = auto()

@LOGGER.remember_class
class Button_Manager( Interactable ):
    is_finalized: bool
    
    button_amount: int
    button_matrix: dict[int, dict[int, Button]]
    '''{ line_index: { col_index: Button } }'''
    button_flattened: list[ Button ]
    button_alignment: list[ Alignment ]
    
    index_2_matrix: dict[ int, tuple[int, int] ]
    '''index -> (line, col)'''
    matrix_2_index: dict[ tuple[int, int], int ]
    '''(line, col) -> index'''
    
    required_line_height : dict[ int, int ]
    required_column_width: dict[ int, int ]
    required_offset      : dict[ tuple[int, int], Point[int] ]
    
    active_button: Button
    active_index : int
    
    grid_dimensions: Point[int]
    '''(lines, columns)'''
    
    min_max_line_at_column: dict[int, tuple[int, int]]
    '''(column) -> (min_line, max_line)'''
    min_max_column_at_line: dict[int, tuple[int, int]]
    '''(line) -> (min_column, max_column)'''
    
    inner_spacing: Point[int]
    '''(col, line)'''
    outer_spacing: Point[int]
    '''(col, line)'''
    
    need_render_update: list[int]
    
    def __init__(self, inner_spacing:tuple[int, int]=(3, 1), outer_spacing:tuple[int, int]=(1, 0)) -> None:
        """
        Setup a Button_Manager to a range Buttons in a table like manner

        Args:
            inner_spacing (`tuple[int, int]`, optional): (col, line) setting the spacing sizes between the Buttons. Defaults to (3, 1).
            outer_spacing (`tuple[int, int]`, optional): (col, line) setting the spacing sizes between the Buttons and the bounding box. Defaults to (1, 0).
        """
        # inner_spacing = (10, 2), outer_spacing = (7, 2)
        # +------------------------------------------------+
        # |            ^ os[1]               ^ os[1]       |
        # |            v                     v             |
        # | os[0] +----------+   is[0]  +----------+ os[0] |
        # |<----->| Button 1 |<-------->| Button 2 |<----->|
        # |       +----------+          +----------+       |
        # |            ^ is[1]               ^ is[1]       |
        # |            v                     v             |
        # | os[0] +----------+   is[0]  +----------+ os[0] |
        # |<----->| Button 3 |<-------->| Button 4 |<----->|
        # |       +----------+          +----------+       |
        # |            ^                     ^             |
        # |            v os[1]               v os[1]       |
        # +------------------------------------------------+
        self.position = (0, 0)
        self.bounding = (0, 0)
        
        self.is_finalized = False
        
        self.button_amount    = 0
        self.button_matrix    = dict()
        self.button_flattened = []
        self.button_alignment = []
        
        self.index_2_matrix = dict()
        self.matrix_2_index = dict()
        
        self.required_line_height  = dict()
        self.required_column_width = dict()
        self.required_offset       = dict()
        
        self.active_button = None
        self.active_index  = -1
        
        self.grid_dimensions = None
        
        self.min_max_line_at_column = dict()
        self.min_max_column_at_line = dict()
        
        self.inner_spacing = Point( *inner_spacing )
        self.outer_spacing = Point( *outer_spacing )

        self.need_render_update = []

    
    ###########################################################
    # User should use these methods to setup a button manager #
    ###########################################################
    
    def append_at(self, line:int, column:int, button:Button, alignment:Alignment=Alignment.CENTER_CENTER ) -> Self:
        assert not self.is_finalized, "Can not append further Buttons. This Button Manager has already been finalized"
        assert not self.button_flattened, f"Can not mix appends. Can only use ONE append method to append Buttons: append_at was called after append_auto"
        assert line   >= 0, f"Invalid Coordinates. Coordinates must be strictly non-negative, but {line=} was given as a negative"
        assert column >= 0, f"Invalid Coordinates. Coordinates must be strictly non-negative, but {column=} was given as a negative"
        
        if not line in self.button_matrix:
            self.button_matrix |= { line: dict() }
        
        assert not column in self.button_matrix[line], f"Cannot append multiple Buttons to one Cell: Cell {(line, column)} is already occupied"
        
        self.button_matrix[ line ] |= { column: button }
        
        if self.grid_dimensions is None:
            self.grid_dimensions = Point(0, 0)
        
        self.grid_dimensions = max( self.grid_dimensions, Point(line+1, column+1) )
        
        self.button_alignment.append( (line, column, alignment) )
        
        self.button_amount += 1
        return self
    
    def append_auto(self, button:Button, alignment:Alignment=Alignment.CENTER_CENTER) -> Self:
        assert not self.is_finalized, "Can not append further Buttons. This Button Manager has already been finalized"
        assert not self.button_matrix, f"Can not mix appends. Can only use ONE append method to append Buttons: append_auto was called after append_at"
        
        self.button_flattened.append( button )
        self.button_alignment.append( alignment )
        
        self.button_amount += 1
        return self
    
    def finalize(self) -> Self:
        assert not self.is_finalized, "Can not finalize. This Button Manager has already been finalized"
        assert self.button_matrix or self.button_flattened, "Can not finalize with 0 Buttons appended"
        
        if self.button_flattened:
            self._finalize_via_flattened()
        elif self.button_matrix:
            self._finalize_via_matrix()
        
        self.need_render_update = [i for i in range(self.button_amount)]
        
        self._calc_helper_min_max_dict()
        self._calc_cell_dimensions()
        self._calc_and_set_positions()

        # preliminary position
        self.set_position((0, 0))
        
        self.is_finalized = True
        
        self._switch_active_index( None )
        return self
    
    
    def get_button_at(self, line:int, col:int) -> Optional[Button]:
        if not line in self.button_matrix:
            return None
        
        if not col in self.button_matrix[line]:
            return None
        
        return self.button_matrix[line][col]
    
    def get_button_index(self, index) -> Optional[Button]:
        if not( 0 <= index < self.button_amount ):
            return None
        
        return self.button_flattened[index]
    
    
    ##############################
    # Private non-public methods #
    ##############################
    def _finalize_via_flattened(self) -> None:
        line_count = floor( sqrt( self.button_amount ) )
        self.grid_dimensions = Point( line_count, self.button_amount // line_count )
        
        for i, but in enumerate( self.button_flattened ):
            col, line = divmod( i, line_count )
            
            if not line in self.button_matrix:
                self.button_matrix |= { line: dict() }
            
            self.button_matrix[ line ] |= { col: but }
            
            self.matrix_2_index |= { (line, col): i }
            self.index_2_matrix |= { i: (line, col) }
    
    def _finalize_via_matrix(self) -> None:
        # sorting the keys by lines and then by columns.
        # Yes this a dictionary and sorting it does kind of circumvent the intended way of using a dictionary, but it is necessary when flattening out the dictionary to a 1D-List
        self.button_matrix = dict( sorted( self.button_matrix.items(), key=lambda kv: kv[0] ) )
        for line, cols in self.button_matrix.items():
            self.button_matrix[ line ] = dict( sorted( cols.items(), key=lambda kv: kv[0] ) )
        
        column_lower_bound = min( map( lambda line_cols: min( list(line_cols[1].keys()) ), self.button_matrix.items() ) )
        column_upper_bound = max( map( lambda line_cols: max( list(line_cols[1].keys()) ), self.button_matrix.items() ) )
        
        for col in range( column_lower_bound, column_upper_bound+1, 1 ):
            for line in self.button_matrix.keys():
                button = self.button_matrix[ line ].get( col, None )
                
                if button is None:
                    continue
                
                self.matrix_2_index |= { (line, col): len(self.button_flattened) }
                self.index_2_matrix |= { len(self.button_flattened): (line, col) }
                
                self.button_flattened.append( button )
        
        # mapping from list[ tuple[line:int, col:int, align:Alignment] ] to list[ tuple[index:int, align:Alignment] ] 
        self.button_alignment: map[tuple[int, Alignment]]  = map( lambda line_col_align: (self.matrix_2_index[(line_col_align[0], line_col_align[1])], line_col_align[2]), self.button_alignment )
        # sorting by index
        self.button_alignment: list[tuple[int, Alignment]] = sorted( self.button_alignment, key=lambda index_align: index_align[0] )
        # removing index from tuple and finalizing the button_alignment list
        self.button_alignment: list[Alignment] = [align for _, align in self.button_alignment]
    
    
    def _switch_active_index(self, index:int|None) -> None:
        """
        switching with which button the user is currently interacting

        Args:
            index (`int | None`): index == None: no button will be set active
        """
        if self.active_button:
            self.active_button.set_in_focus( False )
            self.need_render_update.append( self.active_index )
        
        if index is None:
            self.active_index  = None
            self.active_button = None
            return
        
        assert 0 <= index < self.button_amount, IndexError( f"supplied {index=} is out of bounds for length of {self.button_amount} buttons" )
        
        self.active_index  = index
        self.active_button = self.button_flattened[ self.active_index ]
        self.active_button.set_in_focus( True )
        self.need_render_update.append( self.active_index )
    
    def _find_button_for_direction(self, direction:Key=None) -> int:
        '''returns index of best suited button for supplied direction, Key.left, Key.right, Key.up, Key.down'''
        if self.active_index is None:
            self._switch_active_index( 0 )
        
        index = self.active_index
        indx_buttons = self.button_amount - 1

        line, col = self.index_2_matrix[ index ]
        
        match direction:
            case Key( np=keyboard.Key.up ):
                if index == 0 or line == 0:
                    return None
                
                index -= 1
                
                # if we switched to a column on the left
                if col != self.index_2_matrix[ index ][1]:
                    index = self.matrix_2_index[ ( self.min_max_line_at_column[ col ][0], self.index_2_matrix[ index ][1] ) ]
            
            case Key( np=keyboard.Key.down ):
                if index == indx_buttons or line == self.min_max_line_at_column[ col ][1]:
                    return None
                
                index += 1
                
            case Key( np=keyboard.Key.left ):
                if line == col == 0:
                    return 0
                
                while True:
                    if col == 0:
                        line -= 1
                        col = self.min_max_column_at_line[ line ][1]
                    
                    col -= 1
                    indx = self.matrix_2_index.get( (line, col), None )
                    
                    if indx is not None:
                        index = indx
                        break
                    
                    # we went all the way up to (0, 0), there are now no other buttons
                    if line == col == 0:
                        break
                    
            case Key( np=keyboard.Key.right ):
                if index == indx_buttons:
                    return indx_buttons
                
                while True:
                    if col == self.min_max_column_at_line[ line ][1]:
                        line += 1
                        col = self.min_max_column_at_line[ line ][0]
                    
                    col += 1
                    indx = self.matrix_2_index.get( (line, col), None )
                    
                    if indx is not None:
                        index = indx
                        break
                    
                    if index == indx_buttons:
                        break
        
        return index
    
    def _calc_cell_dimensions(self) -> None:
        for i, but in enumerate( self.button_flattened ):
            line, col = self.index_2_matrix[ i ]
            
            self.required_column_width[ col ] = max( self.required_column_width.get( col, 0 ), but.get_dimensions()[0] )
            self.required_line_height[ line ] = max( self.required_line_height.get( line, 0 ), but.get_dimensions()[1] )
        
        accu_line = 0
        for line in range(self.grid_dimensions.x):
            accu_col = 0
            for col in range(self.grid_dimensions.y):
                self.required_offset |= { (line, col): Point( accu_col, accu_line ) }
                accu_col += self.required_column_width.get(col, 0) + self.inner_spacing.col
            accu_line += self.required_line_height.get(line, 0) + self.inner_spacing.line
    
    def _position_alignments_offset(self, index:int) -> Point[int]:
        line, col = self.index_2_matrix[index]
        button = self.button_flattened[ index ]
        
        # x == col  is horizontally
        # y == line is vertically
        # we are now again on terminal coordinates, NOT in grid coordinates
        offset_x = 0
        offset_y = 0
        space_x = self.required_column_width[ col ] - button.get_dimensions()[0]
        space_y = self.required_line_height[ line ] - button.get_dimensions()[1]
        match self.button_alignment[ index ]:
            case Alignment.LEFT_TOP:
                pass
            case Alignment.LEFT_CENTER:
                offset_y = space_y // 2
            case Alignment.LEFT_BOTTOM:
                offset_y = space_y
            case Alignment.CENTER_TOP:
                offset_x = space_x // 2
            case Alignment.CENTER_CENTER:
                offset_x = space_x // 2
                offset_y = space_y // 2
            case Alignment.CENTER_BOTTOM:
                offset_x = space_x // 2
                offset_y = space_y
            case Alignment.RIGHT_TOP:
                offset_x = space_x
            case Alignment.RIGHT_CENTER:
                offset_x = space_x
                offset_y = space_y // 2
            case Alignment.RIGHT_BOTTOM:
                offset_x = space_x
                offset_y = space_y
        
        return self.required_offset[ (line, col) ] + (offset_x, offset_y)
    
    def _calc_and_set_positions(self) -> None:
        lt = self.position + self.outer_spacing
        
        for i, button in enumerate(self.button_flattened):
            button.set_position( *( lt + self._position_alignments_offset( i ) ) )
        
        rb_but_line, rb_but_col = self.index_2_matrix[self.button_amount-1]
        self.bounding = lt\
            + self.required_offset[ (rb_but_line, rb_but_col) ]\
            + Point( self.required_column_width[rb_but_col], self.required_line_height[rb_but_line] )\
            + self.outer_spacing

    def _calc_helper_min_max_dict(self) -> None:
        """ calculates the minimum and maximum values for the `min_max_line_at_column` and `min_max_column_at_line` variables """
        for i in range(self.button_amount):
            line, col = self.index_2_matrix[ i ]
            
            if not col in self.min_max_line_at_column:
                self.min_max_line_at_column |= { col : (0, 0) }
            
            self.min_max_line_at_column[ col ] = ( min( self.min_max_line_at_column[ col ][0], line ), max( line, self.min_max_line_at_column[ col ][1] ) )
            
            if not line in self.min_max_column_at_line:
                self.min_max_column_at_line |= { line : (0, 0) }
            
            self.min_max_column_at_line[ line ] = ( min( self.min_max_column_at_line[ line ][0], col ), max( col, self.min_max_column_at_line[ line ][1] ) )

    def _resize_table_width(self) -> None:
        """
        resize individual columns to adjust the width for the whole table to the newly set width
        
        increases column sizes beginning at the left columns
        
        call this after the setting a new position, e.g. after `super().set_position(...)` was called

        Args:
            previous_width (`int`): new width to be filled by the whole table
        """
        delta_width = (self.get_dimensions()[0] - 2*self.outer_spacing[0] - (self.button_amount-1)*self.inner_spacing[0]) - sum( self.required_column_width.values() )
        
        if delta_width <= 0:
            return
        
        delta_width_per_col, modulo = divmod( delta_width, self.grid_dimensions[1] )
        
        for i in range(self.grid_dimensions[1]):
            self.required_column_width[ i ] += delta_width_per_col + ( 1 if i < modulo else 0 )
    
    def _request_forward(self) -> None:
        successfully = self.manager.request_unfiltered_forward( self )
        LOGGER.info( f"Button Manager: requested {successfully=} unfiltered forward >>> entered via index {self.active_index:<3d} at ({self.index_2_matrix[ self.active_index ][0]:>3d}, {self.index_2_matrix[ self.active_index ][1]:>3d})")
    
    
    def _log_debug(self) -> None:
        table_fmt:str = "{:^3} | "*(self.grid_dimensions.y+1)
        LOGGER.debug( '\n'.join( [
            # section 1 ---------------------------------------------------------------------------
            f"Position: {self.position.T}, Bounding: {self.bounding.T}, Dimensions: {self.get_dimensions()}, Inner Spacing: {self.inner_spacing.T}, Outer Spacing: {self.outer_spacing.T}",
            
            # section 2 ---------------------------------------------------------------------------
            f"\tGrid: dimensions {self.grid_dimensions.T}",
            "\t\t" + table_fmt.format( "---", *[i for i in range(self.grid_dimensions.y)] ),
            "\t\t" + "\n\t\t".join( [
                table_fmt.format(
                    line,
                    *[
                        (self.matrix_2_index[(line, col)] if col in self.button_matrix[line].keys() else "" )
                        for col
                        in range(self.grid_dimensions.y)
                    ] 
                ) for line in range(self.grid_dimensions.x) ] ),
            
            # section 3 ---------------------------------------------------------------------------
            f"\trequired sizes: ",
            "\t\t  index |" + (' {:>3} |'*max(self.grid_dimensions)).format( *range(max(self.grid_dimensions)) ),
            "\t\t column |" + (' {:>3} |'*self.grid_dimensions[1]  ).format( *[self.required_column_width.get(i, '---') for i in range(max(self.grid_dimensions))] ),
            "\t\t   line |" + (' {:>3} |'*self.grid_dimensions[0]  ).format( *[self.required_line_height .get(i, '---') for i in range(max(self.grid_dimensions))] ),
            
            # section 4 ---------------------------------------------------------------------------
            "\t" + "Buttons: [index]  ( col, line)      alignment  -  ( 'name'  position  bounding )",
            "\t" + "\n\t".join( "{:>16d}  ({:>4d}, {:>4d})  {:>13s}  -  ( '{:}'  {:}  {:} )".format( i, *self.index_2_matrix[ i ], self.button_alignment[ i ].name, self.button_flattened[ i ].prompt_name, *["({:>4d}, {:>4d})".format(*t) for t in self.button_flattened[ i ].get_bbox()] ) for i in range(self.button_amount) )
        ] ) )

    #########################
    # Override Interactable #
    #########################
    def awake(self) -> None:
        Console.hide_cursor()
    
    def clear(self, *, force:bool=False) -> None:
        if force:
            super().clear(force=True)
    
    def render(self) -> None:
        while self.need_render_update:
            self.button_flattened[ self.need_render_update.pop(0) ].render()
    
    def forward_key(self, key: Key) -> None:
        match key:
            case Key( np= keyboard.Key.left | keyboard.Key.right | keyboard.Key.up | keyboard.Key.down ):
                idx = self._find_button_for_direction( key )
                
                if idx is None:
                    self.manager.release_unfiltered_forward( self )
                    LOGGER.debug( "Button Manager: released unfiltered forward")
                else:
                    LOGGER.debug( f"Button Manager: switching with Key {key.info_str():<7s} to index {idx:<3d} at ({self.index_2_matrix[ idx ][0]:>3d}, {self.index_2_matrix[ idx ][1]:>3d})")
                
                self._switch_active_index( idx )
                
                self.render()
            
            case _:
                self.active_button.forward_key( key )
    
    
    def validate(self) -> None:
        self.status = Status.COMPLETED
    
    def result(self) -> Result:
        return Result( True, { but.prompt_name: but.is_pressed() for but in self.button_flattened } )
    
    def enter_via_arrow(self, cursor_col:int, cursor_line:int) -> None:
        if cursor_line < 0.5 * (self.bounding.line + self.position.line):
            self._switch_active_index( 0 )
        else:
            self._switch_active_index( self.button_amount-1 )
        
        self._request_forward()
    
    def enter_via_enter(self) -> None:
        self._switch_active_index( 0 )
        self._request_forward()
    
    def set_offsets(self, name_format_shift:int, validate:Optional[tuple[int, int]]=None) -> None:
        pass
    
    def get_name(self) -> str:
        return "Button_Manager"
    
    def get_required_name_size(self) -> str:
        return len( self.get_name() + ": " )

    def get_required_dimensions(self) -> Point[int]: 
        return Point( *self.get_dimensions() )

    def set_position(self, pos:tuple[int, int], bound:Optional[tuple[int,int]]=None) -> None:
        super().set_position( pos, bound )

        if self.is_finalized:
            self._resize_table_width()
            
            self._calc_cell_dimensions()
            self._calc_and_set_positions()

            self._log_debug()


@LOGGER.remember_class
class Select( Button_Manager ):
    BASIC_BUTTON_SPACING = ( 1, 0 )
    
    selected_index: int
    
    def __init__(self, inner_spacing:tuple[int, int]=(3, 1), outer_spacing:tuple[int, int]=(1, 0)) -> None:
        super().__init__( inner_spacing, outer_spacing )
        self.selected_index = None
    
    def append_name(self, name:str, at_pos:Optional[tuple[int, int]]=None, alignment:Alignment=Alignment.CENTER_CENTER) -> Self:
        """
        append a selecting option (Button)

        if previous options (Buttons) were append with `append_at(...)` or `append_name(..., at_pos=(line, col))` future options (Buttons) must be append in as either of these methods. Same for `append_auto(...)` and `append_name(..., at_pos=None)` appends.

        Args:
            name (`str`): name of the Button to be appended
            at_pos (`Optional[tuple[int, int]]`): if supplied must be a tuple of size 2 with structure (line_index, column_index)

        Returns:
            `Self`: monad architecture
        """
        if at_pos:
            self.append_at( *at_pos, Button( name, self.BASIC_BUTTON_SPACING ), alignment )
        else:
            self.append_auto( Button( name, self.BASIC_BUTTON_SPACING ), alignment )
        
        return self
    
    ###########################
    # Override Button_Manager #
    ###########################
    def forward_key(self, key: Key) -> None:
        super().forward_key(key) # only left, right, up, down keys are registered
        
        match key:
            case Key( np=keyboard.Key.enter ) if self.selected_index is not None:
                self.button_flattened[self.selected_index].forward_key( key ) # forward unselecting command
                
                self.selected_index = None if self.selected_index == self.active_index else self.active_index
            
            case Key( np=keyboard.Key.enter ) if self.selected_index is None:
                self.selected_index = self.active_index
                
                self.button_flattened[self.selected_index].forward_key( key ) # forward selecting command

        self.render()

@LOGGER.remember_class
class Select_yes_no( Select ):
    def __init__(self, accept_name:str="Ja", reject_name:str="Nein") -> None:
        super().__init__( (0,0), (0,0) )
        self.append_name( reject_name, (0, 0), Alignment.LEFT_CENTER )
        self.append_name( accept_name, (0, 1), Alignment.RIGHT_CENTER )
        self.finalize()

#--------------#
# Confirmation #
#--------------#
@runtime_checkable
class Confirmation( Interactable, Protocol ):
    def set_callback(self, callback:Callable[[], bool]) -> None: ...

@LOGGER.remember_class
class Confirm_simple_accept( Confirmation, Button_Manager ):
    manager_callback: Callable[[], bool]
    
    BUTTON_NAME = "Bestätigen"
    
    BUTTON_SPACING = (1, 0)
    
    def __init__(self) -> None:
        super().__init__( (0,0), (0,0) )
        self.manager_callback = None
        self.append_auto( Button(self.BUTTON_NAME, self.BUTTON_SPACING), Alignment.RIGHT_CENTER )
        self.finalize()
    
    ####################
    # Override Methods #
    ####################
    def set_callback(self, callback:Callable[[], bool]) -> None:
        self.manager_callback = callback
    
    def result(self) -> bool:
        return super().result()[0]

    def forward_key(self, key: Key) -> None:
        super().forward_key(key)
        
        match key:
            case Key( np=keyboard.Key.enter ):
                if self.manager_callback():
                    self.manager.release_unfiltered_forward( self )
                    self._switch_active_index( None )
                else:
                    # forward key again to reset the button to its previous non-pressed state
                    super().forward_key(key)

                self.render()

@LOGGER.remember_class
class Confirm_yes_no( Confirmation, Button_Manager ):
    manager_callback: Callable[[], bool]
    
    BUTTON_SPACING = ( 1, 0 )
    
    def __init__(self, accept_name:str="Ja", reject_name:str="Nein") -> None:
        super().__init__( (0,0), (0,0) )
        self.manager_callback = None
        self.append_at( 0, 0, Button( reject_name, self.BUTTON_SPACING ), Alignment.LEFT_CENTER )
        self.append_at( 0, 1, Button( accept_name, self.BUTTON_SPACING ), Alignment.RIGHT_CENTER )
        self.finalize()
    
    ####################
    # Override Methods #
    ####################
    def set_callback(self, callback:Callable[[], bool]) -> None:
        self.manager_callback = callback
    
    
    def result(self) -> bool:
        return self.get_button_at( 0, 1 ).is_pressed()

    def forward_key(self, key: Key) -> None:
        super().forward_key(key)
        
        match key:
            case Key( np=keyboard.Key.enter ):
                if self.manager_callback():
                    self.manager.release_unfiltered_forward( self )
                    self._switch_active_index( None )
                else:
                    # forward key again to reset the button to its previous non-pressed state
                    super().forward_key(key)

                self.render()
    
    def enter_via_arrow(self, cursor_col:int, cursor_line:int) -> None:
        self.enter_via_enter()
    
    def enter_via_enter(self) -> None:
        self._switch_active_index( 1 )
        self._request_forward()


if __name__ == "__main__":
    from dbHandler import DBSession
    Console.setup( "Focus Test" )
    Console.clear()
    Console.set_cursor( 0, 0 )
    SESSION = DBSession()
    
    # Testing code snippets I ========================================================================================
    # from random import randint
    # results:Result = Manager(True, True).set_position_left_top( 5, 1 )\
    #     .append( String("String input", True, "Sample") )\
    #     .append(
    #         Button_Manager( (0,0), (4,1) )\
    #             # .append_at( 0, 0, Button( "Button (0, 0)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 1, 0, Button( "Button (1, 0)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 2, 0, Button( "Button (2, 0)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 3, 0, Button( "Button (3, 0)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 0, 1, Button( "Button (0, 1)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 1, 1, Button( "Button (1, 1)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 2, 1, Button( "Button (2, 1)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 3, 1, Button( "Button (3, 1)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 0, 2, Button( "Button (0, 2)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 1, 2, Button( "Button (1, 2)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 2, 2, Button( "Button (2, 2)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 3, 2, Button( "Button (3, 2)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 0, 3, Button( "Button (0, 3)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 1, 3, Button( "Button (1, 3)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 2, 3, Button( "Button (2, 3)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             # .append_at( 3, 3, Button( "Button (3, 3)", (2, 0) ), Alignment.CENTER_CENTER )\
    #             #.force_cell_dimensions( 1, 1, (30, 10) )\
    #             .append_auto( Button( "Button  0", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button  1", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button  2", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button  3", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button  4", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button  5", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button  6", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button  7", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button  8", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button  9", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button 10", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button 11", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button 12", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button 13", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button 14", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .append_auto( Button( "Button 15", (randint(0, 5), randint(0, 5)) ), Alignment.CENTER_CENTER )\
    #             .finalize()
    #     )\
    #     .append( Value("Value input", True, "", (2,4)) )\
    #     .join()
    
    # Console.write_line( results.success )
    # Console.write_line( [*results] )
    
    # Testing code snippets II =========================================================================================    
    # FMM = Manager(True, True).set_position_left_top( 0, 2 )

    # result = FMM\
    #     .append( Plain_Text("Eine Ablesung mit folgenden Werten ist bereits eingetragen:") )\
    #     .append( Plain_Text("blah blah\n"*5) )\
    #     .append( String( "Wollen Sie diese Werte überschreiben [y/n]", input_size=1 ) )\
    #     .join()
    
    # Console.write_at( result.success, 1, 0, False )
    # Console.write_at( [*result], 4, 1, False )
    # Console.set_cursor( 0, 2, False )
    
    # Testing Focus ===================================================================================================    
    # with Console.virtual_area( (0, 10), reset_cursor_on_exit=False ):
    #     Console.write_line( "Testing Focus stuffs" )
    #     FM = Manager(True, True).set_position_left_top( 4, 1 )
        
    #     # Test 1
    #     # result = FM\
    #     #     .append( String( "string", True ) )\
    #     #     .append( Date  ( "Date"  , True ) )\
    #     #     .append( Value ( "Value" , False, digit_count=(3, 3) ) )\
    #     #     .append( Name  ( "Name"  , True,  preset_names=["Müller Heinz", "van der Linden Heinz Albert", "Günther Peter", "Fuchs Günther", "Maier-Schmidt Heinrich", "Müller-Schmidt Theodor", "Fuchs Peter", "Friedrich Horst"]) )\
        
    #     # Test 2
    #     FM.append( Date( "Datum", True, "", preset_dates=[d for d, *_ in SESSION.get_reading_all()] ) )
    #     for i in range(COUNT_READING_ATTRIBUTES):
    #         FM.append( Value( LIST_READING_ATTRIBUTE_NAMES[i], True, None, LIST_DIGIT_OBJ_LAYOUTS[i] ) )
    #         FM.append_rule( 0, LIST_READING_ATTRIBUTE_NAMES[i], TX_func_factory.date_2_value(SESSION, i) )
        
    #     FM.append( Button_Manager().append_auto(Button("Ja")).append_auto(Button("Nein")).finalize() )
    #     FM.append( Select().append_name("Ja").append_name("Nein").finalize() )
    #     FM.append( Select_yes_no() )
        
    #     # Test 3
    #     # result = FM\
    #     #     .append( String( "Name", False, "", 32 ) )\
    #     #     .append( Date( "Date", False, "" ) )\
    #     #     .append_tx_rx( 0, 1, TX_func_factory.name_2_dates(SESSION, 0) )\
    #     #     #.append( Focus_Name( "Name", False, 32, True, [ n  for n, *_ in SESSION.get_person_all() if n ] ) )\
        
    #     result = FM.append( Confirm_simple_accept() ).join()
        
    #     Console.write_at( result.success, 1, 1, False )
    #     Console.write_at( [*result], 4, 2, False )
    #     Console.set_cursor( 0, 3, False )
    
    
    Console.stop()