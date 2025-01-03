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
from datetime import datetime
from logger import configure_logger
import logging
import json

# Redis keys for storing messages and nodes
REDIS_MESSAGES_KEY = "meshtastic:messages"
REDIS_NODES_KEY = "meshtastic:nodes"

class RedisHandler:
    def __init__(self, host="localhost", port=6379, log_level=logging.INFO, logger=None, debugging=False):
        """
        Initialize the RedisHandler.

        :param host: Redis host. Defaults to 'localhost'.
        :param port: Redis port. Defaults to 6379.
        :param log_level: Logging level for this handler.
        :param logger: Logger instance for configuration. If None, configure a module-specific logger.
        """

        if logger:
            # Use a child logger based on the parent logger
            self.logger = logger.getChild(__name__)
        else:
            # Fallback to a new logger if no parent logger is provided
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(log_level)


        # Debugging: Check logger properties after initialization
        if debugging:
            print(f"Initialized logger: {self.logger.name}")
            print(f"Logger level: {self.logger.level} ({logging.getLevelName(self.logger.level)})")
            print(f"Logger propagate: {self.logger.propagate}")

        # Prevent duplicate handlers
        if logger and not self.logger.hasHandlers():
            for handler in logger.handlers:
                self.logger.addHandler(handler)
            self.logger.setLevel(logger.level)

        # Redis connection
        self.client = redis.Redis(host=host, port=port, decode_responses=True)
        self.logger.redis(f"Connected to Redis at {host}:{port}")


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
            self.logger.redis(f"Initialized broadcast node: {broadcast_id} -> {broadcast_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize broadcast node: {e}", exc_info=True)

    @staticmethod
    def format_timestamp():
        """
        Get the current timestamp in a readable format.
        """
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    async def save_message(self, redis_key, message):
        """
        Save a pre-constructed message to Redis.
        """
        try:
            await self.client.lpush(redis_key, message)
            self.logger.redis(f"Saved message to {redis_key}: {message}")

        except Exception as e:
            self.logger.error(f"Failed to save message to {redis_key}: {e}", exc_info=True)

    async def load_messages(self):
        """
        Load all messages from the Redis list.
        """
        try:
            messages = await self.client.lrange(REDIS_MESSAGES_KEY, 0, -1)
            self.logger.redis(f"Loaded {len(messages)} messages from {REDIS_MESSAGES_KEY}.")

            return messages
        except Exception as e:
            self.logger.error(f"Failed to load messages: {e}", exc_info=True)
            return []


    async def load_nodes(self):
        """
        Load all nodes and their timestamps from Redis.
        """
        try:
            nodes = await self.client.hgetall(REDIS_NODES_KEY)
            timestamps = await self.client.hgetall(f"{REDIS_NODES_KEY}:timestamps")
            self.logger.redis(f"Loaded {len(nodes)} nodes from Redis.")


            return nodes, timestamps
        except Exception as e:
            self.logger.error(f"Failed to load nodes: {e}", exc_info=True)
            return {}, {}

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
            self.logger.redis(f"Updated node {node_id}: name={node_name}, battery={battery_level}, position={position}")
        except Exception as e:
            logger.error(f"Failed to update node {node_id}: {e}", exc_info=True)

    async def initialize_connected_node(self, interface):
        """
        Initialize the Redis node lookup with the station ID and name of the connected node.
        """
        try:
            node_info = interface.getMyNodeInfo()
            node_id_decimal = node_info.get("num", None)
            if node_id_decimal is None:
                self.logger.error("Node ID (num) not found in node info.")
                return

            # Convert the numeric node ID to hexadecimal with Meshtastic format (!hex)
            node_id_hex = f"!{node_id_decimal:08x}"
            user = node_info.get("user", {})
            node_name = user.get("longName", user.get("shortName", node_id_hex))
            timestamp = self.format_timestamp()

            # Save the connected node details and timestamp in Redis
            await self.client.hset(REDIS_NODES_KEY, node_id_hex, node_name)
            await self.client.hset(f"{REDIS_NODES_KEY}:timestamps", node_id_hex, timestamp)
            self.logger.redis(f"[{timestamp}] Connected node: {node_id_hex} -> {node_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize connected node: {e}", exc_info=True)

    async def update_stored_messages(self, node_id, new_name):
        """
        Update stored messages with a new node name if the node ID has changed.
        """
        try:
            messages = await self.load_messages(REDIS_MESSAGES_KEY)
            for i, message in enumerate(messages):
                try:
                    message_dict = json.loads(message)
                    if message_dict["station_id"] == node_id:
                        message_dict["station_id"] = new_name
                        await self.client.lset(REDIS_MESSAGES_KEY, i, json.dumps(message_dict))
                        self.logger.debug(f"Updated message at index {i}: {message_dict}")
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Skipping malformed message at index {i}: {message}")
        except Exception as e:
            self.logger.error(f"Failed to update stored messages for node {node_id}: {e}", exc_info=True)


    async def process_update(self, update):
        """
        Process an update from the queue and perform the appropriate Redis operation.
        """
        try:
            if update["type"] == "message":
                # Save new message
                message = json.dumps({
                    "timestamp": update["timestamp"],
                    "station_id": update["station_id"],
                    "to_id": update["to_id"],
                    "message": update["text_message"]
                })
                await self.save_message(REDIS_MESSAGES_KEY, message)
                self.logger.redis(f"Saved message: {message}")

            elif update["type"] == "node":
                # Update node information
                await self.update_node(
                    node_id=update["node_id"],
                    node_name=update["node_name"],
                    timestamp=update["timestamp"],
                    battery_level=update.get("battery_level"),
                    position=update.get("position")
                )
                self.logger.info(f"Updated node: {update['node_id']} -> {update['node_name']}")

            elif update["type"] == "update_message":
                # Update an existing message by index
                index = update["index"]
                updated_message = update["updated_message"]
                await self.client.lset(REDIS_MESSAGES_KEY, index, updated_message)
                self.logger.redis(f"Updated message at index {index}: {updated_message}")

        except Exception as e:
            self.logger.error(f"Error processing update: {e}", exc_info=True)

