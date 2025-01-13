# constants.py
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

"""
System-wide constants for the Meshtastic Base Station.

This module contains all constant definitions used across the system,
organized by functional area.
"""

# Redis Configuration
class RedisConst:
    """Redis-related constants."""
    DISPATCH_SLEEP = 0.01      # Sleep when queue is empty to prevent CPU hogging
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 6379
    DEFAULT_DB = 0
    DEFAULT_DECODE_RESPONSES = True
    
    # Redis key names
    KEY_MESSAGES = "meshtastic:messages"
    KEY_NODES = "meshtastic:nodes"
    KEY_TELEMETRY_DEVICE = "meshtastic:telemetry:device"
    KEY_TELEMETRY_NETWORK = "meshtastic:telemetry:network"
    KEY_TELEMETRY_ENVIRONMENT = "meshtastic:telemetry:environment"
    
    # Redis channels for pubsub
    CHANNEL_TEXT = "meshtastic.text"
    CHANNEL_NODE = "meshtastic.node"
    CHANNEL_TELEMETRY_DEVICE = "meshtastic.telemetry.device"
    CHANNEL_TELEMETRY_NETWORK = "meshtastic.telemetry.network"
    CHANNEL_TELEMETRY_ENVIRONMENT = "meshtastic.telemetry.environment"
    CHANNEL_PROCESSED = "meshtastic.processed"  # For GUI updates

# Meshtaastic Handler Configuration
class MeshtasticConst:
    """Meshtastic-related constants."""
    TOPIC_RECEIVE_TEXT = "meshtastic.receive.text" # Text message
    TOPIC_RECEIVE_USER = "meshtastic.receive.user" # Node message
    TOPIC_RECEIVE_TELEMETRY = "meshtastic.receive.telemetry" # Telemetry message

# Device Configuration
class DeviceConst:
    """Device-related constants."""
    DEFAULT_PORT_LINUX = "/dev/ttyACM0"
    DEFAULT_PORT_WINDOWS = "COM1"
    DEFAULT_PORT_MAC = "/dev/tty.usbmodem1"
    DEFAULT_BAUD_RATE = 115200
    DEFAULT_TIMEOUT = 1.0

# Display Limits
class DisplayConst:
    """Display and formatting constants."""
    MAX_DEVICE_TELEMETRY = 10    # Number of device telemetry entries to show
    MAX_NETWORK_TELEMETRY = 5    # Number of network status entries to show
    MAX_DEBUG_STRING = 200       # Maximum length for debug output

# Logging Configuration
class LoggingConst:
    """Logging-related constants."""
    DEFAULT_LEVEL = "INFO"
    DEFAULT_FILE = "meshtastic.log"
    CONSOLE_FORMAT = "%(levelname)s:%(name)s:%(message)s"
    FILE_FORMAT = "%(asctime)s %(levelname)s:%(name)s:%(message)s"
    DEFAULT_USE_THRESHOLD = False
    DEFAULT_DEBUGGING = False
    PACKET_LEVEL = 15  # Custom log levels
    DATA_LEVEL = 16
    REDIS_LEVEL = 17

# Data Retention
class RetentionConst:
    """Data retention constants."""
    DEFAULT_DAYS = 30           # Default retention period in days
    MAX_QUEUE_SIZE = 10000      # Maximum queue size before oldest entries removed
    CLEANUP_INTERVAL = 3600     # Hourly cleanup in seconds(meshtastic-base-station) 

# Base Station Configuration
class BaseStationConst:
    """Base Station configuration constants."""
    DEFAULT_DATA_RETENTION_DAYS = RetentionConst.DEFAULT_DAYS
    DEFAULT_ENVIRONMENT = "development"
    CONFIG_PATHS = [
        'config.yaml',                               # Current directory
        '.config/meshtastic/config.yaml',            # User config
        '/etc/meshtastic/config.yaml',              # System config
    ]
