# terminal_ui.py

import curses
import asyncio
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime

from src.station.ui.base import MeshtasticUI
from src.station.utils.constants import DisplayConst

class CursesUI(MeshtasticUI):
    """Curses-based terminal UI for Meshtastic Base Station."""
    
    def __init__(self, data_handler, logger: Optional[logging.Logger] = None):
        super().__init__(data_handler, logger)
        self.screen = None
        self.current_view = 'nodes'  # Default view
        self.views = ['nodes', 'messages', 'device', 'network', 'environment']
        self.max_lines = 0
        self.max_cols = 0

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
            
            self.max_lines, self.max_cols = self.screen.getmaxyx()
            
            # Load initial data
            await self.load_initial_data()
            
        except Exception as e:
            self.logger.error(f"Failed to start curses UI: {e}")
            raise

    async def stop(self) -> None:
        """Clean up and stop the curses UI."""
        if self.screen:
            try:
                self.screen.keypad(False)
                curses.nocbreak()
                curses.echo()
                curses.endwin()
            except Exception as e:
                self.logger.error(f"Error stopping curses UI: {e}")

    def handle_input(self) -> None:
        """Handle keyboard input."""
        try:
            key = self.screen.getch()
            if key != -1:  # Key was pressed
                if key == ord('q'):
                    self.running = False
                elif key == ord('n'):
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
                await self.refresh_nodes(await self.data_handler.get_formatted_nodes())
            elif self.current_view == 'messages':
                await self.refresh_messages(await self.data_handler.get_formatted_messages())
            elif self.current_view == 'device':
                await self.refresh_device_telemetry(
                    await self.data_handler.get_formatted_device_telemetry()
                )
            elif self.current_view == 'network':
                await self.refresh_network_telemetry(
                    await self.data_handler.get_formatted_network_telemetry()
                )
            elif self.current_view == 'environment':
                await self.refresh_environment_telemetry(
                    await self.data_handler.get_formatted_environment_telemetry()
                )
        except Exception as e:
            self.logger.error(f"Error updating current view: {e}")

    async def refresh_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """Refresh the nodes display."""
        try:
            if not nodes:
                self.screen.addstr(4, 2, "No nodes found")
                return

            # Draw headers
            self.screen.attron(curses.color_pair(3))
            self.screen.addstr(4, 2, f"{'Node ID':<10} {'Name':<20} {'Last Seen':<20}")
            self.screen.attroff(curses.color_pair(3))
            
            # Draw nodes
            for i, node in enumerate(sorted(nodes, key=lambda x: x['timestamp']), start=1):
                if 4 + i < self.max_lines - 1:
                    self.screen.addstr(4 + i, 2, 
                        f"{node['id']:<10} {node['name']:<20} {node['timestamp']:<20}")
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
            self.screen.addstr(4, 2, 
                f"{'Time':<8} {'From':<10} {'To':<10} Message")
            self.screen.attroff(curses.color_pair(3))
            
            # Draw messages
            for i, msg in enumerate(sorted(messages, key=lambda x: x['timestamp']), start=1):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
                    self.screen.addstr(4 + i, 2,
                        f"{time_str:<8} {msg['from']:<10} {msg['to']:<10} {msg['text']}")
        except Exception as e:
            self.logger.error(f"Error refreshing messages: {e}")

    async def refresh_device_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh device telemetry display."""
        try:
            if not telemetry:
                self.screen.addstr(4, 2, "No device telemetry found")
                return

            # Draw headers
            self.screen.attron(curses.color_pair(3))
            self.screen.addstr(4, 2,
                f"{'Time':<8} {'Node ID':<10} {'Battery':<8} {'Voltage':<8} {'Ch Util':<8}")
            self.screen.attroff(curses.color_pair(3))
            
            # Draw telemetry
            for i, entry in enumerate(
                sorted(telemetry, key=lambda x: x['timestamp'])[-DisplayConst.MAX_DEVICE_TELEMETRY:],
                start=1
            ):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                    self.screen.addstr(4 + i, 2,
                        f"{time_str:<8} {entry['from_id']:<10} "
                        f"{entry['battery']:>3}% {float(entry['voltage']):>7.2f}V "
                        f"{float(entry['channel_util']):>7.2f}%")
        except Exception as e:
            self.logger.error(f"Error refreshing device telemetry: {e}")

    async def refresh_network_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh network telemetry display."""
        try:
            if not telemetry:
                self.screen.addstr(4, 2, "No network telemetry found")
                return

            # Draw headers
            self.screen.attron(curses.color_pair(3))
            self.screen.addstr(4, 2,
                f"{'Time':<8} {'Node ID':<10} {'Nodes':<12} {'TX':<6} {'RX':<6}")
            self.screen.attroff(curses.color_pair(3))
            
            # Draw telemetry
            for i, entry in enumerate(
                sorted(telemetry, key=lambda x: x['timestamp'])[-DisplayConst.MAX_NETWORK_TELEMETRY:],
                start=1
            ):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                    self.screen.addstr(4 + i, 2,
                        f"{time_str:<8} {entry['from_id']:<10} "
                        f"{entry['online_nodes']}/{entry['total_nodes']:<8} "
                        f"{entry['packets_tx']:>5} {entry['packets_rx']:>5}")
        except Exception as e:
            self.logger.error(f"Error refreshing network telemetry: {e}")

    async def refresh_environment_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh environment telemetry display."""
        try:
            if not telemetry:
                self.screen.addstr(4, 2, "No environment telemetry found")
                return

            # Draw headers
            self.screen.attron(curses.color_pair(3))
            self.screen.addstr(4, 2,
                f"{'Time':<8} {'Node ID':<10} {'Temp':<8} {'Humidity':<8} {'Pressure':<10}")
            self.screen.attroff(curses.color_pair(3))
            
            # Draw telemetry
            for i, entry in enumerate(sorted(telemetry, key=lambda x: x['timestamp']), start=1):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                    self.screen.addstr(4 + i, 2,
                        f"{time_str:<8} {entry['from_id']:<10} "
                        f"{entry['temperature']:<8} {entry['humidity']:<8} "
                        f"{entry['pressure']:<10}")
        except Exception as e:
            self.logger.error(f"Error refreshing environment telemetry: {e}")

    async def show_error(self, message: str) -> None:
        """Display an error message."""
        try:
            self.screen.attron(curses.color_pair(1))  # Red for errors
            self.screen.addstr(self.max_lines-1, 0, f"Error: {message}"[:self.max_cols-1])
            self.screen.attroff(curses.color_pair(1))
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
