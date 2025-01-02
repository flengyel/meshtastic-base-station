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

import redis.asyncio as redis
import json
from datetime import datetime
from logger import get_logger

# Initialize module-specific logger
logger = get_logger(__name__)

# Redis keys for storing messages and nodes
REDIS_MESSAGES_KEY = "meshtastic:messages"
REDIS_NODES_KEY = "meshtastic:nodes"

class RedisHandler:
    def __init__(self, host="localhost", port=6379):
        self.client = redis.Redis(host=host, port=port, decode_responses=True)
        logger.info(f"Connected to Redis at {host}:{port}")

    async def initialize_broadcast_node(self):
        """
        Initialize the Redis node lookup with a broadcast node and timestamp.
        """
        try:
            broadcast_id = "^all"
            broadcast_name = broadcast_id
            timestamp = self.format_timestamp()

            await self.client.hset(REDIS_NODES_KEY, broadcast_id, broadcast_name)
            await self.client.hset(f"{REDIS_NODES_KEY}:timestamps", broadcast_id, timestamp)
            logger.info(f"Initialized broadcast node: {broadcast_id} -> {broadcast_name}")
        except Exception as e:
            logger.error(f"Failed to initialize broadcast node: {e}", exc_info=True)

    @staticmethod
    def format_timestamp():
        """
        Get the current timestamp in a readable format.
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def save_message(self, station_id, to_id, text_message, timestamp):
        """
        Save a message to Redis.
        """
        try:
            message = json.dumps({
                "timestamp": timestamp,
                "station_id": station_id,
                "to_id": to_id,
                "message": text_message
            })
            await self.client.lpush(REDIS_MESSAGES_KEY, message)
            logger.info(f"Saved message: {message}")
        except Exception as e:
            logger.error(f"Failed to save message: {e}", exc_info=True)

    async def update_node(self, node_id, node_name, timestamp, battery_level=None, position=None):
        """
        Update node information in Redis.
        """
        try:
            async with self.client.pipeline() as pipe:
                await pipe.hset(REDIS_NODES_KEY, node_id, node_name)
                await pipe.hset(f"{REDIS_NODES_KEY}:timestamps", node_id, timestamp)
                if battery_level is not None:
                    await pipe.hset(f"{REDIS_NODES_KEY}:metrics", f"{node_id}:battery", battery_level)
                if position:
                    await pipe.hset(f"{REDIS_NODES_KEY}:position", f"{node_id}:latitude", position.get("latitude", ""))
                    await pipe.hset(f"{REDIS_NODES_KEY}:position", f"{node_id}:longitude", position.get("longitude", ""))
                    await pipe.hset(f"{REDIS_NODES_KEY}:position", f"{node_id}:altitude", position.get("altitude", ""))
                await pipe.execute()
            logger.info(f"Updated node {node_id}: name={node_name}, battery={battery_level}, position={position}")
        except Exception as e:
            logger.error(f"Failed to update node {node_id}: {e}", exc_info=True)

    async def resolve_node_name(self, node_id):
        """
        Resolve a node ID to its name stored in Redis.
        """
        try:
            name = await self.client.hget(REDIS_NODES_KEY, node_id) or node_id
            logger.debug(f"Resolved node name: {node_id} -> {name}")
            return name
        except Exception as e:
            logger.error(f"Failed to resolve node name for {node_id}: {e}", exc_info=True)
            return node_id

    async def load_nodes(self):
        """
        Load all nodes and their timestamps from Redis.
        """
        try:
            nodes = await self.client.hgetall(REDIS_NODES_KEY)
            timestamps = await self.client.hgetall(f"{REDIS_NODES_KEY}:timestamps")
            logger.info(f"Loaded {len(nodes)} nodes from Redis.")
            return nodes, timestamps
        except Exception as e:
            logger.error(f"Failed to load nodes: {e}", exc_info=True)
            return {}, {}

    async def load_messages(self):
        """
        Load all messages from Redis.
        """
        try:
            messages = await self.client.lrange(REDIS_MESSAGES_KEY, 0, -1)
            logger.info(f"Loaded {len(messages)} messages from Redis.")
            return messages
        except Exception as e:
            logger.error(f"Failed to load messages: {e}", exc_info=True)
            return []

    async def update_stored_messages(self, node_id, new_name):
        """
        Update stored messages with a new node name if the node ID has changed.
        """
        try:
            messages = await self.load_messages()
            for i, message in enumerate(messages):
                try:
                    message_dict = json.loads(message)
                    if message_dict["station_id"] == node_id:
                        message_dict["station_id"] = new_name
                        await self.client.lset(REDIS_MESSAGES_KEY, i, json.dumps(message_dict))
                        logger.debug(f"Updated message at index {i}: {message_dict}")
                except json.JSONDecodeError as e:
                    logger.warning(f"Skipping malformed message at index {i}: {message}")
        except Exception as e:
            logger.error(f"Failed to update stored messages for node {node_id}: {e}", exc_info=True)

