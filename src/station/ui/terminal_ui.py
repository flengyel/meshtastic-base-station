# terminal_ui.py

import curses
import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from src.station.ui.base import MeshtasticUI
from src.station.utils.constants import DisplayConst

class CursesUI(MeshtasticUI):
    """Terminal-based user interface using curses."""
    
    def __init__(self, data_handler, logger: Optional[logging.Logger] = None):
        super().__init__(data_handler, logger)
        self.screen = None
        self.current_view = 'nodes'
        self.views = ['nodes', 'messages', 'device', 'network', 'environment']
        self.max_lines = 0
        self.max_cols = 0

    @classmethod
    async def create(cls, data_handler, logger=None):
        """Factory method to create UI instance using curses wrapper."""
        instance = cls(data_handler, logger)
        instance.screen = curses.initscr()
        
        # Initialize curses settings
        curses.start_color()
        curses.noecho()
        curses.cbreak()
        instance.screen.keypad(True)
        instance.screen.nodelay(1)  # Non-blocking input
        
        # Initialize color pairs
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        
        instance.max_lines, instance.max_cols = instance.screen.getmaxyx()
        
        # Load initial data
        await instance.load_initial_data()
        
        return instance

    async def cleanup(self):
        """Clean up curses settings."""
        if self.screen:
            self.screen.keypad(False)
            curses.nocbreak()
            curses.echo()
            curses.endwin()

    async def run(self):
        """Main UI loop with proper curses cleanup."""
        try:
            self.running = True
            while self.running:
                try:
                    self.handle_input()
                    await self.update()
                    await asyncio.sleep(0.1)
                except curses.error as e:
                    self.logger.error(f"Curses error: {e}")
                    self.running = False
                except Exception as e:
                    self.logger.error(f"Error in UI loop: {e}")
                    self.running = False
        finally:
            await self.cleanup()


        
    async def start(self) -> None:
        """Initialize and start the curses UI."""
        try:
            self.screen = curses.initscr()
            curses.start_color()
            curses.noecho()
            curses.cbreak()
            self.screen.keypad(True)
            self.screen.nodelay(1)  # Non-blocking input
            
            # Initialize color pairs
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
            
            self.max_lines, self.max_cols = self.screen.getmaxyx()
            
            # Load initial data
            await self.load_initial_data()
            
        except Exception as e:
            self.logger.error(f"Failed to start curses UI: {e}")
            raise

    async def stop(self) -> None:
        """Clean up and stop the curses UI."""
        try:
            if self.screen:
                self.screen.keypad(False)
                curses.nocbreak()
                curses.echo()
                curses.endwin()
        except Exception as e:
            self.logger.error(f"Error stopping curses UI: {e}")
        finally:
            self.running = False

    def handle_input(self) -> None:
        """Handle keyboard input."""
        try:
            key = self.screen.getch()
            if key == ord('q'):  # Quit on 'q'
                self.running = False
                return
            elif key != -1:  # Any other key pressed
                if key == ord('n'):
                    self.current_view = 'nodes'
                elif key == ord('m'):
                    self.current_view = 'messages'
                elif key == ord('d'):
                    self.current_view = 'device'
                elif key == ord('t'):
                    self.current_view = 'network'
                elif key == ord('e'):
                    self.current_view = 'environment'
                self.screen.clear()
        except Exception as e:
            self.logger.error(f"Error handling input: {e}")
            self.running = False  # Exit on error


    async def update(self) -> None:
        """Update the UI with latest data."""
        try:
            await self._draw_header()
            await self._update_current_view()
            self.screen.refresh()
        except Exception as e:
            self.logger.error(f"Error updating display: {e}")

    async def _draw_header(self) -> None:
        """Draw the header bar."""
        header = " Meshtastic Base Station Monitor "
        menu = " [N]odes [M]essages [D]evice [T]elemetry [E]nvironment [Q]uit "
        time_str = datetime.now().strftime("%H:%M:%S")
        
        try:
            # Draw header bar
            self.screen.attron(curses.color_pair(1))
            self.screen.addstr(0, 0, "=" * self.max_cols)
            self.screen.addstr(0, (self.max_cols - len(header)) // 2, header)
            self.screen.addstr(1, 0, "-" * self.max_cols)
            
            # Draw menu
            self.screen.attron(curses.color_pair(2))
            self.screen.addstr(2, 0, menu)
            self.screen.addstr(2, self.max_cols - len(time_str) - 1, time_str)
            self.screen.attroff(curses.color_pair(2))
        except Exception as e:
            self.logger.error(f"Error drawing header: {e}")

    async def _update_current_view(self) -> None:
        """Update the current view content."""
        try:
            if self.current_view == 'nodes':
                nodes = await self.data_handler.get_formatted_nodes()
                await self.refresh_nodes(nodes)
            elif self.current_view == 'messages':
                messages = await self.data_handler.get_formatted_messages()
                await self.refresh_messages(messages)
            elif self.current_view == 'device':
                telemetry = await self.data_handler.get_formatted_device_telemetry()
                await self.refresh_device_telemetry(telemetry)
            elif self.current_view == 'network':
                telemetry = await self.data_handler.get_formatted_network_telemetry()
                await self.refresh_network_telemetry(telemetry)
            elif self.current_view == 'environment':
                telemetry = await self.data_handler.get_formatted_environment_telemetry()
                await self.refresh_environment_telemetry(telemetry)
        except Exception as e:
            self.logger.error(f"Error updating current view: {e}")