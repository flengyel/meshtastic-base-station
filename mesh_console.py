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

import argparse
import asyncio
from pubsub import pub
from meshtastic.serial_interface import SerialInterface
import json
import serial.tools.list_ports  # Required for listing available ports
from logger import configure_logging, get_logger
from datetime import datetime
from redis_handler import RedisHandler

# Initialize asyncio queue for Redis updates
redis_update_queue = asyncio.Queue()

# Initialize Redis connection
redis_handler = RedisHandler()

def parse_arguments():
    """
    Parse command-line arguments for interface device, logging level, and Redis display.
    """
    parser = argparse.ArgumentParser(description="Meshtastic Console")
    parser.add_argument(
        "--device",
        type=str,
        default="/dev/ttyACM0",
        help="Serial interface device (default: /dev/ttyACM0)"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "PACKET"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    parser.add_argument(
        "--display-redis",
        action="store_true",
        help="Display Redis data and exit without connecting to the serial device"
    )
    return parser.parse_args()

# Parse arguments and configure logging
args = parse_arguments()
configure_logging(args.log_level)  # Global logger configured here
logger = get_logger(__name__)

async def process_node_update(update):
    """
    Asynchronous function to process node updates in Redis.
    """
    try:
        # Delegate node update to RedisHandler
        await redis_handler.update_node(
            node_id=update["node_id"],
            node_name=update["node_name"],
            timestamp=update["timestamp"],
            battery_level=update.get("battery_level"),
            position=update.get("position")
        )

        # Delegate stored message updates to RedisHandler
        await redis_handler.update_stored_messages(update["node_id"], update["node_name"])
    except Exception as e:
        logger.error(f"Error processing node update: {e}", exc_info=True)

async def redis_writer():
    """
    Asynchronous coroutine to process Redis updates from the queue.
    """
    while True:
        update = await redis_update_queue.get()  # Wait for an update
        try:
            # Delegate update processing to RedisHandler
            await redis_handler.process_update(update)
        except Exception as e:
            logger.error(f"Error writing to Redis: {e}", exc_info=True)
        finally:
            redis_update_queue.task_done()  # Mark the task as done

async def load_nodes():
    """
    Load and display previously saved nodes.
    """
    logger.info("--- Previously Saved Nodes ---")

    # Fetch nodes and timestamps from RedisHandler
    nodes, timestamps = await redis_handler.load_nodes()

    if not nodes:
        logger.info("[No nodes found]")
    else:
        parsed_nodes = []
        for node_id, node_name in nodes.items():
            # Retrieve corresponding timestamp
            timestamp = timestamps.get(node_id)
            if not timestamp:
                logger.warning(f"Skipped node with missing timestamp: Node {node_id} -> {node_name}")
                continue  # Skip nodes without a timestamp

            parsed_nodes.append({
                "timestamp": timestamp,
                "node_id": node_id,
                "node_name": node_name
            })

        # Sort nodes by timestamp
        sorted_nodes = sorted(parsed_nodes, key=lambda n: n["timestamp"])

        # Log sorted nodes
        for node in sorted_nodes:
            logger.info(f"[{node['timestamp']}] Node {node['node_id']}: {node['node_name']}")


async def load_messages():
    """
    Load and display previously saved messages.
    """
    logger.info("--- Previously Saved Messages ---")

    # Fetch messages from RedisHandler
    messages = await redis_handler.load_messages()

    if not messages:
        logger.info("[No messages found]")
    else:
        parsed_messages = []
        for msg in messages:
            try:
                message = json.loads(msg)

                # Ensure timestamp exists
                timestamp = message.get("timestamp")
                if not timestamp:
                    logger.warning(f"Skipped message with missing timestamp: {msg}")
                    continue  # Skip messages without a timestamp

                # Collect parsed messages for sorting
                parsed_messages.append({
                    "timestamp": timestamp,
                    "station_id": message["station_id"],
                    "to_id": message.get("to_id", "Unknown"),
                    "message": message["message"]
                })
            except json.JSONDecodeError:
                logger.warning(f"Skipped malformed message: {msg}")

        # Sort parsed messages by timestamp
        sorted_messages = sorted(parsed_messages, key=lambda m: m["timestamp"])

        # Log sorted messages
        for message in sorted_messages:
            logger.info(
                f"[{message['timestamp']}] {message['station_id']} -> {message['to_id']}: {message['message']}"
            )


async def cancellable_task():
    """
    A cancellable infinite loop task.
    """
    try:
        while True:
            await asyncio.sleep(0.01) # Small delay to avoid CPU hogging
    except asyncio.CancelledError:
        logger.info("Exiting...")

def on_telemetry_message(packet, interface):
    """
    Callback to enqueue telemetry messages for Redis updates
    """
    # for now, only log packets
    logger.packet(f"on_telemetry_message: {packet}")

def on_text_message(packet, interface):
    """
    Callback to enqueue text messages for Redis updates.
    """
    logger.packet(f"on_text_message: {packet}")
    try:
        # Extract the station ID (fromId)
        station_id = packet.get("fromId")
        if station_id is None:
            logger.warning(f"Text message is missing the station ID (fromId): {packet}")
            return  # Exit as we cannot process a message without a station ID

        # Extract the recipient ID (toId)
        to_id = packet.get("toId")
        if to_id is None:
            logger.warning(f"Text message is missing the recipient ID (toId): {packet}")
            to_id = "?"  # Use "?" for unknown recipient ID

        # Extract the text message
        text_message = packet.get("decoded", {}).get("text", "")

        # Warn if the text message is empty
        if not text_message:
            logger.warning(f"Text message contains no text: {packet}")

        # Get the current timestamp
        timestamp = redis_handler.format_timestamp()

        # DEBUG log for raw message details
        logger.debug(
            f"Raw msg received: fromId={station_id}, toId={to_id}, text='{text_message}', timestamp={timestamp}"
        )

        # Enqueue the message for Redis update
        redis_update_queue.put_nowait({
            "type": "message",
            "station_id": station_id,
            "to_id": to_id,
            "text_message": text_message,
            "timestamp": timestamp
        })
    except Exception as e:
        logger.error(f"Error processing text message: {e}", exc_info=True)

def on_node_message(packet, interface):
    """
    Callback to process received node messages and enqueue them for Redis updates.
    """

    # Log the packet first if required
    logger.packet(f"on_node_message: {packet}")

    try:
        # Extract the node ID (fromId)
        node_id = packet.get("fromId")
        if node_id is None:
            logger.warning(f"Node message is missing the station ID (fromId): {packet}")
            return  # Exit early as we cannot process a node without a node_id

        # Extract node information
        node_info = packet.get("decoded", {}).get("user", {})
        long_name = node_info.get("longName", "")
        short_name = node_info.get("shortName", "")

        # Determine the node name
        node_name = long_name or short_name or None

        # Check for missing node name and log a warning if necessary
        if not node_name:
            logger.warning(f"Node message has no identifiable name (longName, shortName): {packet}")
            return  # Exit as we cannot process a node without a name

        # Get the current timestamp
        timestamp = redis_handler.format_timestamp()

        # Enqueue the node update for Redis
        redis_update_queue.put_nowait({
            "type": "node",
            "node_id": node_id,
            "node_name": node_name,
            "timestamp": timestamp
        })

        # Log the node announcement at DEBUG level
        logger.debug(f"Node announcement: {timestamp} Node {node_id}: {node_name}")

    except Exception as e:
        logger.error(f"Error processing node message: {e}", exc_info=True)

async def initialize_connected_node(interface):
    """
    Initialize the Redis node lookup with the station ID and name of the connected node.
    """
    try:
        # Query the connected node info
        node_info = interface.getMyNodeInfo()
        node_id_decimal = node_info.get("num", None)
        if node_id_decimal is None:
            logger.error("Node ID (num) not found in node info.")
            return

        # Convert the numeric node ID to hexadecimal with Meshtastic format (!hex)
        node_id_hex = f"!{node_id_decimal:08x}"
        user = node_info.get("user", {})
        node_name = user.get("longName", user.get("shortName", node_id_hex))
        timestamp = redis_handler.format_timestamp()

        # Use redis_handler to save the connected node details
        await redis_handler.update_node(
            node_id=node_id_hex,
            node_name=node_name,
            timestamp=timestamp
        )

        logger.info(f"[{timestamp}] Connected node: {node_id_hex} -> {node_name}")
    except Exception as e:
        logger.error(f"Failed to initialize connected node: {e}", exc_info=True)

def suggest_available_ports():
    """
    Suggest available serial ports to the user.
    """
    try:
        logger.info("Available ports:")
        ports = list(serial.tools.list_ports.comports())
        if ports:
            for port in ports:
                logger.info(f"  - {port.device}")
        else:
            logger.info("  No serial ports detected.")
    except Exception as e:
        logger.error(f"Cannot list available ports: {e}")

async def main():
    """
    Main function to set up the Meshtastic listener for text and node messages.
    """

    # Display Redis data and exit if the flag is set
    if args.display_redis:
        logger.info("Displaying Redis data ...")
        await load_nodes()
        await load_messages()
        return  # Exit the program gracefully

    # Initialize device path
    device_path = args.device

    try:
        # Attempt to initialize the serial interface
        # The serial library logs the connection attempt at DEBUG level
        interface = SerialInterface(device_path)
        logger.debug(f"Connected to serial device: {device_path}")
    except FileNotFoundError:
        logger.error(f"Cannot connect to serial device {device_path}: Device not found.")
        suggest_available_ports()
        return  # Exit the program gracefully
    except Exception as e:
        logger.error(f"Cannot connect to serial device {device_path}: {e}")
        suggest_available_ports()
        return  # Exit the program gracefully

    logger.info("Listening for messages... Press Ctrl+C to exit.")

    # Initialize broadcast node
    await redis_handler.initialize_broadcast_node()

    # Load and display previous data
    await load_nodes()
    await load_messages()

    await initialize_connected_node(interface)

    # Subscribe to message topics using pubsub
    pub.subscribe(on_text_message, "meshtastic.receive.text")
    pub.subscribe(on_node_message, "meshtastic.receive.user")
    pub.subscribe(on_telemetry_message, "meshtastic.receive.telemetry")

    logger.info("Subscribed to text, telementry, and user messages.")

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
        logger.info("Interface closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program terminated.")

