# src/station/ui/mvc_app.py

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.clock import Clock
from kivy.lang import Builder
import asyncio
from functools import partial
from typing import Optional
from src.station.handlers.redis_handler import RedisHandler
from src.station.handlers.data_handler import MeshtasticDataHandler
from src.station.config.base_config import BaseStationConfig
from src.station.utils.constants import RedisConst
import logging

from kivy.lang import Builder
Builder.load_file('src/station/ui/meshtasticbase.kv')

class MessagesView(BoxLayout):
    """Displays and manages text messages."""
    def update_messages(self, packet):
        pass  # Will implement message display logic

class NodesView(BoxLayout):
    """Displays node information and status."""
    def update_nodes(self, packet):
        pass  # Will implement node status updates

class DeviceTelemetryView(BoxLayout):
    """Shows device-specific telemetry (battery, voltage, etc)."""
    def update_telemetry(self, packet):
        pass  # Will implement device telemetry visualization

class NetworkTelemetryView(BoxLayout):
    """Displays network statistics and performance metrics."""
    def update_telemetry(self, packet):
        pass  # Will implement network stats display

class EnvironmentTelemetryView(BoxLayout):
    """Shows environmental sensor data."""
    def update_telemetry(self, packet):
        pass  # Will implement environmental data display

class MeshtasticBaseApp(App):
    def __init__(self, redis_handler: RedisHandler,
                 data_handler: MeshtasticDataHandler,
                 logger: Optional[logging.Logger] = None,
                 config: Optional[BaseStationConfig] = None):
        super().__init__()
        self.redis_handler = redis_handler
        self.data_handler = data_handler
        self.logger = logger
        self.config = config
        self._running = False
        self._tasks = []
        self.views = {}

    def build(self):
        """Build the UI with tabbed views."""
        self.root = BoxLayout(orientation='vertical')
        tabs = TabbedPanel()

        # Initialize all views
        self.views['messages'] = MessagesView()
        self.views['nodes'] = NodesView()
        self.views['device_telemetry'] = DeviceTelemetryView()
        self.views['network_telemetry'] = NetworkTelemetryView()
        self.views['environment_telemetry'] = EnvironmentTelemetryView()

        # Create tabs for each view
        for name, view in self.views.items():
            tab = TabbedPanelItem(text=name.replace('_', ' ').title())
            tab.add_widget(view)
            tabs.add_widget(tab)

        self.root.add_widget(tabs)
        return self.root

    async def process_messages(self):
        """Process messages from redis_queue."""
        try:
            while self._running:
                try:
                    if self.redis_handler.redis_queue.qsize() > 0:
                        update = await self.redis_handler.redis_queue.get()
                        await self.data_handler.process_packet(
                            update["packet"],
                            update["type"]
                        )
                        Clock.schedule_once(
                            partial(self.update_ui, update)
                        )
                        self.redis_handler.redis_queue.task_done()
                    else:
                        await asyncio.sleep(RedisConst.DISPATCH_SLEEP)
                except Exception as e:
                    self.logger.error(f"Error processing messages: {e}")
                    self.redis_handler.redis_queue.task_done()
        except asyncio.CancelledError:
            self.logger.info("Message processor shutting down")
            raise

    def update_ui(self, update, dt):
        """Route updates to appropriate views."""
        try:
            update_type = update["type"]
            packet = update["packet"]
            
            if update_type == "text":
                self.views['messages'].update_messages(packet)
            elif update_type == "node":
                self.views['nodes'].update_nodes(packet)
            elif update_type == "telemetry":
                telemetry_type = self._get_telemetry_type(packet)
                if telemetry_type == "device":
                    self.views['device_telemetry'].update_telemetry(packet)
                elif telemetry_type == "network":
                    self.views['network_telemetry'].update_telemetry(packet)
                elif telemetry_type == "environment":
                    self.views['environment_telemetry'].update_telemetry(packet)
                
        except Exception as e:
            self.logger.error(f"Error updating UI: {e}")

    def _get_telemetry_type(self, packet):
        """Determine telemetry type from packet."""
        telemetry = packet['decoded']['telemetry']
        if 'deviceMetrics' in telemetry:
            return "device"
        elif 'localStats' in telemetry:
            return "network"
        elif 'environmentMetrics' in telemetry:
            return "environment"
        return None

    async def app_func(self):
        """Main async function."""
        try:
            self._running = True
            self.logger.info("Starting Meshtastic Base Station GUI")
            
            message_task = asyncio.create_task(self.process_messages())
            self._tasks.append(message_task)
            
            while self._running:
                await asyncio.sleep(1/60)
                Clock.tick()
                
        except Exception as e:
            self.logger.error(f"Error in app_func: {e}", exc_info=True)
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self._running = False
        for task in self._tasks:
            if not task.done():
                task.cancel()

    async def start(self):
        """Start GUI and dispatcher."""
        try:
            self._running = True
            self.logger.info("Starting Meshtastic Base Station GUI")
            dispatcher_task = asyncio.create_task(self.redis_handler.redis_dispatcher(self.data_handler))
            self._tasks.append(dispatcher_task)
            return await self.app_func()
        except Exception as e:
            self.logger.error(f"GUI startup error: {e}")
            raise