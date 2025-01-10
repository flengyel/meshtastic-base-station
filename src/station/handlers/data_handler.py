# data_handler.py
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

from datetime import datetime
import json
import logging
from typing import Optional, Dict, Any 
from ..types.meshtastic_types import (Metrics, NodeInfo, TextMessage,
       DeviceTelemetry, NetworkTelemetry, EnvironmentTelemetry
)
from ..utils.validation import validate_typed_dict

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

        # Dispatch table for packet types
        self.packet_handlers = {
            'NODEINFO_APP': self._handle_nodeinfo,
            'TEXT_MESSAGE_APP': self._handle_text,
            'TELEMETRY_APP': self._handle_telemetry
        }

    async def process_packet(self, packet: Dict[str, Any], packet_type: str) -> None:
        """Dispatch packet to appropriate handler based on portnum."""
        try:
            self.logger.debug(f"Processing {packet_type} packet")
            portnum = packet['decoded']['portnum']
            self.logger.debug(f"Portnum: {portnum}") # Claude and Copilot agreed on this line   
            handler = self.packet_handlers.get(portnum)
            self.logger.debug(f"Handler found: {handler is not None} for {portnum}")
            
            if handler:
                await handler(packet)
            else:
                self.logger.warning(f"Unknown packet type: {portnum}")

        except Exception as e:
            self.logger.error(f"Error processing {packet_type} packet: {e}", exc_info=True)

    async def _handle_nodeinfo(self, packet: Dict[str, Any]) -> None:
        """Handle NODEINFO_APP packets."""
        processed = self._process_nodeinfo(packet)
        await self.redis.store_node(json.dumps(processed))
        self.logger.data(f"Stored node info for {processed['from_id']}")
        self.logger.info(
            f"[{processed['timestamp']}] Node {processed['from_id']}: {processed['user']['long_name']}"
        )

    async def _handle_text(self, packet: Dict[str, Any]) -> None:
        """Handle TEXT_MESSAGE_APP packets."""
        processed = self._process_textmessage(packet)
        await self.redis.store_message(json.dumps(processed))
        self.logger.data(f"Stored text message from {processed['from_id']}")
        self.logger.info(
            f"[{processed['timestamp']}] {processed['from_id']} -> {processed['to_id']}: {processed['text']}"
        )

    async def _handle_telemetry(self, packet: Dict[str, Any]) -> None:
        """Handle TELEMETRY_APP packets."""
        try:
            telemetry = packet['decoded']['telemetry']
            if 'deviceMetrics' in telemetry:
                await self._handle_device_telemetry(packet)
            elif 'localStats' in telemetry:
                await self._handle_network_telemetry(packet)
            elif 'environmentMetrics' in telemetry:
                await self._handle_environment_telemetry(packet)
            else:
                self.logger.warning(f"Unknown telemetry type in packet: {packet}")
        except Exception as e:
            self.logger.error(f"Error handling telemetry packet: {e}", exc_info=True)

    async def _handle_environment_telemetry(self, packet: Dict[str, Any]) -> None:
       """Handle environment telemetry packets."""
       processed = self._process_environment_telemetry(packet)
       await self.redis.store_environment_telemetry(json.dumps(processed))
       metrics = processed['environment_metrics']
       self.logger.data(
           f"[{processed['timestamp']}] Environment telemetry from {processed['from_id']}: "
           f"temp={metrics['temperature']:.1f}°C, "
           f"humidity={metrics['relative_humidity']:.1f}%, "
           f"pressure={metrics['barometric_pressure']:.1f}hPa"
       )
       self.logger.info(
           f"[{processed['timestamp']}] Environment from {processed['from_id']}: "
           f"temp={metrics['temperature']:.1f}°C,humidity={metrics['relative_humidity']:.1f}%"
        )

    async def _handle_device_telemetry(self, packet: Dict[str, Any]) -> None:
        """Handle device telemetry packets."""
        processed = self._process_device_telemetry(packet)
        await self.redis.store_device_telemetry(json.dumps(processed))
        self.logger.data(
            f"[{processed['timestamp']}] Device telemetry from {processed['from_id']}: "
            f"battery={processed['device_metrics']['battery_level']}%, "
            f"voltage={processed['device_metrics']['voltage']:.2f}V"
        )

    async def _handle_network_telemetry(self, packet: Dict[str, Any]) -> None:
        """Handle network telemetry packets."""
        processed = self._process_network_telemetry(packet)
        await self.redis.store_network_telemetry(json.dumps(processed))
        stats = processed['local_stats']
        self.logger.data(
            f"[{processed['timestamp']}] Network telemetry from {processed['from_id']}: "
            f"online={stats['num_online_nodes']}/{stats['num_total_nodes']} nodes, "
            f"tx={stats['num_packets_tx']}, rx={stats['num_packets_rx']}"
        )


    def _extract_metrics(self, packet: Dict[str, Any]) -> Metrics:
        """
        Extract network metrics from a packet.

        Args:
            packet: Raw packet dictionary

        Returns:
            Metrics dictionary with optional fields
        """
        return {
            'rx_time': int(packet['rxTime']),
            'rx_snr': float(packet.get('rxSnr', 0)),     # Optional
            'rx_rssi': int(packet.get('rxRssi', 0)),     # Optional
            'hop_limit': int(packet.get('hopLimit', 3))  # Default to 3 if not present
        }

    def _process_nodeinfo(self, packet: Dict[str, Any]) -> NodeInfo:
        """Process NODEINFO_APP packet."""
        try:
            user_info = dict(packet['decoded']['user'])
            node_info: NodeInfo = {
                'type': 'nodeinfo',
                'timestamp': datetime.now().isoformat(),
                'from_num': int(packet['from']),
                'from_id': str(packet['fromId']),
                'user': {
                    'id': str(user_info['id']),
                    'long_name': str(user_info['longName']),
                    'short_name': str(user_info['shortName']),
                    'macaddr': str(user_info['macaddr']),
                    'hw_model': str(user_info['hwModel']),
                    'raw': str(user_info['raw'])
                },
                'metrics': self._extract_metrics(packet),
                'raw': str(packet['raw'])
            }
            validate_typed_dict(node_info, NodeInfo)
            return node_info
        except Exception as e:
            self.logger.error(f"Error processing node info: {e}", exc_info=True)
            raise

    def _process_textmessage(self, packet: Dict[str, Any]) -> TextMessage:
        """Process TEXT_MESSAGE_APP packet."""
        try:
            text_message: TextMessage = {
                'type': 'text',
                'timestamp': datetime.now().isoformat(),
                'from_num': int(packet['from']),
                'from_id': str(packet['fromId']),
                'to_num': int(packet['to']),
                'to_id': str(packet['toId']),
                'text': str(packet['decoded']['text']),
                'metrics': self._extract_metrics(packet),
                'raw': str(packet['raw'])
            }
            validate_typed_dict(text_message, TextMessage)
            return text_message
        except Exception as e:
            self.logger.error(f"Error processing text message: {e}", exc_info=True)
            raise

    def _process_device_telemetry(self, packet: Dict[str, Any]) -> DeviceTelemetry:
        """
        Process device telemetry packet.

        Args:
            packet: Raw packet dictionary

        Returns:
            DeviceTelemetry dictionary
        """
        try:
            telemetry = packet['decoded']['telemetry']
            device_metrics = telemetry['deviceMetrics']
            device_telemetry: DeviceTelemetry = {
                'type': 'device_telemetry',
                'timestamp': datetime.now().isoformat(),
                'from_num': int(packet['from']),
                'from_id': str(packet['fromId']),
                'device_metrics': {
                    'battery_level': int(device_metrics['batteryLevel']),
                    'voltage': float(device_metrics['voltage']),
                    'channel_utilization': float(device_metrics.get('channelUtilization', 0.0)),
                    'air_util_tx': float(device_metrics['airUtilTx']),
                    'uptime_seconds': int(device_metrics['uptimeSeconds'])
                },
                'metrics': self._extract_metrics(packet),
                'priority': packet.get('priority'),
                'raw': str(packet['raw'])
            }
            validate_typed_dict(device_telemetry, DeviceTelemetry)
            return device_telemetry
        except Exception as e:
            self.logger.error(f"Error processing device telemetry: {e}", exc_info=True)
            raise

    def _process_network_telemetry(self, packet: Dict[str, Any]) -> NetworkTelemetry:
        """
        Process network telemetry packet.
    
        Args:
            packet: Raw packet dictionary
    
        Returns:
            NetworkTelemetry dictionary
        """
        try:
            telemetry = packet['decoded']['telemetry']
            local_stats = telemetry['localStats']
        
            network_telemetry: NetworkTelemetry = {
                'type': 'network_telemetry',
                'timestamp': datetime.now().isoformat(),
                'from_num': int(packet['from']),
                'from_id': str(packet['fromId']),
                'local_stats': {
                    'uptime_seconds': int(local_stats.get('uptimeSeconds', 0)),
                    'channel_utilization': float(local_stats.get('channelUtilization', 0.0)),
                    'air_util_tx': float(local_stats.get('airUtilTx', 0.0)),
                    'num_packets_tx': int(local_stats.get('numPacketsTx', 0)),
                    'num_packets_rx': int(local_stats.get('numPacketsRx', 0)),
                    'num_packets_rx_bad': int(local_stats.get('numPacketsRxBad', 0)),
                    'num_online_nodes': int(local_stats.get('numOnlineNodes', 0)),
                    'num_total_nodes': int(local_stats.get('numTotalNodes', 0)),
                    'num_rx_dupe': local_stats.get('numRxDupe'),
                    'num_tx_relay': local_stats.get('numTxRelay'),
                    'num_tx_relay_canceled': local_stats.get('numTxRelayCanceled')
                },
                'metrics': self._extract_metrics(packet),
                'priority': packet.get('priority'),
                'raw': str(packet['raw'])
            }
        
            validate_typed_dict(network_telemetry, NetworkTelemetry)
            return network_telemetry
        except Exception as e:
            self.logger.error(f"Error processing network telemetry: {e}")
            raise
       
    def _process_environment_telemetry(self, packet: Dict[str, Any]) -> EnvironmentTelemetry:
        """Process environment telemetry packet."""
        telemetry = packet['decoded']['telemetry']
        env_metrics = telemetry['environmentMetrics']

        environment_telemetry: EnvironmentTelemetry = {
            'type': 'environment_telemetry',
            'timestamp': datetime.now().isoformat(),
            'from_num': int(packet['from']),
            'from_id': str(packet['fromId']),
            'environment_metrics': {
                'temperature': float(env_metrics.get('temperature', 0.0)),
                'relative_humidity': float(env_metrics.get('relativeHumidity', 0.0)),
                'barometric_pressure': float(env_metrics.get('barometricPressure', 0.0)),
                'gas_resistance': float(env_metrics.get('gasResistance', 0.0)),
                'iaq': int(env_metrics.get('iaq', 0))
            },
            'metrics': self._extract_metrics(packet),
            'priority': packet.get('priority'),
            'raw': str(packet['raw'])
        }
        validate_typed_dict(environment_telemetry, EnvironmentTelemetry)
        return environment_telemetry

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

    async def format_environment_telemetry_for_display(self, json_str: str) -> Optional[Dict[str, str]]:
        """Format environment telemetry for display."""
        try:
            data = json.loads(json_str)
            metrics = data['environment_metrics']
            return {
                'timestamp': data['timestamp'],
                'from_id': data['from_id'],
                'temperature': f"{metrics['temperature']:.1f}°C",
                'humidity': f"{metrics['relative_humidity']:.1f}%",
                'pressure': f"{metrics['barometric_pressure']:.1f}hPa"
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding environment telemetry JSON: {e}")
            return None

    async def get_formatted_environment_telemetry(self, limit: int = -1) -> list:
        """Get formatted environment telemetry for display."""
        self.logger.debug("Retrieving formatted environment telemetry")
        telemetry = await self.redis.load_environment_telemetry(limit)
        self.logger.debug(f"Found {len(telemetry)} environment telemetry records")
    
        formatted = []
        for entry in telemetry:
            fmt_entry = await self.format_environment_telemetry_for_display(entry)
            if fmt_entry:
                formatted.append(fmt_entry)
    
        return formatted

    async def format_device_telemetry_for_display(self, json_str: str) -> Optional[Dict[str, str]]:
        """Format device telemetry for display."""
        try:
            data = json.loads(json_str)
            metrics = data['device_metrics']
            return {
                'timestamp': data['timestamp'],
                'from_id': data['from_id'],
                'battery': str(metrics['battery_level']),
                'voltage': f"{metrics['voltage']:.2f}",
                'channel_util': f"{metrics.get('channel_utilization', 0):.2f}",
                'air_util': f"{metrics['air_util_tx']:.2f}"
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding device telemetry JSON: {e}")
            return None

    async def get_formatted_device_telemetry(self, limit: int = -1) -> list:
        """Get formatted device telemetry for display."""
        self.logger.debug("Retrieving formatted device telemetry")
        telemetry = await self.redis.load_device_telemetry(limit)
        self.logger.debug(f"Found {len(telemetry)} device telemetry records")
        
        formatted = []
        for entry in telemetry:
            fmt_entry = await self.format_device_telemetry_for_display(entry)
            if fmt_entry:
                formatted.append(fmt_entry)
        return formatted

    async def format_network_telemetry_for_display(self, json_str: str) -> Optional[Dict[str, str]]:
        """Format network telemetry for display."""
        try:
            data = json.loads(json_str)
            stats = data['local_stats']
            return {
                'timestamp': data['timestamp'],
                'from_id': data['from_id'],
                'online_nodes': str(stats['num_online_nodes']),
                'total_nodes': str(stats['num_total_nodes']),
                'packets_tx': str(stats['num_packets_tx']),
                'packets_rx': str(stats['num_packets_rx']),
                'packets_rx_bad': str(stats['num_packets_rx_bad'])
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decoding network telemetry JSON: {e}")
            return None

    async def get_formatted_network_telemetry(self, limit: int = -1) -> list:
        """Get formatted network telemetry for display."""
        self.logger.debug("Retrieving formatted network telemetry")
        telemetry = await self.redis.load_network_telemetry(limit)
        self.logger.debug(f"Found {len(telemetry)} network telemetry records")
        
        formatted = []
        for entry in telemetry:
            fmt_entry = await self.format_network_telemetry_for_display(entry)
            if fmt_entry:
                formatted.append(fmt_entry)
        return formatted


