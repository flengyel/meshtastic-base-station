# src/station/ui/terminal_ui.py

import curses
import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
import logging
from src.station.utils.constants import DisplayConst

from src.station.ui.base import MeshtasticUI

class CursesUI(MeshtasticUI):
    """Curses-based terminal UI for Meshtastic Base Station."""
    
    def __init__(self, data_handler, logger: Optional[logging.Logger] = None):
        self.data_handler = data_handler
        self.logger = logger or logging.getLogger(__name__)
        self.screen = None
        self.current_view = 'nodes'  # Default view
        self.views = ['nodes', 'messages', 'device', 'network', 'environment']
        self.running = False
        self.max_lines = 0
        self.max_cols = 0

    def start(self):
        """Initialize and start the curses UI."""
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
        self.running = True

    def stop(self):
        """Clean up and close the curses UI."""
        if self.screen:
            self.screen.keypad(False)
            curses.nocbreak()
            curses.echo()
            curses.endwin()
        self.running = False

    def handle_input(self):
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
        except Exception as e:
            self.logger.error(f"Error handling input: {e}")

    def draw_header(self):
        """Draw the header bar."""
        header = " Meshtastic Base Station Monitor "
        menu = " [N]odes [M]essages [D]evice [T]elemetry [E]nvironment [Q]uit "
        time_str = datetime.now().strftime("%H:%M:%S")
        
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

    async def update_display(self):
        """Update the display based on current view."""
        try:
            self.screen.clear()
            self.draw_header()
            
            content_start = 4  # Start after header
            
            if self.current_view == 'nodes':
                await self.draw_nodes(content_start)
            elif self.current_view == 'messages':
                await self.draw_messages(content_start)
            elif self.current_view == 'device':
                await self.draw_device_telemetry(content_start)
            elif self.current_view == 'network':
                await self.draw_network_telemetry(content_start)
            elif self.current_view == 'environment':
                await self.draw_environment_telemetry(content_start)
            
            self.screen.refresh()
            
        except Exception as e:
            self.logger.error(f"Error updating display: {e}")

    async def draw_nodes(self, start_line: int):
        """Draw the nodes view."""
        nodes = await self.data_handler.get_formatted_nodes()
        if not nodes:
            self.screen.addstr(start_line, 2, "No nodes found")
            return

        # Draw column headers
        self.screen.attron(curses.color_pair(3))
        self.screen.addstr(start_line, 2, f"{'Node ID':<10} {'Name':<20} {'Last Seen':<20}")
        self.screen.attroff(curses.color_pair(3))
        
        # Draw nodes
        line = start_line + 1
        for node in sorted(nodes, key=lambda x: x['timestamp'], reverse=True):
            if line < self.max_lines - 1:
                self.screen.addstr(line, 2, 
                    f"{node['id']:<10} {node['name']:<20} {node['timestamp']:<20}")
                line += 1

    async def draw_messages(self, start_line: int):
        """Draw the messages view."""
        messages = await self.data_handler.get_formatted_messages()
        if not messages:
            self.screen.addstr(start_line, 2, "No messages found")
            return

        # Draw column headers
        self.screen.attron(curses.color_pair(3))
        self.screen.addstr(start_line, 2, 
            f"{'Time':<8} {'From':<10} {'To':<10} Message")
        self.screen.attroff(curses.color_pair(3))
        
        # Draw messages
        line = start_line + 1
        for msg in sorted(messages, key=lambda x: x['timestamp'], reverse=True):
            if line < self.max_lines - 1:
                time_str = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
                self.screen.addstr(line, 2, 
                    f"{time_str:<8} {msg['from']:<10} {msg['to']:<10} {msg['text']}")
                line += 1

    async def draw_device_telemetry(self, start_line: int):
        """Draw the device telemetry view."""
        telemetry = await self.data_handler.get_formatted_device_telemetry()
        if not telemetry:
            self.screen.addstr(start_line, 2, "No device telemetry found")
            return

        # Draw column headers
        self.screen.attron(curses.color_pair(3))
        self.screen.addstr(start_line, 2,
            f"{'Time':<8} {'Node ID':<10} {'Battery':<8} {'Voltage':<8} {'Ch Util':<8}")
        self.screen.attroff(curses.color_pair(3))
        
        # Draw telemetry
        line = start_line + 1
        for entry in sorted(telemetry, key=lambda x: x['timestamp'], 
                          reverse=True)[:DisplayConst.MAX_DEVICE_TELEMETRY]:
            if line < self.max_lines - 1:
                time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                self.screen.addstr(line, 2,
                    f"{time_str:<8} {entry['from_id']:<10} "
                    f"{entry['battery']:>3}% {float(entry['voltage']):>7.2f}V "
                    f"{float(entry['channel_util']):>7.2f}%")
                line += 1

    async def draw_network_telemetry(self, start_line: int):
        """Draw the network telemetry view."""
        telemetry = await self.data_handler.get_formatted_network_telemetry()
        if not telemetry:
            self.screen.addstr(start_line, 2, "No network telemetry found")
            return

        # Draw column headers
        self.screen.attron(curses.color_pair(3))
        self.screen.addstr(start_line, 2,
            f"{'Time':<8} {'Node ID':<10} {'Nodes':<12} {'TX':<6} {'RX':<6}")
        self.screen.attroff(curses.color_pair(3))
        
        # Draw telemetry
        line = start_line + 1
        for entry in sorted(telemetry, key=lambda x: x['timestamp'], 
                          reverse=True)[:DisplayConst.MAX_NETWORK_TELEMETRY]:
            if line < self.max_lines - 1:
                time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                self.screen.addstr(line, 2,
                    f"{time_str:<8} {entry['from_id']:<10} "
                    f"{entry['online_nodes']}/{entry['total_nodes']:<8} "
                    f"{entry['packets_tx']:>5} {entry['packets_rx']:>5}")
                line += 1

    async def draw_environment_telemetry(self, start_line: int):
        """Draw the environment telemetry view."""
        telemetry = await self.data_handler.get_formatted_environment_telemetry()
        if not telemetry:
            self.screen.addstr(start_line, 2, "No environment telemetry found")
            return

        # Draw column headers
        self.screen.attron(curses.color_pair(3))
        self.screen.addstr(start_line, 2,
            f"{'Time':<8} {'Node ID':<10} {'Temp':<8} {'Humidity':<8} {'Pressure':<10}")
        self.screen.attroff(curses.color_pair(3))
        
        # Draw telemetry
        line = start_line + 1
        for entry in sorted(telemetry, key=lambda x: x['timestamp'], reverse=True):
            if line < self.max_lines - 1:
                time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                self.screen.addstr(line, 2,
                    f"{time_str:<8} {entry['from_id']:<10} "
                    f"{entry['temperature']:<8} {entry['humidity']:<8} "
                    f"{entry['pressure']:<10}")
                line += 1

    async def run(self):
        """Main UI loop."""
        try:
            self.start()
            while self.running:
                self.handle_input()
                await self.update_display()
                await asyncio.sleep(0.1)  # Prevent high CPU usage
        except Exception as e:
            self.logger.error(f"Error in UI loop: {e}")
        finally:
            self.stop()