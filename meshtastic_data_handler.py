# meshtastic_data_handler.py
#
# Copyright (C) 2025 Florian Lengyel WM2D
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

from google.protobuf.json_format import MessageToJson
import json
import logging
from datetime import datetime

class MeshtasticDataHandler:
    """
    Handles Meshtastic-specific data processing and JSON conversion.
    Works with RedisHandler for storage.
    """
    def __init__(self, redis_handler, logger=None):
        self.redis = redis_handler
        self.logger = logger.getChild(__name__) if logger else logging.getLogger(__name__)

    async def process_packet(self, packet, packet_type: str):
        """
        Process a Meshtastic packet and store it in Redis.
        
        :param packet: Meshtastic protobuf packet
        :param packet_type: Type of packet ('text', 'node', etc)
        """
        try:
            json_data = MessageToJson(packet)
            
            if packet_type == 'text':
                await self.redis.store_message(json_data)
            elif packet_type == 'node':
                await self.redis.store_node(json_data)
            
            self.logger.debug(f"Processed {packet_type} packet: {json_data[:100]}...")
            
        except Exception as e:
            self.logger.error(f"Error processing {packet_type} packet: {e}", exc_info=True)

    async def format_message_for_display(self, json_str: str):
        """
        Format a JSON message string for display.
        
        :param json_str: JSON string to format
        :return: Formatted message dictionary or None on error
        """
        try:
            data = json.loads(json_str)
            return {
                'timestamp': data.get('timestamp', datetime.now().isoformat()),
                'from': data.get('fromId', 'Unknown'),
                'to': data.get('toId', 'Unknown'),
                'text': data.get('decoded', {}).get('text', '')
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding message JSON: {e}")
            return None

    async def format_node_for_display(self, json_str: str):
        """
        Format a JSON node string for display.
        
        :param json_str: JSON string to format
        :return: Formatted node dictionary or None on error
        """
        try:
            data = json.loads(json_str)
            return {
                'timestamp': data.get('timestamp', datetime.now().isoformat()),
                'id': data.get('fromId', 'Unknown'),
                'name': data.get('decoded', {}).get('user', {}).get('longName', 'Unknown')
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding node JSON: {e}")
            return None

    async def get_formatted_messages(self, limit: int = -1):
        """
        Get formatted messages for display.
        
        :param limit: Maximum number of messages to return (-1 for all)
        :return: List of formatted message dictionaries
        """
        messages = await self.redis.load_messages(limit)
        formatted = []
        for msg in messages:
            fmt_msg = await self.format_message_for_display(msg)
            if fmt_msg:
                formatted.append(fmt_msg)
        return formatted

    async def get_formatted_nodes(self, limit: int = -1):
        """
        Get formatted nodes for display.
        
        :param limit: Maximum number of nodes to return (-1 for all)
        :return: List of formatted node dictionaries
        """
        nodes = await self.redis.load_nodes(limit)
        formatted = []
        for node in nodes:
            fmt_node = await self.format_node_for_display(node)
            if fmt_node:
                formatted.append(fmt_node)
        return formatted


