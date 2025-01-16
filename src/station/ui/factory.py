# factory.py

import logging
from typing import Optional
from src.station.ui.base import MeshtasticUI
from src.station.ui.terminal_ui import CursesUI
from src.station.utils.platform_utils import UIType, check_ui_availability

class ConsoleUI(MeshtasticUI):
    """Basic console output UI."""
    
    async def start(self):
        self.running = True
        self.logger.info("Started console UI")

    async def stop(self):
        self.running = False
        self.logger.info("Stopped console UI")

    def handle_input(self):
        pass  # Console UI doesn't handle input

    async def update(self):
        pass  # Console UI updates through direct print statements

    async def refresh_nodes(self, nodes):
        # Basic console output implementation
        print("\nNodes:")
        for node in nodes:
            print(f"{node['timestamp']}: {node['id']} - {node['name']}")

    async def refresh_messages(self, messages):
        print("\nMessages:")
        for msg in messages:
            print(f"{msg['timestamp']}: {msg['from']} -> {msg['to']}: {msg['text']}")

    async def refresh_device_telemetry(self, telemetry):
        print("\nDevice Telemetry:")
        for entry in telemetry:
            print(f"{entry['timestamp']}: {entry['from_id']} - Battery: {entry['battery']}%")

    async def refresh_network_telemetry(self, telemetry):
        print("\nNetwork Telemetry:")
        for entry in telemetry:
            print(f"{entry['timestamp']}: {entry['online_nodes']}/{entry['total_nodes']} nodes")

    async def refresh_environment_telemetry(self, telemetry):
        print("\nEnvironment Telemetry:")
        for entry in telemetry:
            print(f"{entry['timestamp']}: {entry['temperature']}, {entry['humidity']}")

    async def show_error(self, message):
        print(f"\nError: {message}")

    async def show_status(self, message):
        print(f"\nStatus: {message}")

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
    return ConsoleUI(data_handler, logger)