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

import asyncio
import redis.asyncio as aioredis
import redis.exceptions
from typing import Optional
import logging
import json
from src.station.utils.constants import RedisConst
from src.station.handlers.data_handler import DataHandler

class RedisHandler:
    def __init__(self, host : str = RedisConst.DEFAULT_HOST, port: int = RedisConst.DEFAULT_PORT, logger: Optional[logging.Logger] = None):
        """Initialize Redis connection and logger."""
        self.logger = logger.getChild(__name__) if logger else logging.getLogger(__name__)
        self.message_queue = asyncio.Queue()
        self.data_handler = None  # to be set by a method by delayed assignment
        
        try:
            self.client = aioredis.Redis(host=host, port=port, decode_responses=True)            
            self.logger.debug("Redis handler initialized")
        except Exception as e:
            self.logger.error(f"Failed to create Redis client: {e}", exc_info=True)
            raise
        
        # Define Redis keys for data storage
        self.keys = {
            'messages': RedisConst.KEY_MESSAGES,
            'nodes': RedisConst.KEY_NODES,
            'device_telemetry': RedisConst.KEY_TELEMETRY_DEVICE,
            'network_telemetry': RedisConst.KEY_TELEMETRY_NETWORK,
            'environment_telemetry': RedisConst.KEY_TELEMETRY_ENVIRONMENT
        }

    def set_data_handler(self, data_handler: DataHandler) -> None:
        self.data_handler = data_handler

    async def message_publisher(self):
        """Process messages from queue and store in Redis."""
        if self.data_handler is None:
            self.logger.critical("Data handler not set")
            raise ValueError("Data handler not set") 
        try:
            self.logger.info("Message publisher started")
            while True:
                try:
                    if self.message_queue.qsize() > 0:
                        message = await self.message_queue.get()
                        msg_type = message["type"]
                        packet = message["packet"]

                        # Store based on message type using async Redis calls
                        if msg_type == "text":
                            await self.store_message(json.dumps(packet))
                        elif msg_type == "node":
                            await self.store_node(json.dumps(packet))
                        elif msg_type == "telemetry":
                            telemetry = packet['decoded'].get('telemetry', {})
                            if 'deviceMetrics' in telemetry:
                                await self.store_device_telemetry(json.dumps(packet))
                            elif 'localStats' in telemetry:
                                await self.store_network_telemetry(json.dumps(packet))
                            elif 'environmentMetrics' in telemetry:
                                await self.store_environment_telemetry(json.dumps(packet))

                        self.message_queue.task_done()
                    else:
                        await asyncio.sleep(RedisConst.DISPATCH_SLEEP)

                except Exception as e:
                    self.logger.error(f"Error processing message: {e}", exc_info=True)
                    continue
                    
        except asyncio.CancelledError:
            self.logger.info("Message publisher shutting down")
            raise

    async def verify_connection(self) -> bool:
        """Verify Redis connection is working."""
        try:
            result = await self.client.ping()
            if result:
                self.logger.info("Redis connection verified")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Redis connection error: {e}")
            return False

    async def store(self, key: str, data: str):
        """Store data in Redis list."""
        try:
            await self.client.lpush(key, data)
            self.logger.debug(f"Stored data in {key}")
        except Exception as e:
            self.logger.error(f"Failed to store data in {key}: {e}")
            raise

    async def load(self, key: str, start: int = 0, end: int = -1):
        """Load data from Redis list."""
        try:
            return await self.client.lrange(key, start, end)
        except Exception as e:
            self.logger.error(f"Failed to load data from {key}: {e}")
            return []

    # Storage methods for different types
    async def store_message(self, json_message: str):
        await self.store(self.keys['messages'], json_message)

    async def store_node(self, json_node: str):
        await self.store(self.keys['nodes'], json_node)

    async def store_device_telemetry(self, json_telemetry: str):
        await self.store(self.keys['device_telemetry'], json_telemetry)

    async def store_network_telemetry(self, json_telemetry: str):
        await self.store(self.keys['network_telemetry'], json_telemetry)

    async def store_environment_telemetry(self, json_telemetry: str):
        await self.store(self.keys['environment_telemetry'], json_telemetry)

    # Load methods for different types
    async def load_messages(self, limit: int = -1):
        return await self.load(self.keys['messages'], 0, limit)

    async def load_nodes(self, limit: int = -1):
        return await self.load(self.keys['nodes'], 0, limit)

    async def load_device_telemetry(self, limit: int = -1):
        return await self.load(self.keys['device_telemetry'], 0, limit)

    async def load_network_telemetry(self, limit: int = -1):
        return await self.load(self.keys['network_telemetry'], 0, limit)

    async def load_environment_telemetry(self, limit: int = -1):
        return await self.load(self.keys['environment_telemetry'], 0, limit)

    async def close(self):
        """Close Redis connection."""
        await self.client.close()