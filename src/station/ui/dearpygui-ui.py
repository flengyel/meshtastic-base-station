# src/station/ui/dearpygui_ui.py

import dearpygui.dearpygui as dpg
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.station.ui.base import MeshtasticUI
from src.station.utils.constants import DisplayConst

class DearPyGuiUI(MeshtasticUI):
    """DearPyGUI-based UI implementation for Meshtastic Base Station."""

    def __init__(self, data_handler, logger: Optional[logging.Logger] = None):
        super().__init__(data_handler, logger)
        self.window_width = 1280
        self.window_height = 800
        self.table_row_bg = [32, 32, 32]
        self.error_color = [255, 0, 0]
        self.status_color = [0, 255, 0]
        
        # Store widget references
        self.telemetry_plots = {}
        self.status_text = None
        self.error_text = None
        self.data_buffers = {
            'battery': {'times': [], 'values': []},
            'voltage': {'times': [], 'values': []},
            'tx': {'times': [], 'values': []},
            'rx': {'times': [], 'values': []},
            'temperature': {'times': [], 'values': []},
            'humidity': {'times': [], 'values': []}
        }
        self.buffer_size = 100  # Maximum number of points to keep in plots
        self.last_resize_check = 0
        self.resize_interval = 1.0  # Check resize every second

    async def start(self) -> None:
        """Initialize and start DearPyGUI."""
        try:
        dpg.create_context()
        dpg.create_viewport(title="Meshtastic Base Station", 
                          width=self.window_width, 
                          height=self.window_height)
        
        # Load fonts
        with dpg.font_registry():
            default_font = dpg.add_font("fonts/DejaVuSansMono.ttf", 15)
            dpg.bind_font(default_font)

        # Create main window
        with dpg.window(label="Meshtastic Base Station", tag="main_window"):
            # Create tabbar
            with dpg.tab_bar():
                with dpg.tab(label="Nodes"):
                    self._create_nodes_view()
                with dpg.tab(label="Messages"):
                    self._create_messages_view()
                with dpg.tab(label="Device Telemetry"):
                    self._create_device_telemetry_view()
                with dpg.tab(label="Network Status"):
                    self._create_network_telemetry_view()
                with dpg.tab(label="Environment"):
                    self._create_environment_telemetry_view()

            # Status and error area at bottom
            with dpg.group(horizontal=True):
                self.status_text = dpg.add_text("Ready")
                self.error_text = dpg.add_text("", color=self.error_color)

        dpg.setup_dearpygui()
        dpg.show_viewport()
        
        # Load initial data
        await self.load_initial_data()
        
        except Exception as e:
            self.logger.error(f"Failed to start DearPyGUI: {e}", exc_info=True)
            raise

    def _create_nodes_view(self):
        """Create the nodes view tab."""
        with dpg.table(header_row=True, policy=dpg.mvTable_SizingFixedFit,
                      borders_innerH=True, borders_outerH=True, borders_innerV=True,
                      borders_outerV=True, tag="nodes_table"):
            dpg.add_table_column(label="ID")
            dpg.add_table_column(label="Name")
            dpg.add_table_column(label="Last Seen")
            dpg.add_table_column(label="Status")

    def _create_messages_view(self):
        """Create the messages view tab."""
        with dpg.table(header_row=True, policy=dpg.mvTable_SizingFixedFit,
                      borders_innerH=True, borders_outerH=True, borders_innerV=True,
                      borders_outerV=True, tag="messages_table"):
            dpg.add_table_column(label="Time")
            dpg.add_table_column(label="From")
            dpg.add_table_column(label="To")
            dpg.add_table_column(label="Message", width_stretch=True)

    def _create_device_telemetry_view(self):
        """Create the device telemetry view tab."""
        with dpg.group():
            # Real-time plots
            with dpg.plot(label="Battery Levels", height=200, width=-1, tag="battery_plot"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Time", tag="battery_x_axis")
                dpg.add_plot_axis(dpg.mvYAxis, label="Battery %", tag="battery_y_axis")
                self.telemetry_plots["battery"] = dpg.add_line_series([], [], label="Battery %", parent="battery_y_axis")

            with dpg.plot(label="Voltage Levels", height=200, width=-1, tag="voltage_plot"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Time", tag="voltage_x_axis")
                dpg.add_plot_axis(dpg.mvYAxis, label="Voltage", tag="voltage_y_axis")
                self.telemetry_plots["voltage"] = dpg.add_line_series([], [], label="Voltage", parent="voltage_y_axis")

            # Current values table
            with dpg.table(header_row=True, tag="device_telemetry_table"):
                dpg.add_table_column(label="Node")
                dpg.add_table_column(label="Battery")
                dpg.add_table_column(label="Voltage")
                dpg.add_table_column(label="Channel Util")

    def _create_network_telemetry_view(self):
        """Create the network telemetry view tab."""
        with dpg.group():
            # Network status plot
            with dpg.plot(label="Network Activity", height=200, width=-1, tag="network_plot"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Time", tag="network_x_axis")
                dpg.add_plot_axis(dpg.mvYAxis, label="Packets", tag="network_y_axis")
                self.telemetry_plots["tx"] = dpg.add_line_series([], [], label="TX", parent="network_y_axis")
                self.telemetry_plots["rx"] = dpg.add_line_series([], [], label="RX", parent="network_y_axis")

            # Node status table
            with dpg.table(header_row=True, tag="network_status_table"):
                dpg.add_table_column(label="Time")
                dpg.add_table_column(label="Online Nodes")
                dpg.add_table_column(label="Total Nodes")
                dpg.add_table_column(label="TX")
                dpg.add_table_column(label="RX")

    def _create_environment_telemetry_view(self):
        """Create the environment telemetry view tab."""
        with dpg.group():
            # Temperature and humidity plots
            with dpg.plot(label="Environmental Data", height=300, width=-1, tag="env_plot"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Time", tag="env_x_axis")
                
                # Temperature axis (left)
                dpg.add_plot_axis(dpg.mvYAxis, label="Temperature (°C)", tag="temp_y_axis")
                self.telemetry_plots["temperature"] = dpg.add_line_series(
                    [], [], label="Temperature", parent="temp_y_axis"
                )
                
                # Humidity axis (right)
                dpg.add_plot_axis(dpg.mvYAxis, label="Humidity %", tag="humidity_y_axis", location=dpg.mvPlotLocation_Right)
                self.telemetry_plots["humidity"] = dpg.add_line_series(
                    [], [], label="Humidity", parent="humidity_y_axis"
                )

            # Current values table
            with dpg.table(header_row=True, tag="environment_table"):
                dpg.add_table_column(label="Node")
                dpg.add_table_column(label="Temperature")
                dpg.add_table_column(label="Humidity")
                dpg.add_table_column(label="Pressure")

    async def stop(self) -> None:
        """Clean up and stop DearPyGUI."""
        try:
            # Clear all data buffers
            for buffer in self.data_buffers.values():
                buffer['times'].clear()
                buffer['values'].clear()
            
            # Stop viewport and destroy context
            if dpg.is_viewport_available():
                dpg.stop_dearpygui()
            dpg.destroy_context()
            
        except Exception as e:
            self.logger.error(f"Error stopping DearPyGUI: {e}", exc_info=True)
        finally:
            self.running = False

    def handle_input(self) -> None:
        """Handle DearPyGUI input events and window management."""
        try:
            current_time = time.time()
            
            # Check for window resize periodically
            if current_time - self.last_resize_check > self.resize_interval:
                self.last_resize_check = current_time
                self._handle_window_resize()
            
            dpg.render_dearpygui_frame()
            
        except Exception as e:
            self.logger.error(f"Error handling input: {e}", exc_info=True)
            
    def _handle_window_resize(self) -> None:
        """Handle viewport and window resizing."""
        try:
            viewport_width = dpg.get_viewport_width()
            viewport_height = dpg.get_viewport_height()
            
            if viewport_width != self.window_width or viewport_height != self.window_height:
                self.window_width = viewport_width
                self.window_height = viewport_height
                
                # Update main window size
                dpg.set_item_width("main_window", viewport_width)
                dpg.set_item_height("main_window", viewport_height)
                
                # Update plot sizes
                plot_width = max(viewport_width - 40, 400)  # Leave margin
                for plot_tag in ["battery_plot", "voltage_plot", "network_plot", "env_plot"]:
                    if dpg.does_item_exist(plot_tag):
                        dpg.set_item_width(plot_tag, plot_width)
                        
        except Exception as e:
            self.logger.error(f"Error handling window resize: {e}", exc_info=True)
            
    def _update_data_buffer(self, buffer_name: str, time_val: float, value: float) -> None:
        """Update a data buffer with new values, maintaining buffer size."""
        buffer = self.data_buffers[buffer_name]
        buffer['times'].append(time_val)
        buffer['values'].append(value)
        
        # Remove oldest values if buffer is full
        if len(buffer['times']) > self.buffer_size:
            buffer['times'].pop(0)
            buffer['values'].pop(0)

    async def update(self) -> None:
        """Update the UI with latest data."""
        # DearPyGUI updates are handled in refresh_* methods
        pass

    async def refresh_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """Refresh the nodes table."""
        dpg.delete_item("nodes_table", children_only=True, slot=1)
        
        for node in sorted(nodes, key=lambda x: x['timestamp'], reverse=True):
            with dpg.table_row(parent="nodes_table"):
                dpg.add_text(node['id'])
                dpg.add_text(node['name'])
                dpg.add_text(node['timestamp'])
                dpg.add_text("Online", color=[0, 255, 0])

    async def refresh_messages(self, messages: List[Dict[str, Any]]) -> None:
        """Refresh the messages table."""
        dpg.delete_item("messages_table", children_only=True, slot=1)
        
        for msg in sorted(messages, key=lambda x: x['timestamp'], reverse=True):
            with dpg.table_row(parent="messages_table"):
                time_str = datetime.fromisoformat(msg['timestamp']).strftime("%H:%M:%S")
                dpg.add_text(time_str)
                dpg.add_text(msg['from'])
                dpg.add_text(msg['to'])
                dpg.add_text(msg['text'])

    async def refresh_device_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh device telemetry display."""
        # Update plots
        times = []
        batteries = []
        voltages = []
        
        for entry in sorted(telemetry, key=lambda x: x['timestamp'])[-100:]:
            time_val = datetime.fromisoformat(entry['timestamp']).timestamp()
            times.append(time_val)
            batteries.append(float(entry['battery']))
            voltages.append(float(entry['voltage']))

        dpg.set_value(self.telemetry_plots["battery"], [times, batteries])
        dpg.set_value(self.telemetry_plots["voltage"], [times, voltages])
        
        # Update current values table
        dpg.delete_item("device_telemetry_table", children_only=True, slot=1)
        for entry in sorted(telemetry, key=lambda x: x['timestamp'])[-DisplayConst.MAX_DEVICE_TELEMETRY:]:
            with dpg.table_row(parent="device_telemetry_table"):
                dpg.add_text(entry['from_id'])
                dpg.add_text(f"{entry['battery']}%")
                dpg.add_text(f"{float(entry['voltage']):.2f}V")
                dpg.add_text(f"{float(entry['channel_util']):.2f}%")

    async def refresh_network_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh network telemetry display."""
        # Update plot
        times = []
        tx_packets = []
        rx_packets = []
        
        for entry in sorted(telemetry, key=lambda x: x['timestamp'])[-100:]:
            time_val = datetime.fromisoformat(entry['timestamp']).timestamp()
            times.append(time_val)
            tx_packets.append(int(entry['packets_tx']))
            rx_packets.append(int(entry['packets_rx']))

        dpg.set_value(self.telemetry_plots["tx"], [times, tx_packets])
        dpg.set_value(self.telemetry_plots["rx"], [times, rx_packets])
        
        # Update status table
        dpg.delete_item("network_status_table", children_only=True, slot=1)
        for entry in sorted(telemetry, key=lambda x: x['timestamp'])[-DisplayConst.MAX_NETWORK_TELEMETRY:]:
            with dpg.table_row(parent="network_status_table"):
                time_str = datetime.fromisoformat(entry['timestamp']).strftime("%H:%M:%S")
                dpg.add_text(time_str)
                dpg.add_text(f"{entry['online_nodes']}")
                dpg.add_text(f"{entry['total_nodes']}")
                dpg.add_text(f"{entry['packets_tx']}")
                dpg.add_text(f"{entry['packets_rx']}")

    async def refresh_environment_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """Refresh environment telemetry display."""
        # Update plots
        times = []
        temps = []
        humidities = []
        
        for entry in sorted(telemetry, key=lambda x: x['timestamp'])[-100:]:
            time_val = datetime.fromisoformat(entry['timestamp']).timestamp()
            times.append(time_val)
            temps.append(float(entry['temperature'].strip('°C')))
            humidities.append(float(entry['humidity'].strip('%')))

        dpg.set_value(self.telemetry_plots["temperature"], [times, temps])
        dpg.set_value(self.telemetry_plots["humidity"], [times, humidities])
        
        # Update current values table
        dpg.delete_item("environment_table", children_only=True, slot=1)
        for entry in sorted(telemetry, key=lambda x: x['timestamp'])[-10:]:
            with dpg.table_row(parent="environment_table"):
                dpg.add_text(entry['from_id'])
                dpg.add_text(entry['temperature'])
                dpg.add_text(entry['humidity'])
                dpg.add_text(entry['pressure'])

    async def show_error(self, message: str) -> None:
        """Display an error message."""
        dpg.set_value(self.error_text, message)
        dpg.configure_item(self.error_text, color=self.error_color)

    async def show_status(self, message: str) -> None:
        """Display a status message."""
        dpg.set_value(self.status_text, message)
        dpg.configure_item(self.status_text, color=self.status_color)