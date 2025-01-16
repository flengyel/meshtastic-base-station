# terminal_ui.py

import curses
import asyncio
import logging
from typing import Optional
from src.station.ui.base import MeshtasticUI
from src.station.ui.terminal_views import CursesViews

class CursesUI(MeshtasticUI, CursesViews):
    """Terminal-based user interface using curses."""
    
    def __init__(self, data_handler, logger: Optional[logging.Logger] = None):
        MeshtasticUI.__init__(self, data_handler, logger)
        CursesViews.__init__(self)
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
        
        return instance

    async def start(self) -> None:
        """Initialize and start the UI."""
        self.running = True
        # Load initial data
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

    async def run(self):
        """Main UI loop with proper curses cleanup."""
        try:
            await self.start()
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
            await self.stop()

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
            
            self.screen.refresh()
        except Exception as e:
            self.logger.error(f"Error updating view: {e}")

            