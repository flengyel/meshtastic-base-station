from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.core.text import LabelBase

import asyncio
import json
import logging
from datetime import datetime
from src.station.utils.constants import RedisConst
from src.station.ui.gui_redis_handler import GuiRedisHandler
from src.station.handlers.data_handler import MeshtasticDataHandler
from src.station.config.base_config import BaseStationConfig

# Load the Kivy UI definition
# we're doing this too many times
# Builder.load_file('src/station/ui/meshtasticbase.kv')


class MeshtasticBaseApp(App):
    def __init__(self, redis_handler: GuiRedisHandler,
                 data_handler: MeshtasticDataHandler,
                 logger=None, config=None):
        super().__init__()
        self.redis_handler = redis_handler
        self.data_handler = data_handler
        self.logger = logger or logging.getLogger(__name__)
        self.config = config
        self._running = False
        self._tasks = []
        self.views = {}

    async def load_initial_data(self):
        """Load and display stored data when GUI starts."""
        try:
            # Load and display nodes
            nodes = await self.data_handler.get_formatted_nodes()
            Clock.schedule_once(lambda dt: self.views['nodes'].update_nodes(nodes))

            # Load and display messages
            messages = await self.data_handler.get_formatted_messages()
            Clock.schedule_once(lambda dt: self.views['messages'].update_messages(messages))

            # Load and display device telemetry
            device_telemetry = await self.data_handler.get_formatted_device_telemetry()
            Clock.schedule_once(lambda dt: self.views['device_telemetry'].update_telemetry(device_telemetry))

            # Load and display network telemetry
            network_telemetry = await self.data_handler.get_formatted_network_telemetry()
            Clock.schedule_once(lambda dt: self.views['network_telemetry'].update_telemetry(network_telemetry))

            # Load and display environment telemetry
            env_telemetry = await self.data_handler.get_formatted_environment_telemetry()
            Clock.schedule_once(lambda dt: self.views['environment_telemetry'].update_telemetry(env_telemetry))

            self.logger.info("Initial data loaded")
        except Exception as e:
            self.logger.error(f"Error loading initial data: {e}")

    def build(self):
        self.logger.debug("Starting build()")
        self.root = BoxLayout(orientation='vertical')
        self.logger.debug("Created root BoxLayout")
    
        tabs = TabbedPanel(do_default_tab=False)
        self.logger.debug("Created TabbedPanel")

        self.views = {
            'messages': MessagesView(),
            'nodes': NodesView(),
            'device_telemetry': DeviceTelemetryView(),
            'network_telemetry': NetworkTelemetryView(),
            'environment_telemetry': EnvironmentTelemetryView()
        }
        self.logger.debug("Created views")

        for name, view in self.views.items():
            tab = TabbedPanelItem(text=name.replace('_', ' ').title())
            self.logger.debug(f"Created tab for {name}")
            tab.add_widget(view)
            self.logger.debug(f"Added view to tab for {name}")
            tabs.add_widget(tab)
            self.logger.debug(f"Added tab to TabbedPanel for {name}")

        self.root.add_widget(tabs)
        self.logger.debug("Added TabbedPanel to root")
        return self.root    
    
    async def process_redis_messages(self):
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
        try:
            # Debugging
            self.logger.debug(f"View keys available for update: {self.views.keys()}")
            
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
            self.logger.error(f"Error updating UI with msg type {msg_type} packet {packet}: {e}")

    def _get_telemetry_type(self, packet):
        telemetry = packet['decoded']['telemetry']
        if 'deviceMetrics' in telemetry:
            return "device"
        elif 'localStats' in telemetry:
            return "network"
        elif 'environmentMetrics' in telemetry:
            return "environment"
        return None

    async def start(self):
        try:
            self._running = True
            self.logger.info("Starting Meshtastic Base Station GUI")

            # We don't need to call build() here anymore as Kivy will do it
            self.logger.debug("Starting Kivy application")
            await self.app_func()
        except Exception as e:
            self.logger.error(f"Error starting GUI: {e}")
            raise
        finally:
            await self.cleanup()

    async def cleanup(self):
        self._running = False
        for task in self._tasks:
            if not task.done():
                task.cancel()
        await self.redis_handler.cleanup()

    async def app_func(self):
        """Main async function."""
        try:
            self._running = True
            self.logger.debug("Starting app_func")
            # Load initial data before starting Kivy
            await self.load_initial_data()
            self.logger.debug("Starting Kivy mainloop")
            self.run()  # Kivy's mainloop
        except Exception as e:
            self.logger.error(f"Error in app_func: {str(e)}", exc_info=True)
            raise
        finally:
            await self.cleanup()

