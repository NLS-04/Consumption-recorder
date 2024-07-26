import inspect
import logging

from pathlib import Path
from typing import Any, Mapping

_log_path = Path(__file__).parent.parent.joinpath("logs").joinpath("debug_Frames.log")
_log_path.open("w").close()

class _adapter( logging.LoggerAdapter ):
    lines_to_class_name: dict[ tuple[int, int], str ]
    
    def __init__(self, logger: Any, extra: Mapping[str, object] | None = {}) -> None:
        super().__init__(logger, extra)
        self.lines_to_class_name = dict()
    
    def process(self, msg, kwargs):
        # Debug print
        # print( *[ "{:>4d} | {:>25s} | {:>10s} | {:s}".format(fi.lineno, '\\'.join(fi.filename.split('\\')[-2:]), fi.function, fi.code_context[0].strip()) for fi in inspect.stack()], sep='\n', end='\n\n' )
        
        frame = inspect.currentframe().f_back.f_back.f_back
        
        clazz = self.get_class_name( frame.f_lineno )
        del frame
        
        if clazz:
            clazz += '.'
        
        self.extra['clazz'] = clazz
        
        return super().process( msg, kwargs )
    
    def get_class_name( self, line:int ) -> str:
        out = list( filter( lambda items: items[0][0] <= line <= items[0][1], self.lines_to_class_name.items() ) )
        print(line, out)
        
        if out:
            return out.pop(0)[1]
        
        return ""

    def remember_class(self, cls):
        lines, start_index = inspect.getsourcelines( cls )
        
        self.lines_to_class_name |= { (start_index+1, start_index+len(lines)-1): cls.__name__ }
        
        return cls
    

LOGGER = logging.getLogger( __name__ )
LOGGER.setLevel(logging.DEBUG)

_fh = logging.FileHandler( _log_path.as_posix() )
_fh.setLevel(logging.DEBUG)
_fh.setFormatter( logging.Formatter( "{asctime:<8s} [ {levelname:>8s} ] | @{lineno:<4d}::{clazz:s}{funcName:s}: {message:s}", "%H:%M:%S", "{"  ) )

LOGGER.addHandler( _fh )

LOGGER = _adapter( LOGGER )



@LOGGER.remember_class
class A():
    def foo(self):
        LOGGER.debug("Oh Oh!")

@LOGGER.remember_class
class B(A):
    def foo(self):
        super().foo()
        LOGGER.debug("Oh Oh! ** 2")

if __name__ == '__main__':
    print( LOGGER.lines_to_class_name )
    LOGGER.info( "TEST" )
    
    A().foo()
    B().foo()