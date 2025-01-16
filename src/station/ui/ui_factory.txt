# factory.py

import logging
from typing import Optional
from src.station.ui.base import MeshtasticUI
from src.station.ui.terminal_ui import CursesUI
from src.station.utils.platform_utils import UIType, check_ui_availability

def create_ui(ui_type: str, 
             data_handler, 
             logger: Optional[logging.Logger] = None) -> MeshtasticUI:
    """
    Create and return appropriate UI instance.
    
    Args:
        ui_type: String name of UI type ('console', 'curses', 'dearpygui')
        data_handler: Data handler instance
        logger: Optional logger instance
        
    Returns:
        MeshtasticUI instance
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    # Convert string to enum
    try:
        ui_enum = UIType[ui_type.upper()]
    except KeyError:
        logger.warning(f"Unknown UI type: {ui_type}, falling back to console")
        ui_enum = UIType.CONSOLE
        
    # Check availability and create UI
    if ui_enum == UIType.DEARPYGUI and check_ui_availability(UIType.DEARPYGUI, logger):
        try:
            from src.station.ui.dearpygui_ui import DearPyGuiUI
            logger.info("Using DearPyGui interface")
            return DearPyGuiUI(data_handler, logger)
        except ImportError:
            logger.warning("DearPyGui import failed, falling back to curses")
            ui_enum = UIType.CURSES
            
    if ui_enum == UIType.CURSES:
        logger.info("Using curses interface")
        return CursesUI(data_handler, logger)
        
    # Fall back to console UI
    logger.info("Using basic console interface")
    from src.station.ui.console_ui import ConsoleUI
    return ConsoleUI(data_handler, logger)