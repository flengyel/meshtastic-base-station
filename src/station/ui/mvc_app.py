from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.lang import Builder
import asyncio
import json
from typing import Optional
import logging
from src.station.utils.constants import RedisConst
from src.station.handlers.redis_handler import RedisHandler
from src.station.handlers.data_handler import MeshtasticDataHandler
from src.station.config.base_config import BaseStationConfig

# Load the Kivy UI definition
Builder.load_file('src/station/ui/meshtasticbase.kv')

class MeshtasticBaseApp(App):
    def __init__(self, redis_handler: RedisHandler,
                 data_handler: MeshtasticDataHandler,
                 logger: Optional[logging.Logger] = None,
                 config: Optional[BaseStationConfig] = None):
        super().__init__()
        self.redis_handler = redis_handler
        self.data_handler = data_handler
        self.logger = logger or logging.getLogger(__name__)
        self.config = config
        self._running = False
        self._tasks = []
        self.views = {}

    def build(self):
        """Build the UI with tabbed views."""
        self.root = BoxLayout(orientation='vertical')
        tabs = TabbedPanel()

        # Initialize all views
        self.views = {
            'messages': MessagesView(),
            'nodes': NodesView(),
            'device_telemetry': DeviceTelemetryView(),
            'network_telemetry': NetworkTelemetryView(),
            'environment_telemetry': EnvironmentTelemetryView()
        }

        # Create tabs for each view
        for name, view in self.views.items():
            tab = TabbedPanelItem(text=name.replace('_', ' ').title())
            tab.add_widget(view)
            tabs.add_widget(tab)

        self.root.add_widget(tabs)
        return self.root

    async def process_redis_messages(self):
        """Process messages from Redis pubsub."""
        try:
            channels = [
                RedisConst.CHANNEL_TEXT,
                RedisConst.CHANNEL_NODE,
                RedisConst.CHANNEL_TELEMETRY_DEVICE,
                RedisConst.CHANNEL_TELEMETRY_NETWORK,
                RedisConst.CHANNEL_TELEMETRY_ENVIRONMENT
            ]
            await self.redis_handler.subscribe_gui(channels)
            
            async for message in self.redis_handler.listen_gui():
                if not self._running:
                    break
                    
                if message['type'] == 'message':
                    data = json.loads(message['data'])
                    Clock.schedule_once(lambda dt: self.update_ui(data))
                    
        except asyncio.CancelledError:
            self.logger.info("Redis message processor shutting down")
            raise
        except Exception as e:
            self.logger.error(f"Error processing Redis messages: {e}")
            raise

    def update_ui(self, data):
        """Update UI based on message type."""
        try:
            msg_type = data["type"]
            packet = data["packet"]

            if msg_type == "text":
                self.views['messages'].update_messages([packet])
            elif msg_type == "node":
                self.views['nodes'].update_nodes([packet])
            elif msg_type == "telemetry":
                telemetry_type = self._get_telemetry_type(packet)
                if telemetry_type:
                    self.views[f'{telemetry_type}_telemetry'].update_telemetry(packet)

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
            while self._running:
                await asyncio.sleep(1/60)  # 60 FPS
                Clock.tick()
        except Exception as e:
            self.logger.error(f"Error in app_func: {e}")
            raise
        finally:
            await self.cleanup()

    async def start(self):
        """Start the GUI application."""
        try:
            self._running = True
            self.logger.info("Starting Meshtastic Base Station GUI")
            
            # Start Redis message processor
            redis_task = asyncio.create_task(self.process_redis_messages())
            self._tasks.append(redis_task)
            
            # Run the Kivy application
            await self.app_func()
            
        except Exception as e:
            self.logger.error(f"Error starting GUI: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Clean up resources."""
        self._running = False
        for task in self._tasks:
            if not task.done():
                task.cancel()
        await self.redis_handler.cleanup()

class MessagesView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.scroll = ScrollView(size_hint=(1, None), size=(self.width, self.height))
        self.container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_messages(self, messages):
        self.container.clear_widgets()
        for message in messages:
            self.container.add_widget(
                Label(text=f"[{message['timestamp']}] {message['from']} -> {message['to']}: {message['text']}", 
                      size_hint_y=None, height=40)
            )

class NodesView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.scroll = ScrollView(size_hint=(1, None), size=(self.width, self.height))
        self.container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_nodes(self, nodes):
        self.container.clear_widgets()
        for node in nodes:
            self.container.add_widget(
                Label(text=f"[{node['timestamp']}] Node {node['id']}: {node['name']}", 
                      size_hint_y=None, height=40)
            )

class DeviceTelemetryView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.scroll = ScrollView(size_hint=(1, None), size=(self.width, self.height))
        self.container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_telemetry(self, packet):
        metrics = packet['device_metrics']
        self.container.clear_widgets()
        self.container.add_widget(
            Label(text=f"Battery: {metrics['battery_level']}%, Voltage: {metrics['voltage']}V",
                  size_hint_y=None, height=40)
        )

class NetworkTelemetryView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.scroll = ScrollView(size_hint=(1, None), size=(self.width, self.height))
        self.container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_telemetry(self, packet):
        stats = packet['local_stats']
        self.container.clear_widgets()
        self.container.add_widget(
            Label(text=f"Nodes: {stats['num_online_nodes']}/{stats['num_total_nodes']}, "
                      f"Packets TX: {stats['num_packets_tx']}, RX: {stats['num_packets_rx']}",
                  size_hint_y=None, height=40)
        )

class EnvironmentTelemetryView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.scroll = ScrollView(size_hint=(1, None), size=(self.width, self.height))
        self.container = BoxLayout(orientation='vertical', size_hint_y=None)
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_telemetry(self, packet):
        metrics = packet['environment_metrics']
        self.container.clear_widgets()
        self.container.add_widget(
            Label(text=f"Temp: {metrics['temperature']}°C, "
                      f"Humidity: {metrics['relative_humidity']}%, "
                      f"Pressure: {metrics['barometric_pressure']}hPa",
                  size_hint_y=None, height=40)
        )