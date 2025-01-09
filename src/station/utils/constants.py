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
    QUEUE_TIMEOUT = 1.0        # Timeout for queue operations in seconds
    HEARTBEAT_INTERVAL = 900.0 # 15 minutes between heartbeats
    ERROR_SLEEP = 1.0         # Sleep after error to prevent tight loops
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = 6379
    DEFAULT_DB = 0

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
    PACKET_LEVEL = 15  # Custom log levels
    DATA_LEVEL = 16
    REDIS_LEVEL = 17

# Data Retention
class RetentionConst:
    """Data retention constants."""
    DEFAULT_DAYS = 30           # Default retention period in days
    MAX_QUEUE_SIZE = 10000      # Maximum queue size before oldest entries removed
    CLEANUP_INTERVAL = 3600     # Hourly cleanup in seconds