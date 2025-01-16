# terminal_ui.py

import curses
import asyncio
import logging
from typing import Optional
from src.station.ui.base import MeshtasticUI
from src.station.ui.terminal_views import CursesViews

class CursesUI(CursesViews, MeshtasticUI):  # Changed order of inheritance
    """Terminal-based user interface using curses."""
    
    def __init__(self, data_handler, logger: Optional[logging.Logger] = None):
        # Initialize both parent classes
        CursesViews.__init__(self)
        MeshtasticUI.__init__(self, data_handler, logger)
        
        # Initialize UI state
        self.screen = None
        self.current_view = 'nodes'
        self.views = ['nodes', 'messages', 'device', 'network', 'environment']
        self.max_lines = 0
        self.max_cols = 0
        self._last_view = None
        self._last_update = 0

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
        
        return instance

    async def start(self) -> None:
        """Initialize and start the UI."""
        self.running = True
        await self.load_initial_data()
        
    async def stop(self) -> None:
        """Stop the UI and clean up resources."""
        await self.cleanup()
        self.running = False

    async def cleanup(self):
        """Clean up curses settings."""
        if self.screen:
            self.screen.keypad(False)
            curses.nocbreak()
            curses.echo()
            curses.endwin()

    def handle_input(self):
        """Handle keyboard input."""
        try:
            ch = self.screen.getch()
            if ch == ord('q'):
                self.running = False
            elif ch != -1:
                if ch == ord('n'):
                    self.current_view = 'nodes'
                elif ch == ord('m'):
                    self.current_view = 'messages'
                elif ch == ord('d'):
                    self.current_view = 'device'
                elif ch == ord('t'):
                    self.current_view = 'network'
                elif ch == ord('e'):
                    self.current_view = 'environment'
                self.screen.clear()
        except Exception as e:
            self.logger.error(f"Error handling input: {e}")
            self.running = False

    async def update(self):
        """Update the current view."""
        try:
            # Rate limit updates
            await asyncio.sleep(0.1)  # Check input more frequently
            
            # Clear screen and draw border
            self.screen.clear()
            self.screen.box()
            
            # Draw header
            header = " Meshtastic Base Station "
            header_pos = (self.max_cols - len(header)) // 2
            self.screen.addstr(0, header_pos, header)
            
            # Update data every 5 seconds or on view change
            current_time = int(asyncio.get_event_loop().time())
            if (current_time - self._last_update) >= 5 or self._last_view != self.current_view:
                self._last_view = self.current_view
                self._last_update = current_time
                
                # Update based on current view
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
            
            # Draw menu at bottom
            menu = " [N]odes [M]essages [D]evice [T]elemetry [E]nvironment [Q]uit "
            menu_pos = (self.max_cols - len(menu)) // 2
            self.screen.addstr(self.max_lines-1, menu_pos, menu)
            
            # Move cursor to bottom right
            self.screen.move(self.max_lines-1, self.max_cols-1)
            
            # Refresh screen
            self.screen.refresh()
        except Exception as e:
            self.logger.error(f"Error updating view: {e}")

    async def run(self):
        """Main UI loop with proper curses cleanup."""
        try:
            await self.start()
            while self.running:
                try:
                    self.handle_input()
                    await self.update()
                except curses.error as e:
                    self.logger.error(f"Curses error: {e}")
                    self.running = False
                except Exception as e:
                    self.logger.error(f"Error in UI loop: {e}")
                    self.running = False
        finally:
            await self.stop()
            