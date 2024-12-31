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
import redis.asyncio as redis  # Use asynchronous Redis
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

async def initialize_broadcast_node():
    """
    Initialize the Redis node lookup with a broadcast node and timestamp.
    """
    broadcast_id = "^all"
    broadcast_name = "Broadcast"
    timestamp = format_timestamp()

    # Save broadcast node details and timestamp in Redis
    await redis_client.hset(REDIS_NODES_KEY, broadcast_id, broadcast_name)
    await redis_client.hset(f"{REDIS_NODES_KEY}:timestamps", broadcast_id, timestamp)

    print(f"[{timestamp}] Initialized broadcast node: {broadcast_id} -> {broadcast_name}")

def format_timestamp():
    """
    Get the current timestamp in a readable format.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

async def process_node_update(update):
    """
    Asynchronous function to process node updates in Redis.
    """
    node_id = update["node_id"]
    new_name = update["node_name"]
    timestamp = update["timestamp"]

    # Extract additional fields
    battery_level = update.get("battery_level", "")  # Default to empty string
    position = update.get("position", {})
    latitude = position.get("latitude", "")
    longitude = position.get("longitude", "")
    altitude = position.get("altitude", "")

    try:
        # Fetch current data from Redis
        current_name = await redis_client.hget(REDIS_NODES_KEY, node_id)
        current_battery = await redis_client.hget(f"{REDIS_NODES_KEY}:metrics", f"{node_id}:battery")
        current_latitude = await redis_client.hget(f"{REDIS_NODES_KEY}:position", f"{node_id}:latitude")
        current_longitude = await redis_client.hget(f"{REDIS_NODES_KEY}:position", f"{node_id}:longitude")
        current_altitude = await redis_client.hget(f"{REDIS_NODES_KEY}:position", f"{node_id}:altitude")

        # Use Redis pipelines to batch updates
        async with redis_client.pipeline() as pipe:
            # Update name and timestamp if changed
            if current_name != new_name:
                logging.info(f"Updating node {node_id}: {current_name} -> {new_name}")
                pipe.hset(REDIS_NODES_KEY, node_id, new_name)
                pipe.hset(f"{REDIS_NODES_KEY}:timestamps", node_id, timestamp)

            # Update battery level if changed
            if current_battery != battery_level:
                pipe.hset(f"{REDIS_NODES_KEY}:metrics", f"{node_id}:battery", battery_level)

            # Update position fields if changed
            if current_latitude != latitude:
                pipe.hset(f"{REDIS_NODES_KEY}:position", f"{node_id}:latitude", latitude)
            if current_longitude != longitude:
                pipe.hset(f"{REDIS_NODES_KEY}:position", f"{node_id}:longitude", longitude)
            if current_altitude != altitude:
                pipe.hset(f"{REDIS_NODES_KEY}:position", f"{node_id}:altitude", altitude)

            # Execute all updates in the pipeline
            await pipe.execute()

        # Update stored messages with the new node name if it has changed
        if current_name != new_name:
            messages = await redis_client.lrange(REDIS_MESSAGES_KEY, 0, -1)
            for i, message in enumerate(messages):
                try:
                    message_dict = json.loads(message)  # Parse JSON string
                    if message_dict["station_id"] == node_id:
                        # Update the station_id to the new node name
                        message_dict["station_id"] = new_name
                        await redis_client.lset(REDIS_MESSAGES_KEY, i, json.dumps(message_dict))
                        logging.debug(f"Updated message: {message_dict}")
                except json.JSONDecodeError:
                    logging.warning(f"Skipping malformed message: {message}")

    except Exception as e:
        logging.error(f"Error processing node update for {node_id}: {e}")

async def redis_writer():
    """
    Asynchronous coroutine to process Redis updates from the queue.
    """
    while True:
        update = await redis_update_queue.get()  # Wait for an update
        try:
            if update["type"] == "message":
                # Resolve names for station_id and to_id
                station_id = update["station_id"]
                to_id = update["to_id"]

                sender_name = await redis_client.hget(REDIS_NODES_KEY, station_id) or station_id
                recipient_name = await redis_client.hget(REDIS_NODES_KEY, to_id) or to_id

                # Save message to Redis with resolved names
                message = json.dumps({
                    "timestamp": update["timestamp"],
                    "station_id": sender_name,  # Use resolved name
                    "to_id": recipient_name,  # Use resolved name
                    "message": update["text_message"]
                })
                await redis_client.lpush(REDIS_MESSAGES_KEY, message)

                # Print message with resolved names
                print(f"[{update['timestamp']}] {sender_name} -> {recipient_name}: {update['text_message']}")

            elif update["type"] == "node":
                # Process node updates
                await process_node_update(update)

            elif update["type"] == "update_message":
                # Update an existing message in Redis
                await redis_client.lset(REDIS_MESSAGES_KEY, update["index"], update["updated_message"])

        except Exception as e:
            logging.error(f"Error writing to Redis: {e}")
        finally:
            redis_update_queue.task_done()  # Mark the task as done



async def load_previous_data():
    """
    Load and display previous messages and nodes from Redis asynchronously.
    """
    print("\n--- Previously Saved Nodes ---")

    # Fetch nodes and their timestamps
    nodes = await redis_client.hgetall(REDIS_NODES_KEY)
    timestamps = await redis_client.hgetall(f"{REDIS_NODES_KEY}:timestamps")

    # Sort nodes by their timestamps
    sorted_nodes = sorted(
        nodes.items(), key=lambda x: timestamps.get(x[0], "[No timestamp]")
    )
    for node_id, node_name in sorted_nodes:
        timestamp = timestamps.get(node_id, "[No timestamp]")
        print(f"[{timestamp}] Node {node_id}: {node_name}")

    print("\n--- Previously Saved Messages ---")

    # Fetch messages
    messages = await redis_client.lrange(REDIS_MESSAGES_KEY, 0, -1)
    parsed_messages = []

    for msg in messages:
        try:
            message = json.loads(msg)
            station_id = message["station_id"]
            to_id = message.get("to_id", "^all")

            # Resolve names for sender and recipient
            sender_name = nodes.get(station_id, station_id)
            recipient_name = nodes.get(to_id, to_id)

            # Add the message with resolved names
            parsed_messages.append({
                "timestamp": message["timestamp"],
                "sender_name": sender_name,
                "recipient_name": recipient_name,
                "message": message["message"]
            })
        except json.JSONDecodeError:
            logging.warning(f"Skipping malformed message: {msg}")

    # Sort messages by their timestamp and display them
    sorted_messages = sorted(parsed_messages, key=lambda m: m["timestamp"])
    for message in sorted_messages:
        print(f"[{message['timestamp']}] {message['sender_name']} -> {message['recipient_name']}: {message['message']}")


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
        station_id = packet.get("fromId", "[Unknown ID]")
        to_id = packet.get("toId", "^all")
        text_message = packet.get("decoded", {}).get("text", "[No text]")
        timestamp = format_timestamp()

        # DEBUG log for raw message details
        logging.debug(f"Raw msg received: fromId={station_id}, toId={to_id}, text='{text_message}', timestamp={timestamp}")

        # Enqueue the message for Redis update
        redis_update_queue.put_nowait({
            "type": "message",
            "station_id": station_id,
            "to_id": to_id,
            "text_message": text_message,
            "timestamp": timestamp
        })
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
        timestamp = format_timestamp()

        # Determine the node name
        node_name = long_name or short_name or node_id

        # Enqueue the node update for Redis
        redis_update_queue.put_nowait({
            "type": "node",
            "node_id": node_id,
            "node_name": node_name,
            "timestamp": timestamp
        })

        # Log the node announcement without Redis lookup
        print(f"[{timestamp}] Node {node_id}: {node_name}")
    except Exception as e:
        logging.error(f"Error processing node message: {e}")


async def initialize_connected_node(interface):
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
        await redis_client.hset(REDIS_NODES_KEY, node_id_hex, node_name)
        await redis_client.hset(f"{REDIS_NODES_KEY}:timestamps", node_id_hex, timestamp)

        # Shorter message format
        print(f"[{timestamp}] Connected node: {node_id_hex} -> {node_name}")
    except Exception as e:
        logging.error(f"Failed to initialize connected node: {e}", exc_info=True)


async def main():
    """
    Main function to set up the Meshtastic listener for text and node messages.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    logging.getLogger("meshtastic").setLevel(logging.WARNING)  # Suppress non-essential logs

    print("Listening for messages... Press Ctrl+C to exit.")

    # Initialize broadcast node
    await initialize_broadcast_node()

    # Load and display previous data
    await load_previous_data()

    device_path = '/dev/ttyACM0'  # Adjust to your actual device path
    interface = SerialInterface(device_path)

    await initialize_connected_node(interface)

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

