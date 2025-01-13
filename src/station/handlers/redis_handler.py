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
from datetime import datetime, timedelta
from src.station.utils.constants import RedisConst
from src.station.handlers.data_handler import MeshtasticDataHandler

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

    def set_data_handler(self, data_handler: MeshtasticDataHandler) -> None:
        self.data_handler = data_handler

    async def message_publisher(self):
        """Process messages from queue and store in Redis."""
        if self.data_handler is None:
            self.logger.critical("Meshtastic Data handler not set")
            raise ValueError("Meshtastic Data handler not set")
        
        try:
            self.logger.info("Message publisher started")
            while True:
                try:
                    if self.message_queue.qsize() > 0:
                        message = await self.message_queue.get()
                        msg_type = message["type"]
                        packet = message["packet"]

                        # Let data_handler process and store the packet
                        try:
                            await self.data_handler.process_packet(packet, msg_type)
                        except Exception as e:
                            self.logger.error(f"Error processing {msg_type} packet: {e}")
                            continue

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
        """Load data from Redis list with validation."""
        try:
            data = await self.client.lrange(key, start, end)
            # Filter out None or empty strings
            return [item for item in data if item]
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

# cleanup methods

    async def cleanup_data(self, days: int = 30):
        """Remove data older than specified days."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_time.isoformat()
        
            for key in self.keys.values():
                try:
                    # Get all items
                    items = await self.load(key)
                    cleaned = []
                    removed = 0
                    malformed = 0
                
                    for item in items:
                        if not item:  # Skip None or empty strings
                            removed += 1
                            continue
                        
                        try:
                            data = json.loads(item)
                            if not isinstance(data, dict):
                                malformed += 1
                                continue
                            
                            timestamp = data.get('timestamp')
                            if not timestamp:
                                malformed += 1
                                continue
                            
                            if timestamp >= cutoff_str:
                                cleaned.append(item)
                            else:
                                removed += 1
                            
                        except (json.JSONDecodeError, TypeError, ValueError):
                            malformed += 1
                            continue
                
                    # Delete the key and add back cleaned items
                    await self.client.delete(key)
                    if cleaned:
                        await self.client.rpush(key, *cleaned)
                
                    self.logger.info(
                        f"Cleaned {key}: removed {removed} old items, "
                        f"found {malformed} malformed items, kept {len(cleaned)} items"
                    )
                
                except Exception as e:
                    self.logger.error(f"Error cleaning {key}: {str(e)}")
                    continue
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    async def cleanup_corrupted_data(self):
        """Remove any entries that can't be parsed as JSON or lack required fields."""
        try:
            for key in self.keys.values():
                try:
                    items = await self.load(key)
                    valid_items = []
                    corrupted = 0
                    missing_fields = 0
                
                    required_fields = {
                        'meshtastic:messages': ['timestamp', 'from_id', 'to_id', 'text'],
                        'meshtastic:nodes': ['timestamp', 'from_id', 'user'],
                        'meshtastic:telemetry:device': ['timestamp', 'from_id', 'device_metrics'],
                        'meshtastic:telemetry:network': ['timestamp', 'from_id', 'local_stats'],
                        'meshtastic:telemetry:environment': ['timestamp', 'from_id', 'environment_metrics']
                    }
                
                    for item in items:
                        if not item:  # Skip None or empty strings
                            corrupted += 1
                            continue
                        
                        try:
                            data = json.loads(item)
                            if not isinstance(data, dict):
                                corrupted += 1
                                continue
                            
                            # Check required fields for this key type
                            fields = required_fields.get(key, ['timestamp'])  # Default to just timestamp
                            if all(field in data for field in fields):
                                valid_items.append(item)
                            else:
                                missing_fields += 1
                            
                        except (json.JSONDecodeError, TypeError):
                            corrupted += 1
                            continue
                
                    # Replace with valid items
                    await self.client.delete(key)
                    if valid_items:
                        await self.client.rpush(key, *valid_items)
                    
                    self.logger.info(
                        f"Cleaned corrupted data from {key}: "
                        f"found {corrupted} corrupted items, "
                        f"{missing_fields} items with missing fields, "
                        f"kept {len(valid_items)} valid items"
                    )
                
                except Exception as e:
                    self.logger.error(f"Error cleaning corrupted data from {key}: {str(e)}")
                    continue
                
        except Exception as e:
            self.logger.error(f"Error during corrupted data cleanup: {str(e)}")