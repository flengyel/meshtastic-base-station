# src/station/handlers/meshtastic_handler.py

import asyncio
import logging
from pubsub import pub
from typing import Optional
import time
from datetime import datetime

from meshtastic.serial_interface import SerialInterface
from src.station.types.meshtastic_types import NodeInfo
from src.station.utils.validation import validate_typed_dict
from src.station.utils.constants import MeshtasticConst

class MeshtasticHandler:
    """
    Bridge between Meshtastic's sync callbacks and async processing.
    Only responsible for queuing messages for async processing.
    The interface isn't used directly, but is required for Meshtastic's callbacks.
    """

    def __init__(self, message_queue: asyncio.Queue, interface: SerialInterface, logger: Optional[logging.Logger] = None):
        self.message_queue = message_queue
        self.logger = logger or logging.getLogger(__name__)
        
        pub.subscribe(self.on_text_message, MeshtasticConst.TOPIC_RECEIVE_TEXT)
        pub.subscribe(self.on_node_message, MeshtasticConst.TOPIC_RECEIVE_USER)
        pub.subscribe(self.on_telemetry_message, MeshtasticConst.TOPIC_RECEIVE_TELEMETRY)
        
        self.logger.debug("Meshtastic handler initialized")

    def on_text_message(self, packet, interface):
        """Queue text message for async processing."""
        self.logger.packet(f"on_text_message: {packet}")
        try:
            self.message_queue.put_nowait({
                "type": "text",
                "packet": packet
            })
        except Exception as e:
            self.logger.error(f"Error queueing text message: {e}", exc_info=True)

    def on_node_message(self, packet, interface):
        """Queue node message for async processing."""
        self.logger.packet(f"on_node_message: {packet}")
        try:
            self.message_queue.put_nowait({
                "type": "node",
                "packet": packet
            })
        except Exception as e:
            self.logger.error(f"Error queueing node message: {e}", exc_info=True)

    def on_telemetry_message(self, packet, interface):
        """Queue telemetry message for async processing."""
        self.logger.packet(f"on_telemetry_message: {packet}")
        try:
            self.message_queue.put_nowait({
                "type": "telemetry",
                "packet": packet
            })
        except Exception as e:
            self.logger.error(f"Error queueing telemetry message: {e}", exc_info=True)
    
    def cleanup(self):
        """Unsubscribe from Meshtastic API topics."""
        pub.unsubscribe(self.on_text_message, MeshtasticConst.TOPIC_RECEIVE_TEXT)
        pub.unsubscribe(self.on_node_message, MeshtasticConst.TOPIC_RECEIVE_USER)
        pub.unsubscribe(self.on_telemetry_message, MeshtasticConst.TOPIC_RECEIVE_TELEMETRY)

    def initialize_connected_node(self) -> None:
        """Initialize connected node information."""
        try:
            # Get node info from interface
            node_info = self.interface.getMyNodeInfo()
            if not node_info:
                self.logger.error("Failed to get connected node info")
                return

            node_num = node_info.get("num")
            if node_num is None:
                self.logger.error("Node number not found in node info")
                return

            # Format node ID in Meshtastic format (!hex)
            node_id = f"!{node_num:08x}"
            
            # Get user info
            user = node_info.get("user", {})
            node_name = user.get("longName") or user.get("shortName") or node_id

            # Create NodeInfo structure
            connected_node = {
                "type": "nodeinfo",
                "timestamp": datetime.now().isoformat(),
                "from_num": node_num,
                "from_id": node_id,
                "user": {
                    "id": node_id,
                    "long_name": node_name,
                    "short_name": user.get("shortName", node_name),
                    "macaddr": user.get("macaddr", ""),
                    "hw_model": user.get("hwModel", "unknown"),
                    "raw": str(user)
                },
                "metrics": {
                    "rx_time": int(time.time()),
                    "rx_snr": None,
                    "rx_rssi": None,
                    "hop_limit": 3
                },
                "raw": str(node_info)
            }

            # Validate the node info structure
            validate_typed_dict(connected_node, NodeInfo)

            # Create packet for processing
            packet = {
                'from': node_num,
                'fromId': node_id,
                'decoded': {
                    'portnum': 'NODEINFO_APP',
                    'user': connected_node['user']  # Use our validated user info
                },
                'rxTime': connected_node['metrics']['rx_time'],
                'hopLimit': connected_node['metrics']['hop_limit'],
                'raw': connected_node['raw']
            }

            # Queue the node info for processing
            self.message_queue.put_nowait({
                "type": "node",
                "packet": packet
            })
            
            self.logger.info(f"Initialized connected node: {node_id} ({node_name})")

        except Exception as e:
            self.logger.error(f"Failed to initialize connected node: {e}")
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("Error details:", exc_info=True)