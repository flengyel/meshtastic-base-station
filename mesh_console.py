# mesh_console.py
#
# Copyright (C) 2024 Florian Lengyel WM2D
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
from pubsub import pub
from meshtastic.serial_interface import SerialInterface
import logging
from datetime import datetime
import redis
import json

# Redis keys for storing messages and nodes
REDIS_MESSAGES_KEY = "meshtastic:messages"
REDIS_NODES_KEY = "meshtastic:nodes"

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Adjust this to logging.DEBUG to see detailed logs
    format="%(asctime)s %(levelname)s: %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to console
        logging.FileHandler("meshtastic.log", mode="a")  # Log to a file
    ]
)

# Initialize asyncio queue for Redis updates
redis_update_queue = asyncio.Queue()

# Initialize Redis connection
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


def initialize_broadcast_node():
    """
    Initialize the Redis node lookup with a broadcast node and timestamp.
    """
    broadcast_id = "^all"
    broadcast_name = "Broadcast"
    timestamp = format_timestamp()

    # Save broadcast node details and timestamp in Redis
    redis_client.hset(REDIS_NODES_KEY, broadcast_id, broadcast_name)
    redis_client.hset(f"{REDIS_NODES_KEY}:timestamps", broadcast_id, timestamp)

    print(f"[{timestamp}] Initialized broadcast node: {broadcast_id} -> {broadcast_name}")

async def update_stored_messages_with_node_name(node_id, node_name):
    """
    Update messages in Redis to replace station_id with the corresponding node name,
    but only if the node_name for the node_id has changed.
    """
    # Get the current node name in Redis
    current_name = redis_client.hget(REDIS_NODES_KEY, node_id)

    # Exit early if the node name has not changed
    if current_name == node_name:
        logging.debug(f"No change for node {node_id}: {node_name}. Update skipped.")
        return

    # Update messages if the node name has changed
    logging.info(f"Updating messages for node {node_id}: {current_name} -> {node_name}")
    messages = redis_client.lrange(REDIS_MESSAGES_KEY, 0, -1)
    for i, message in enumerate(messages):
        try:
            message_dict = json.loads(message)  # Parse JSON string
            if message_dict["station_id"] == node_id:
                # Update the station_id to the new node name
                message_dict["station_id"] = node_name

                # Enqueue the updated message for Redis update
                await redis_update_queue.put({
                    "type": "update_message",
                    "index": i,  # Index of the message in the Redis list
                    "updated_message": json.dumps(message_dict)
                })
                logging.debug(f"Enqueued updated message: {message_dict}")
        except json.JSONDecodeError:
            logging.warning(f"Skipping malformed message: {message}")

