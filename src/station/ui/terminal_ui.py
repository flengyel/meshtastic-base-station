# terminal_ui.py

import curses
import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
from src.station.ui.base import MeshtasticUI
from src.station.utils.constants import DisplayConst

class CursesViews:
    """View implementations for the curses-based UI."""
    
    async def refresh_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """Refresh the nodes display."""
        try:
            if not nodes:
                self.screen.addstr(4, 2, "No nodes found")
                return

            # Draw headers
            self.screen.attron(curses.color_pair(3))
            self.screen.addstr(4, 2, f"{'Node ID':<12} {'Name':<20} {'Last Seen':<20}")
            self.screen.attroff(curses.color_pair(3))
            
            # Draw nodes
            for i, node in enumerate(sorted(nodes, key=lambda x: x['timestamp']), start=1):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(node['timestamp']).strftime("%H:%M:%S")
                    self.screen.addstr(4 + i, 2, 
                        f"{node['id']:<12} {node['name']:<20} {time_str:<20}")
        except Exception as e:
            self.logger.error(f"Error refreshing nodes: {e}")

    async def refresh_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Refresh the messages display."""
        try:
            if not messages:
                self.screen.addstr(4, 2, "No messages found")
                return

            # Draw headers
            self.screen.attron(curses.color_pair(3))
            self.screen.addstr(4, 2, f"{'Time':<8} {'From':<12} {'To':<12} Message")
            self.screen.attroff(curses.color_pair(3))
            
            # Draw messages
            for i, msg in enumerate(sorted(messages, key=lambda x: x['timestamp'], reverse=True), start=1):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
                    text_width = self.max_cols - 36
                    text = msg['text'][:text_width]
                    self.screen.addstr(4 + i, 2,
                        f"{time_str:<8} {msg['from']:<12} {msg['to']:<12} {text}")
        except Exception as e:
            self.logger.error(f"Error refreshing messages: {e}")

    async def refresh_device_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh device telemetry display."""
        try:
            if not telemetry:
                self.screen.addstr(4, 2, "No device telemetry found")
                return

            # Headers
            self.screen.attron(curses.color_pair(3))
            self.screen.addstr(4, 2, f"{'Time':<8} {'Node ID':<12} {'Battery':<8} {'Voltage':<8} {'Ch Util':<8}")
            self.screen.attroff(curses.color_pair(3))

            # Entries
            for i, entry in enumerate(sorted(telemetry, key=lambda x: x['timestamp'])[-10:], start=1):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                    self.screen.addstr(4 + i, 2, 
                        f"{time_str:<8} {entry['from_id']:<12} {entry['battery']:>3}% "
                        f"{float(entry['voltage']):>7.2f}V {float(entry['channel_util']):>7.2f}%")
        except Exception as e:
            self.logger.error(f"Error refreshing device telemetry: {e}")

    async def refresh_network_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh network telemetry display."""
        try:
            if not telemetry:
                self.screen.addstr(4, 2, "No network telemetry found")
                return

            # Headers
            self.screen.attron(curses.color_pair(3))
            self.screen.addstr(4, 2, f"{'Time':<8} {'Node ID':<12} {'Nodes':<12} {'TX':<8} {'RX':<8}")
            self.screen.attroff(curses.color_pair(3))

            # Entries
            for i, entry in enumerate(sorted(telemetry, key=lambda x: x['timestamp'])[-5:], start=1):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                    self.screen.addstr(4 + i, 2,
                        f"{time_str:<8} {entry['from_id']:<12} {entry['online_nodes']}/{entry['total_nodes']} "
                        f"{entry['packets_tx']:>7} {entry['packets_rx']:>7}")
        except Exception as e:
            self.logger.error(f"Error refreshing network telemetry: {e}")

    async def refresh_environment_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh environment telemetry display."""
        try:
            if not telemetry:
                self.screen.addstr(4, 2, "No environment telemetry found")
                return

            # Headers
            self.screen.attron(curses.color_pair(3))
            self.screen.addstr(4, 2, f"{'Time':<8} {'Node ID':<12} {'Temp':<8} {'Humidity':<8} {'Pressure':<10}")
            self.screen.attroff(curses.color_pair(3))

            # Entries
            for i, entry in enumerate(sorted(telemetry, key=lambda x: x['timestamp']), start=1):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                    self.screen.addstr(4 + i, 2,
                        f"{time_str:<8} {entry['from_id']:<12} {entry['temperature']} "
                        f"{entry['humidity']} {entry['pressure']}")
        except Exception as e:
            self.logger.error(f"Error refreshing environment telemetry: {e}")

    async def show_error(self, message: str) -> None:
        """Display an error message."""
        try:
            self.screen.attron(curses.color_pair(4))  # Red for errors
            self.screen.addstr(self.max_lines-1, 0, f"Error: {message}"[:self.max_cols-1])
            self.screen.attroff(curses.color_pair(4))
            self.screen.refresh()
        except Exception as e:
            self.logger.error(f"Error showing error message: {e}")

    async def show_status(self, message: str) -> None:
        """Display a status message."""
        try:
            self.screen.attron(curses.color_pair(2))  # Yellow for status
            self.screen.addstr(self.max_lines-2, 0, f"Status: {message}"[:self.max_cols-1])
            self.screen.attroff(curses.color_pair(2))
            self.screen.refresh()
        except Exception as e:
            self.logger.error(f"Error showing status message: {e}")

class CursesUI(MeshtasticUI, CursesViews):
    """Terminal-based user interface using curses."""
    
    async def start(self) -> None:
        """Initialize and start the UI."""
        # Most initialization is handled in create() for curses
        self.running = True
        
    async def stop(self) -> None:
        """Stop the UI and clean up resources."""
        await self.cleanup()
        self.running = False
    
    def __init__(self, data_handler, logger: Optional[logging.Logger] = None):
        MeshtasticUI.__init__(self, data_handler, logger)
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