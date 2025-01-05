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

import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from meshtastic_types import (
    Metrics, UserInfo, NodeInfo, TextMessage, 
    MeshtasticPacket, PACKET_TYPES
)

class MeshtasticDataHandler:
    """
    Handles Meshtastic-specific data processing with typed packet handling.
    Works with RedisHandler for storage.
    """
    def __init__(self, redis_handler, logger: Optional[logging.Logger] = None):
        """
        Initialize the data handler.
        
        Args:
            redis_handler: Redis storage handler
            logger: Optional logger instance
        """
        self.redis = redis_handler
        self.logger = logger.getChild(__name__) if logger else logging.getLogger(__name__)

    def _extract_metrics(self, packet: Dict[str, Any]) -> Metrics:
        """
        Extract network metrics from a packet.
        
        Args:
            packet: Raw packet dictionary
            
        Returns:
            Metrics dictionary
        """
        return {
            'rx_time': packet['rxTime'],
            'rx_snr': packet['rxSnr'],
            'rx_rssi': packet['rxRssi'],
            'hop_limit': packet['hopLimit']
        }

    def _process_nodeinfo(self, packet: Dict[str, Any]) -> NodeInfo:
        """
        Process NODEINFO_APP packet.
        
        Args:
            packet: Raw packet dictionary
            
        Returns:
            NodeInfo dictionary
        """
        user_info = packet['decoded']['user']
        return {
            'type': 'nodeinfo',
            'timestamp': datetime.now().isoformat(),
            'from_num': packet['from'],
            'from_id': packet['fromId'],
            'user': {
                'id': user_info['id'],
                'long_name': user_info['longName'],
                'short_name': user_info['shortName'],
                'macaddr': user_info['macaddr'],
                'hw_model': user_info['hwModel'],
                'raw': user_info['raw']
            },
            'metrics': self._extract_metrics(packet),
            'raw': packet['raw']
        }

    def _process_textmessage(self, packet: Dict[str, Any]) -> TextMessage:
        """
        Process TEXT_MESSAGE_APP packet.
        
        Args:
            packet: Raw packet dictionary
            
        Returns:
            TextMessage dictionary
        """
        return {
            'type': 'text',
            'timestamp': datetime.now().isoformat(),
            'from_num': packet['from'],
            'from_id': packet['fromId'],
            'to_num': packet['to'],
            'to_id': packet['toId'],
            'text': packet['decoded']['text'],
            'metrics': self._extract_metrics(packet),
            'raw': packet['raw']
        }

    async def process_packet(self, packet: Dict[str, Any], packet_type: str) -> None:
        """
        Process a Meshtastic packet and store it in Redis.
        
        Args:
            packet: Raw packet dictionary
            packet_type: Type of packet ('text' or 'node')
        """
        try:
            self.logger.debug(f"Processing {packet_type} packet")
            
            # Convert based on packet type
            portnum = packet['decoded']['portnum']
            if portnum == 'NODEINFO_APP':
                processed = self._process_nodeinfo(packet)
                await self.redis.store_node(json.dumps(processed))
                self.logger.info(f"Stored node info for {processed['from_id']}")
                
            elif portnum == 'TEXT_MESSAGE_APP':
                processed = self._process_textmessage(packet)
                await self.redis.store_message(json.dumps(processed))
                self.logger.info(f"Stored text message from {processed['from_id']}")
                
            else:
                self.logger.warning(f"Unknown packet type: {portnum}")
            
        except Exception as e:
            self.logger.error(f"Error processing {packet_type} packet: {e}", exc_info=True)

    async def format_message_for_display(self, json_str: str) -> Optional[Dict[str, str]]:
        """Format a JSON message string for display."""
        try:
            data = json.loads(json_str)
            return {
                'timestamp': data['timestamp'],
                'from': data['from_id'],
                'to': data['to_id'],
                'text': data['text']
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding message JSON: {e}")
            return None

    async def format_node_for_display(self, json_str: str) -> Optional[Dict[str, str]]:
        """Format a JSON node string for display."""
        try:
            data = json.loads(json_str)
            return {
                'timestamp': data['timestamp'],
                'id': data['from_id'],
                'name': data['user']['long_name']
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding node JSON: {e}")
            return None

    async def get_formatted_messages(self, limit: int = -1) -> list:
        """Get formatted messages for display."""
        self.logger.debug("Retrieving formatted messages")
        messages = await self.redis.load_messages(limit)
        self.logger.debug(f"Found {len(messages)} messages")
        
        formatted = []
        for msg in messages:
            fmt_msg = await self.format_message_for_display(msg)
            if fmt_msg:
                formatted.append(fmt_msg)
        
        return formatted

    async def get_formatted_nodes(self, limit: int = -1) -> list:
        """Get formatted nodes for display."""
        self.logger.debug("Retrieving formatted nodes")
        nodes = await self.redis.load_nodes(limit)
        self.logger.debug(f"Found {len(nodes)} nodes")
        
        formatted = []
        for node in nodes:
            fmt_node = await self.format_node_for_display(node)
            if fmt_node:
                formatted.append(fmt_node)
        
        return formatted