def format_timestamp():
    """
    Get the current timestamp in a readable format.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def process_node_update(node_id, new_name, timestamp):
    """
    Update the node name in Redis if it has changed and update associated messages.
    """
    # Check the current node name in Redis
    current_name = redis_client.hget(REDIS_NODES_KEY, node_id)

    # If the name hasn't changed, exit early
    if current_name == new_name:
        logging.debug(f"No change for node {node_id}: {new_name}. Update skipped.")
        return

    # Update Redis with the new node name and timestamp
    logging.info(f"Updating node {node_id}: {current_name} -> {new_name}")
    redis_client.hset(REDIS_NODES_KEY, node_id, new_name)
    redis_client.hset(f"{REDIS_NODES_KEY}:timestamps", node_id, timestamp)

    # Update stored messages with the new node name
    messages = redis_client.lrange(REDIS_MESSAGES_KEY, 0, -1)
    for i, message in enumerate(messages):
        try:
            message_dict = json.loads(message)  # Parse JSON string
            if message_dict["station_id"] == node_id:
                # Update the station_id to the new node name
                message_dict["station_id"] = new_name
                redis_client.lset(REDIS_MESSAGES_KEY, i, json.dumps(message_dict))
                logging.debug(f"Updated message: {message_dict}")
        except json.JSONDecodeError:
            logging.warning(f"Skipping malformed message: {message}")


async def redis_writer():
    """
    Asynchronous coroutine to process Redis updates from the queue.
    """
    while True:
        update = await redis_update_queue.get()  # Wait for an update
        try:
            if update["type"] == "message":
                # Save message to Redis
                message = json.dumps({
                    "timestamp": update["timestamp"],
                    "station_id": update["station_id"],
                    "to_id": update["to_id"],
                    "message": update["text_message"]
                })
                redis_client.lpush(REDIS_MESSAGES_KEY, message)

            elif update["type"] == "node":
                # Process node updates
                process_node_update(
                    node_id=update["node_id"],
                    new_name=update["node_name"],
                    timestamp=update["timestamp"]
                )

            elif update["type"] == "update_message":
                # Update an existing message in Redis
                redis_client.lset(REDIS_MESSAGES_KEY, update["index"], update["updated_message"])
        except Exception as e:
            logging.error(f"Error writing to Redis: {e}")
        finally:
            redis_update_queue.task_done()  # Mark the task as done


def load_previous_data():
    """
    Load and display previous messages and nodes from Redis.
    """
    print("\n--- Previously Saved Nodes ---")
    nodes = redis_client.hgetall(REDIS_NODES_KEY)
    timestamps = redis_client.hgetall(f"{REDIS_NODES_KEY}:timestamps")

    sorted_nodes = sorted(
        nodes.items(), key=lambda x: timestamps.get(x[0], "[No timestamp]")
    )
    for node_id, node_name in sorted_nodes:
        timestamp = timestamps.get(node_id, "[No timestamp]")
        print(f"[{timestamp}] Node {node_id}: {node_name}")

    print("\n--- Previously Saved Messages ---")
    messages = redis_client.lrange(REDIS_MESSAGES_KEY, 0, -1)
    parsed_messages = [
        json.loads(msg) for msg in messages if json.loads(msg).get("timestamp")
    ]
    sorted_messages = sorted(parsed_messages, key=lambda m: m["timestamp"])
    for message in sorted_messages:
        station_id = message["station_id"]
        to_id = message.get("to_id", "^all")
        sender_name = nodes.get(station_id, station_id)
        recipient_name = nodes.get(to_id, to_id)
        print(f"[{message['timestamp']}] {sender_name} -> {recipient_name}: {message['message']}")


async def cancellable_task():
    """
    A cancellable infinite loop task.
    """
    try:
        while True:
            await asyncio.sleep(0.01) # Small delay to avoid CPU hogging
    except asyncio.CancelledError:
        print("\nExiting...")

def on_text_message(packet, interface):
    """
    Callback to process received text messages and enqueue them for Redis updates.
    """
    try:
        # Extract 'fromId' and 'from'
        station_id = packet.get("fromId")  # No default value to catch missing IDs
        from_field = packet.get("from")  # Numeric 'from' field if 'fromId' is missing

        # Derive 'fromId' from 'from' if necessary
        if station_id is None and from_field is not None:
            station_id = f"!{from_field:08x}"  # Convert 'from' to hex and prepend '!'
        elif station_id is None:
            logging.error(f"Missing 'fromId' and 'from' in packet: {packet}")
            station_id = "[Unknown ID]"

        # Extract 'toId' or default to 'Broadcast'
        to_id = packet.get("toId", "^all")

        # Decode the message text
        text_message = packet.get("decoded", {}).get("text", "[No text]")

        # Lookup the sender and recipient node names
        sender_name = redis_client.hget(REDIS_NODES_KEY, station_id) or station_id
        recipient_name = redis_client.hget(REDIS_NODES_KEY, to_id) or to_id

        # Enqueue the message for Redis update
        redis_update_queue.put_nowait({
            "type": "message",
            "station_id": station_id,
            "to_id": to_id,
            "text_message": text_message,
            "timestamp": format_timestamp()
        })

        # Print message with sender and recipient
        print(f"[{format_timestamp()}] {sender_name} -> {recipient_name}: {text_message}")
    except Exception as e:
        logging.error(f"Error processing text message: {e}", exc_info=True)

def on_node_message(packet, interface):
    """
    Callback to process received node messages and enqueue them for Redis updates.
    """
    try:
        node_id = packet.get("fromId", "[Unknown ID]")
        node_info = packet.get("decoded", {}).get("user", {})
        long_name = node_info.get("longName", "")
        short_name = node_info.get("shortName", "")

        # Determine the node name
        node_name = long_name or short_name or node_id

        # Enqueue the node update for Redis
        redis_update_queue.put_nowait({
            "type": "node",
            "node_id": node_id,
            "node_name": node_name,
            "timestamp": format_timestamp()
        })


        # Print the node announcement
        print(f"[{format_timestamp()}] Node {node_id}: {node_name}")
    except Exception as e:
        logging.error(f"Error processing node message: {e}")

def initialize_connected_node(interface):
    """
    Initialize the Redis node lookup with the station ID and name of the connected node.
    """
    try:
        # Query the connected node info
        node_info = interface.getMyNodeInfo()
        node_id_decimal = node_info.get("num", None)
        if node_id_decimal is None:
            logging.error("Node ID (num) not found in node info.")
            return

        # Convert the numeric node ID to hexadecimal with Meshtastic format (!hex)
        node_id_hex = f"!{node_id_decimal:08x}"
        user = node_info.get("user", {})
        node_name = user.get("longName", user.get("shortName", node_id_hex))
        timestamp = format_timestamp()

        # Save the connected node details and timestamp in Redis
        redis_client.hset(REDIS_NODES_KEY, node_id_hex, node_name)
        redis_client.hset(f"{REDIS_NODES_KEY}:timestamps", node_id_hex, timestamp)

        # Shorter message format
        print(f"[{timestamp}] Connected node: {node_id_hex} -> {node_name}")
    except Exception as e:
        logging.error(f"Failed to initialize connected node: {e}")


async def main():
    """
    Main function to set up the Meshtastic listener for text and node messages.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    logging.getLogger("meshtastic").setLevel(logging.WARNING)  # Suppress non-essential logs

    print("Listening for messages... Press Ctrl+C to exit.")

    # Initialize broadcast node
    initialize_broadcast_node()

    # Load and display previous data
    load_previous_data()

    device_path = '/dev/ttyACM0'  # Adjust to your actual device path
    interface = SerialInterface(device_path)

    initialize_connected_node(interface)

    # Subscribe to message topics using pubsub
    pub.subscribe(on_text_message, "meshtastic.receive.text")
    pub.subscribe(on_node_message, "meshtastic.receive.user")

    print("\nSubscribed to text and user message handlers.")

    tasks = [
              asyncio.create_task(cancellable_task()),
              asyncio.create_task(redis_writer()) 
            ]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        interface.close()
        print("Interface closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated.")

