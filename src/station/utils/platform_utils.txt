# platform_utils.py

import platform
import logging
from enum import Enum, auto
from typing import List

class UIType(Enum):
    """Available UI types."""
    CONSOLE = auto()  # Basic console output
    CURSES = auto()   # Terminal UI using curses
    DEARPYGUI = auto()  # GUI using DearPyGui

class Platform(Enum):
    """Supported platforms."""
    WINDOWS = auto()
    LINUX = auto()
    MACOS = auto()
    RASPBERRY_PI = auto()
    OTHER = auto()

def detect_platform() -> Platform:
    """Detect the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    
    if system == 'windows':
        return Platform.WINDOWS
    elif system == 'darwin':
        return Platform.MACOS
    elif system == 'linux':
        # Check if we're on a Raspberry Pi
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'Raspberry Pi' in f.read():
                    return Platform.RASPBERRY_PI
        except Exception:
            pass
        return Platform.LINUX
    return Platform.OTHER

def get_available_uis() -> List[UIType]:
    """Get list of available UI types for current platform."""
    available = [UIType.CONSOLE, UIType.CURSES]  # These are always available
    
    # Check for DearPyGui availability
    try:
        import dearpygui
        current_platform = detect_platform()
        
        # DearPyGui not supported on Raspberry Pi
        if current_platform != Platform.RASPBERRY_PI:
            available.append(UIType.DEARPYGUI)
    except ImportError:
        pass
    
    return available

def get_default_ui() -> UIType:
    """Get the default UI type for current platform."""
    platform = detect_platform()
    available = get_available_uis()
    
    # Return most capable available UI for platform
    if platform == Platform.RASPBERRY_PI:
        return UIType.CURSES
    elif UIType.DEARPYGUI in available:
        return UIType.DEARPYGUI
    else:
        return UIType.CURSES

def check_ui_availability(ui_type: UIType, logger: logging.Logger = None) -> bool:
    """Check if specified UI type is available."""
    if logger is None:
        logger = logging.getLogger(__name__)
        
    if ui_type == UIType.DEARPYGUI:
        try:
            import dearpygui
            return True
        except ImportError:
            logger.warning("DearPyGui not available. Install with: pip install dearpygui")
            return False
            
    return True  # Console and Curses are always available