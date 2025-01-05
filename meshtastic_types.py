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

# Union type for all possible packet types
MeshtasticPacket = Union[NodeInfo, TextMessage]

# Dictionary mapping packet types to their TypedDict classes
PACKET_TYPES: Dict[str, type] = {
    'NODEINFO_APP': NodeInfo,
    'TEXT_MESSAGE_APP': TextMessage
}

