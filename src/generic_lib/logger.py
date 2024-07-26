from pathlib import Path
from typing  import Callable, Optional

import logging


def get_logger(
    log_dir_path: Path,
    log_name    : str,
    
    *adapters       : logging.LoggerAdapter,
    identifier      : Optional[ Callable[[logging.LogRecord], None] ] = lambda r: r.funcName,
    custom_formatter: Optional[ logging.Formatter ] = None
) -> logging.Logger:
    """
    create or retrieve a logger the specified name

    generic creator method for creating logger objects

    Args:
        log_dir_path (`Path`): Path to the logs directory
        log_name (`str`): name of the log file and the associated "logger"-file. (suffix ".log" will be appended automatically)
        identifier (`(LogRecord) ?-> None`, optional): if no `custom_formatter` was specified this Callable will be utilized in the default formatter to get the identifier of an record.
        custom_formatter (`Optional[ logging.Formatter ]`): if supplied will be used as the formatter instead of the default one and the `identifier` will be ignored.
        *adapters (`LoggerAdapter`, ...): list of adapters to be applied to the resulting logger object. Will apply the adapters in the order in the list
        
    Returns:
        `logging.Logger`: logger with the associated specifications
    """
    
    log_dir_path.mkdir( parents=True, exist_ok=True )

    log_file_path = log_dir_path.joinpath( f"{log_name}.log" )

    # touching the log file
    log_file_path.open("w").close()

    if not custom_formatter:
        class _format( logging.Formatter ):
            fmt_base = "{asctime:<8s} [ {levelname:>8s} ] | @{lineno:>4d}::{identifier:>25s}: "
            
            def __init__(self) -> None:
                super().__init__(self.fmt_base + "{message:s}", "%H:%M:%S", "{")
                
            def format( self, record: logging.LogRecord ) -> str:
                record.identifier = identifier( record )
                
                s = super().format(record)
                
                if record.exc_text or record.exc_info or record.stack_info:
                    return s
                
                l_space = ' ' * ( len(s) - len(record.message) )
                record.message = ('\n'+l_space).join( record.message.splitlines() )
                
                return self.formatMessage(record)
        
        custom_formatter = _format

    logger = logging.getLogger( log_name )
    logger.setLevel( logging.DEBUG )

    _fh = logging.FileHandler( log_file_path.as_posix() )
    _fh.setLevel( logging.DEBUG )
    _fh.setFormatter( custom_formatter() )

    logger.addHandler( _fh )
    
    for adapt in adapters:
        logger = adapt( logger )
    
    return logger