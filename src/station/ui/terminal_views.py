# terminal_views.py

import curses
from datetime import datetime
from typing import Dict, List, Any

from src.station.utils.constants import DisplayConst

class CursesViews:
    """View implementations for the curses-based UI."""

    def __init__(self):
        """Initialize the views class."""
        self.screen = None  # Will be set by CursesUI
        self.max_lines = 0  # Will be set by CursesUI
        self.max_cols = 0   # Will be set by CursesUI
        self.logger = None  # Will be set by CursesUI

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
            self.screen.addstr(4, 2, 
                f"{'Time':<8} {'From':<12} {'To':<12} Message")
            self.screen.attroff(curses.color_pair(3))
            
            # Draw messages (newest first)
            for i, msg in enumerate(sorted(messages, key=lambda x: x['timestamp'], reverse=True), start=1):
                if 4 + i < self.max_lines - 1:
                    time_str = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
                    # Truncate long messages to fit screen width
                    text_width = self.max_cols - 36  # Account for other columns and spacing
                    text = msg['text'][:text_width] + ('...' if len(msg['text']) > text_width else '')
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

            self._draw_device_telemetry_headers()
            self._draw_device_telemetry_entries(telemetry)
        except Exception as e:
            self.logger.error(f"Error refreshing device telemetry: {e}")

    def _draw_device_telemetry_headers(self) -> None:
        """Draw headers for device telemetry."""
        self.screen.attron(curses.color_pair(3))
        self.screen.addstr(4, 2,
            f"{'Time':<8} {'Node ID':<12} {'Battery':<8} {'Voltage':<8} {'Ch Util':<8}")
        self.screen.attroff(curses.color_pair(3))

    def _draw_device_telemetry_entries(self, telemetry: List[Dict[str, Any]]) -> None:
        """Draw device telemetry entries."""
        for i, entry in enumerate(
            sorted(telemetry, key=lambda x: x['timestamp'])[-DisplayConst.MAX_DEVICE_TELEMETRY:],
            start=1
        ):
            if 4 + i < self.max_lines - 1:
                time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                battery = int(entry['battery'])
                
                # Color code based on battery level
                if battery < 20:
                    self.screen.attron(curses.color_pair(4))  # Red
                elif battery < 50:
                    self.screen.attron(curses.color_pair(2))  # Yellow
                    
                self.screen.addstr(4 + i, 2,
                    f"{time_str:<8} {entry['from_id']:<12} "
                    f"{battery:>3}% {float(entry['voltage']):>7.2f}V "
                    f"{float(entry['channel_util']):>7.2f}%")
                
                if battery < 50:
                    self.screen.attroff(curses.color_pair(4 if battery < 20 else 2))

    async def refresh_network_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh network telemetry display."""
        try:
            if not telemetry:
                self.screen.addstr(4, 2, "No network telemetry found")
                return

            self._draw_network_telemetry_headers()
            self._draw_network_telemetry_entries(telemetry)
        except Exception as e:
            self.logger.error(f"Error refreshing network telemetry: {e}")

    def _draw_network_telemetry_headers(self) -> None:
        """Draw headers for network telemetry."""
        self.screen.attron(curses.color_pair(3))
        self.screen.addstr(4, 2,
            f"{'Time':<8} {'Node ID':<12} {'Nodes':<12} {'TX':<8} {'RX':<8}")
        self.screen.attroff(curses.color_pair(3))

    def _draw_network_telemetry_entries(self, telemetry: List[Dict[str, Any]]) -> None:
        """Draw network telemetry entries."""
        for i, entry in enumerate(
            sorted(telemetry, key=lambda x: x['timestamp'])[-DisplayConst.MAX_NETWORK_TELEMETRY:],
            start=1
        ):
            if 4 + i < self.max_lines - 1:
                time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                nodes_str = f"{entry['online_nodes']}/{entry['total_nodes']}"
                
                # Color code based on online ratio
                ratio = int(entry['online_nodes']) / int(entry['total_nodes'])
                if ratio < 0.5:
                    self.screen.attron(curses.color_pair(4))  # Red
                elif ratio < 0.8:
                    self.screen.attron(curses.color_pair(2))  # Yellow
                    
                self.screen.addstr(4 + i, 2,
                    f"{time_str:<8} {entry['from_id']:<12} {nodes_str:<12} "
                    f"{entry['packets_tx']:>7} {entry['packets_rx']:>7}")
                
                if ratio < 0.8:
                    self.screen.attroff(curses.color_pair(4 if ratio < 0.5 else 2))

    async def refresh_environment_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh environment telemetry display."""
        try:
            if not telemetry:
                self.screen.addstr(4, 2, "No environment telemetry found")
                return

            self._draw_environment_telemetry_headers()
            self._draw_environment_telemetry_entries(telemetry)
        except Exception as e:
            self.logger.error(f"Error refreshing environment telemetry: {e}")

    def _draw_environment_telemetry_headers(self) -> None:
        """Draw headers for environment telemetry."""
        self.screen.attron(curses.color_pair(3))
        self.screen.addstr(4, 2,
            f"{'Time':<8} {'Node ID':<12} {'Temp':<8} {'Humidity':<8} {'Pressure':<10}")
        self.screen.attroff(curses.color_pair(3))

    def _draw_environment_telemetry_entries(self, telemetry: List[Dict[str, Any]]) -> None:
        """Draw environment telemetry entries."""
        for i, entry in enumerate(sorted(telemetry, key=lambda x: x['timestamp']), start=1):
            if 4 + i < self.max_lines - 1:
                time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                temp, humidity, pressure = self._extract_environment_values(entry)
                self._color_code_temperature(temp)
                self.screen.addstr(4 + i, 2,
                    f"{time_str:<8} {entry['from_id']:<12} "
                    f"{temp:>6.1f}°C {humidity:>6.1f}% {pressure:>8}hPa")
                self._reset_color_code_temperature(temp)

    def _extract_environment_values(self, entry: Dict[str, Any]) -> tuple:
        """Extract and format environment telemetry values."""
        temp = float(entry['temperature'].replace('°C', ''))
        humidity = float(entry['humidity'].replace('%', ''))
        pressure = entry['pressure'].replace('hPa', '')
        return temp, humidity, pressure

    def _color_code_temperature(self, temp: float) -> None:
        """Color code temperature based on value."""
        if temp > 30 or temp < 10:
            self.screen.attron(curses.color_pair(4))  # Red
        elif temp > 25 or temp < 15:
            self.screen.attron(curses.color_pair(2))  # Yellow

    def _reset_color_code_temperature(self, temp: float) -> None:
        """Reset color code for temperature."""
        if temp > 25 or temp < 15:
            self.screen.attroff(curses.color_pair(4 if temp > 30 or temp < 10 else 2))

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