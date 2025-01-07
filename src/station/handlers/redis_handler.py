# redis_handler.py
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

# redis_handler.py

import redis.asyncio as redis
import logging
from ..utils.logger import configure_logger

class RedisHandler:
    """
    Minimal Redis handler that stores raw JSON data without making assumptions about structure.
    """

    def __init__(self, host="localhost", port=6379, logger=None):
        """Initialize Redis connection and logger."""
        self.logger = logger.getChild(__name__) if logger else logging.getLogger(__name__)
        try:
            self.client = redis.Redis(host=host, port=port, decode_responses=True)
            self.logger.debug("Redis handler initialized")
        except Exception as e:
            self.logger.error(f"Failed to create Redis client: {e}", exc_info=True)
            raise
        
        # Define Redis keys
        self.keys = {
            'messages': 'meshtastic:messages',
            'nodes': 'meshtastic:nodes',
            'device_telemetry': 'meshtastic:telemetry:device',
            'network_telemetry': 'meshtastic:telemetry:network',
            'environment_telemetry': 'meshtastic:telemetry:environment'
        }
        self.logger.debug(f"Initialized Redis handler with keys: {self.keys}")

    async def verify_connection(self):
        """Verify Redis connection is working."""
        try:
            result = await self.client.ping()
            self.logger.debug(f"Redis connection test: {result}")
            return result
        except Exception as e:
            self.logger.error(f"Redis connection test failed: {e}", exc_info=True)
            raise


    async def store(self, key: str, data: str):
        """
        Store raw data string in Redis list.
        :param key: Redis key to store under
        :param data: Raw data string (expected to be JSON)
        """
        try:
            self.logger.debug(f"Attempting to store {len(data)} bytes in key: {key}")
            result = await self.client.lpush(key, data)
            self.logger.debug(f"Redis lpush result: {result}")
            self.logger.redis(f"Stored data in {key}")
            
            # Verify storage
            length = await self.client.llen(key)
            self.logger.debug(f"Current length of {key}: {length}")
            
        except Exception as e:
            self.logger.error(f"Failed to store data in {key}: {e}", exc_info=True)
            raise

    async def load(self, key: str, start: int = 0, end: int = -1):
        """
        Load raw data from Redis list.
        :param key: Redis key to load from
        :param start: Start index
        :param end: End index (-1 for all)
        :return: List of raw data strings
        """
        try:
            data = await self.client.lrange(key, start, end)
            self.logger.redis(f"Loaded {len(data)} items from {key}")
            return data
        except Exception as e:
            self.logger.error(f"Failed to load data from {key}: {e}")
            return []

    async def store_message(self, json_message: str):
        """Store a raw JSON message."""
        self.logger.debug(f"Storing message: {json_message[:200]}...")  # First 200 chars
        await self.store(self.keys['messages'], json_message)

    async def store_node(self, json_node: str):
        """Store a raw JSON node update."""
        self.logger.debug(f"Storing node: {json_node[:200]}...")  # First 200 chars
        await self.store(self.keys['nodes'], json_node)

    async def load_messages(self, limit: int = -1):
        """Load raw JSON messages."""
        return await self.load(self.keys['messages'], 0, limit)

    async def load_nodes(self, limit: int = -1):
        """Load raw JSON node data."""
        return await self.load(self.keys['nodes'], 0, limit)

    async def store_device_telemetry(self, json_telemetry: str):
        """Store device telemetry data."""
        self.logger.debug(f"Storing device telemetry: {json_telemetry[:200]}...")
        await self.store(self.keys['device_telemetry'], json_telemetry)

    async def store_network_telemetry(self, json_telemetry: str):
        """Store network telemetry data."""
        self.logger.debug(f"Storing network telemetry: {json_telemetry[:200]}...")
        await self.store(self.keys['network_telemetry'], json_telemetry)

    async def load_device_telemetry(self, limit: int = -1):
        """Load device telemetry data."""
        return await self.load(self.keys['device_telemetry'], 0, limit)

    async def load_network_telemetry(self, limit: int = -1):
        """Load network telemetry data."""
        return await self.load(self.keys['network_telemetry'], 0, limit)

    async def store_environment_telemetry(self, json_telemetry: str):
        """Store environment telemetry data."""
        self.logger.debug(f"Storing environment telemetry: {json_telemetry[:200]}...")
        await self.store(self.keys['environment_telemetry'], json_telemetry)

    async def load_environment_telemetry(self, limit: int = -1):
        """Load environment telemetry data."""
        return await self.load(self.keys['environment_telemetry'], 0, limit)

    async def close(self):
        """Close Redis connection."""
        await self.client.close()