class MessagesView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        # Add a title label
        self.title = Label(
            text='Messages',
            size_hint_y=None,
            height='40dp',
            bold=True
        )
        self.add_widget(self.title)
        
        # Create scrollview with container
        self.scroll = ScrollView(size_hint=(1, 1))
        self.container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing='5dp',
            padding='5dp'
        )
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_messages(self, messages):
        """Update the messages display."""
        self.container.clear_widgets()
        for message in messages:
            text = f"[{message['timestamp']}] {message['from']} -> {message['to']}: {message['text']}"
            label = Label(
                text=text,
                size_hint_y=None,
                height='40dp',
                text_size=(self.width * 0.9, None),
                halign='left'
            )
            self.container.add_widget(label)


class NodesView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.orientation = 'vertical'
        
        # Use system monospace font
        self.monospace_font = 'monospace'  # Most systems have this alias
        
        # Add a title label
        self.title = Label(
            text='Nodes',
            size_hint_y=None,
            height='40dp',
            bold=True,
            halign='left'  # Left-align the title
        )
        self.add_widget(self.title)
        
        # Create scrollview with container
        self.scroll = ScrollView(
            size_hint=(1, 1),
            do_scroll_x=False,  # Vertical scroll only
            do_scroll_y=True,
            bar_width='10dp',
            scroll_type=['bars']
        )
        self.container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing='2dp',
            padding='5dp'
        )
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_nodes(self, nodes):
        """Update the nodes display."""
        try:
            self.container.clear_widgets()
            for node in nodes:
                try:
                    # Format with fixed-width fields for alignment
                    text = (f"[{node.get('timestamp', 'unknown'):25}] "
                           f"{node.get('id', 'unknown'):10} "
                           f"{node.get('name', 'unknown')}")
                    
                    label = Label(
                        text=text,
                        size_hint_y=None,
                        height='25dp',
                        text_size=(self.width - 20, None),  # Full width minus padding
                        halign='left',
                        valign='middle',
                        font_name=self.monospace_font
                    )
                    self.container.add_widget(label)
                except Exception as e:
                    self.logger.error(f"Error formatting node: {e}")
                    continue
        except Exception as e:
            self.logger.error(f"Error updating nodes view: {e}")

class DeviceTelemetryView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        # Add a title label
        self.title = Label(
            text='Device Telemetry',
            size_hint_y=None,
            height='40dp',
            bold=True
        )
        self.add_widget(self.title)
        
        # Create scrollview with container
        self.scroll = ScrollView(size_hint=(1, 1))
        self.container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing='5dp',
            padding='5dp'
        )
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_telemetry(self, telemetry_list):
        """Update the device telemetry display."""
        self.container.clear_widgets()
        for entry in telemetry_list:
            text = f"[{entry['timestamp']}] {entry['from_id']}: battery={entry['battery']}%, voltage={entry['voltage']}V"
            label = Label(
                text=text,
                size_hint_y=None,
                height='40dp',
                text_size=(self.width * 0.9, None),
                halign='left'
            )
            self.container.add_widget(label)

class NetworkTelemetryView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        # Add a title label
        self.title = Label(
            text='Network Telemetry',
            size_hint_y=None,
            height='40dp',
            bold=True
        )
        self.add_widget(self.title)
        
        # Create scrollview with container
        self.scroll = ScrollView(size_hint=(1, 1))
        self.container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing='5dp',
            padding='5dp'
        )
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_telemetry(self, telemetry_list):
        """Update the network telemetry display."""
        self.container.clear_widgets()
        for entry in telemetry_list:
            text = (f"[{entry['timestamp']}] {entry['from_id']}: "
                   f"{entry['online_nodes']}/{entry['total_nodes']} nodes online, "
                   f"TX: {entry['packets_tx']}, RX: {entry['packets_rx']}")
            label = Label(
                text=text,
                size_hint_y=None,
                height='40dp',
                text_size=(self.width * 0.9, None),
                halign='left'
            )
            self.container.add_widget(label)

class EnvironmentTelemetryView(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        
        # Add a title label
        self.title = Label(
            text='Environment Telemetry',
            size_hint_y=None,
            height='40dp',
            bold=True
        )
        self.add_widget(self.title)
        
        # Create scrollview with container
        self.scroll = ScrollView(size_hint=(1, 1))
        self.container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing='5dp',
            padding='5dp'
        )
        self.container.bind(minimum_height=self.container.setter('height'))
        self.scroll.add_widget(self.container)
        self.add_widget(self.scroll)

    def update_telemetry(self, telemetry_list):
        """Update the environment telemetry display."""
        self.container.clear_widgets()
        for entry in telemetry_list:
            text = (f"[{entry['timestamp']}] {entry['from_id']}: "
                   f"temp={entry['temperature']}, "
                   f"humidity={entry['humidity']}, "
                   f"pressure={entry['pressure']}")
            label = Label(
                text=text,
                size_hint_y=None,
                height='40dp',
                text_size=(self.width * 0.9, None),
                halign='left'
            )
            self.container.add_widget(label)