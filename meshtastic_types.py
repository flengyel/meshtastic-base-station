# meshtastic_types.py
#
# Copyright (C) 2025 Florian Lengyel WM2D
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from typing import TypedDict, Optional, Union, Literal, Dict
from datetime import datetime

class Metrics(TypedDict):
    """Network metrics for a packet."""
    rx_time: int
    rx_snr: float
    rx_rssi: int
    hop_limit: int

class UserInfo(TypedDict):
    """User information from a node."""
    id: str          # Node ID in !hexnum format
    long_name: str   # Long node name
    short_name: str  # Short node name
    macaddr: str     # MAC address
    hw_model: str    # Hardware model
    raw: str        # Raw protobuf data

class NodeInfo(TypedDict):
    """Node information packet."""
    type: Literal['nodeinfo']
    timestamp: str   # ISO format timestamp
    from_num: int    # Numeric node ID
    from_id: str     # String node ID (!hexnum)
    user: UserInfo   # Node user information
    metrics: Metrics # Network metrics
    raw: str        # Raw packet data

class TextMessage(TypedDict):
    """Text message packet."""
    type: Literal['text']
    timestamp: str
    from_num: int
    from_id: str
    to_num: int
    to_id: str
    text: str
    metrics: Metrics
    raw: str


# meshtastic_types.py
from typing import TypedDict, Optional, Union, Literal, Dict

class Metrics(TypedDict):
    """Network metrics for a packet."""
    rx_time: int
    rx_snr: Optional[float]  # Not all packets have SNR
    rx_rssi: Optional[int]   # Not all packets have RSSI
    hop_limit: int

class DeviceMetrics(TypedDict):
    """Device telemetry metrics."""
    battery_level: int
    voltage: float
    channel_utilization: Optional[float]  # Some packets don't have this
    air_util_tx: float
    uptime_seconds: int

class LocalStats(TypedDict):
    """Local network statistics."""
    uptime_seconds: int
    channel_utilization: float
    air_util_tx: float
    num_packets_tx: int
    num_packets_rx: int
    num_packets_rx_bad: int
    num_online_nodes: int
    num_total_nodes: int
    num_rx_dupe: Optional[int]     # Not always present
    num_tx_relay: Optional[int]     # Not always present
    num_tx_relay_canceled: Optional[int]  # Not always present

class DeviceTelemetry(TypedDict):
    """Device telemetry packet."""
    type: Literal['device_telemetry']
    timestamp: str
    from_num: int
    from_id: str
    device_metrics: DeviceMetrics
    metrics: Metrics
    priority: Optional[str]  # Some packets have priority
    raw: str

class NetworkTelemetry(TypedDict):
    """Network statistics telemetry packet."""
    type: Literal['network_telemetry']
    timestamp: str
    from_num: int
    from_id: str
    local_stats: LocalStats
    metrics: Metrics
    priority: Optional[str]
    raw: str

class UserInfo(TypedDict):
    """User information from a node."""
    id: str
    long_name: str
    short_name: str
    macaddr: str
    hw_model: str
    raw: str

class NodeInfo(TypedDict):
    """Node information packet."""
    type: Literal['nodeinfo']
    timestamp: str
    from_num: int
    from_id: str
    user: UserInfo
    metrics: Metrics
    raw: str

class TextMessage(TypedDict):
    """Text message packet."""
    type: Literal['text']
    timestamp: str
    from_num: int
    from_id: str
    to_num: int
    to_id: str
    text: str
    metrics: Metrics
    raw: str

# Union type for all possible packet types
MeshtasticPacket = Union[NodeInfo, TextMessage, DeviceTelemetry, NetworkTelemetry]

# Dictionary mapping packet types to their TypedDict classes
PACKET_TYPES: Dict[str, type] = {
    'NODEINFO_APP': NodeInfo,
    'TEXT_MESSAGE_APP': TextMessage,
    'TELEMETRY_APP': Union[DeviceTelemetry, NetworkTelemetry]
}


