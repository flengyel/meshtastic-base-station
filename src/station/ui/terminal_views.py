# terminal_views.py

import curses
from datetime import datetime
from typing import Dict, List, Any

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