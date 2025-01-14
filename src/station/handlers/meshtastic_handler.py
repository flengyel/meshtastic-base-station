# src/station/handlers/meshtastic_handler.py

import asyncio
import logging
from pubsub import pub
from typing import Optional
import time
from datetime import datetime
import json

from meshtastic.serial_interface import SerialInterface
from src.station.types.meshtastic_types import NodeInfo
from src.station.utils.validation import validate_typed_dict
from src.station.utils.constants import MeshtasticConst
from src.station.handlers.redis_handler import RedisHandler

class MeshtasticHandler:
    """
    Bridge between Meshtastic's sync callbacks and async processing.
    Only responsible for queuing messages for async processing.
    The SerialInterface.interface isn't used directly, but is required for Meshtastic's callbacks.
    """

    def __init__(self, 
                 redis_handler : RedisHandler, 
                 interface: SerialInterface, 
                 logger: Optional[logging.Logger] = None):
        self.redis_handler = redis_handler
        self.message_queue = redis_handler.message_queue
        self.interface = interface
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

    async def initialize_connected_node(self) -> None:
        """Initialize connected node information."""
        try:
            # Get node info from interface
            node_info = self.interface.getMyNodeInfo()
            self.logger.debug(f"Raw node info: {node_info}")
            if not node_info:
                self.logger.error("Failed to get connected node info")
                return

            node_num = node_info.get("num")
            if node_num is None:
                self.logger.error("Node number not found in node info")
                return

            # Format node ID in Meshtastic format (!hex)
            node_id = f"!{node_num:08x}"
            
            # Check if our node already exists
            existing_nodes = await self.redis_handler.load_nodes()
            for node in existing_nodes:
                try:
                    node_data = json.loads(node)
                    if node_data.get('from_id') == node_id:
                        self.logger.info(f"Connected node already exists: {node_id}")
                        return
                except json.JSONDecodeError:
                    continue  # Skip malformed entries
            
            # Get user info and create packet only if node doesn't exist
            user = node_info.get("user", {})
            node_name = user.get("longName") or user.get("shortName") or node_id

            # Create packet for processing
            packet = {
                'from': node_num,
                'fromId': node_id,
                'decoded': {
                    'portnum': 'NODEINFO_APP',
                    'user': {
                        'id': node_id,
                        'longName': node_name,
                        'shortName': user.get("shortName", node_name),
                        'macaddr': user.get("macaddr", ""),
                        'hwModel': user.get("hwModel", "unknown"),
                        'raw': str(user)
                    }
                },
                'rxTime': int(time.time()),
                'hopLimit': 3,
                'raw': str(node_info)
            }

            # Queue the node info
            self.message_queue.put_nowait({
                "type": "node",
                "packet": packet
            })
        
            self.logger.info(f"Initialized connected node: {node_id} ({node_name})")

        except Exception as e:
            self.logger.error(f"Failed to initialize connected node: {e}")
            if self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("Error details:", exc_info=True)