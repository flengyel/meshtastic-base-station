# mesh_console.py
#
# Copyright (C) 2024, 2025 Florian Lengyel WM2D
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
import serial.tools.list_ports
from src.station.utils.logger import configure_logger, get_available_levels
from src.station.handlers.redis_handler import RedisHandler
from src.station.handlers.data_handler import MeshtasticDataHandler
from src.station.config.base_config import BaseStationConfig
import redis # For Redis exceptions

# Initialize asyncio queue for Redis updates
redis_update_queue = asyncio.Queue()

def parse_arguments():
    """Parse command-line arguments with enhanced logging options."""
    parser = argparse.ArgumentParser(
        description="Meshtastic Console",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --device /dev/ttyACM0                    # Use default INFO level
  %(prog)s --log INFO,PACKET                        # Show INFO and PACKET messages
  %(prog)s --log DEBUG --threshold                  # Show DEBUG and above
  %(prog)s --log PACKET,REDIS --no-file-logging     # Show only PACKET and REDIS, console only
        """
    )
    
    # Device configuration
    parser.add_argument(
        "--device",
        type=str,
        default="/dev/ttyACM0",
        help="Serial interface device (default: /dev/ttyACM0)"
    )
    
    # Logging configuration
    log_group = parser.add_argument_group('Logging Options')
    log_group.add_argument(
        "--log",
        type=str,
        default="INFO",
        help=f"Comma-separated list of log levels to include. Available levels: {', '.join(get_available_levels())}"
    )
    log_group.add_argument(
        "--threshold",
        action="store_true",
        help="Treat log level as threshold (show all messages at or above specified level)"
    )
    log_group.add_argument(
        "--no-file-logging",
        action="store_true",
        help="Disable logging to file"
    )
    
    # Other options
    parser.add_argument(
        "--display-redis",
        action="store_true",
        help="Display Redis data and exit without connecting to the serial device"
    )
    parser.add_argument(
        "--debugging",
        action="store_true",
        help="Print diagnostic debugging statements"
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    
    # Redis configuration
    parser.add_argument(
        "--redis-host",
        type=str,
        help="Redis host (overrides config)"
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        help="Redis port (overrides config)"
    )
    
    args = parser.parse_args()
    
    # Convert comma-separated log levels to list
    args.log_levels = [level.strip() for level in args.log.split(",")]
    
    return args

async def display_stored_data(data_handler):
    """Display previously stored data."""
    # Display nodes
    print("\n--- Previously Saved Nodes ---")  # Always print headers
    logger.debug("Attempting to retrieve formatted nodes...")
    nodes = await data_handler.get_formatted_nodes()
    logger.debug(f"Retrieved {len(nodes) if nodes else 0} nodes")
    if not nodes:
        print("[No nodes found]")
    else:
        for node in sorted(nodes, key=lambda x: x['timestamp']):
            print(f"[{node['timestamp']}] Node {node['id']}: {node['name']}")

    # Display messages
    print("\n--- Previously Saved Messages ---")
    logger.debug("Attempting to retrieve formatted messages...")
    messages = await data_handler.get_formatted_messages()
    logger.debug(f"Retrieved {len(messages) if messages else 0} messages")
    if not messages:
        print("[No messages found]")
    else:
        for msg in sorted(messages, key=lambda x: x['timestamp']):
            print(f"[{msg['timestamp']}] {msg['from']} -> {msg['to']}: {msg['text']}")

    # Display device telemetry
    print("\n--- Previously Saved Device Telemetry ---")
    logger.debug("Attempting to retrieve device telemetry...")
    device_telemetry = await data_handler.get_formatted_device_telemetry()
    logger.debug(f"Retrieved {len(device_telemetry) if device_telemetry else 0} device telemetry records")
    if not device_telemetry:
        print("[No device telemetry found]")
    else:
        for tel in sorted(device_telemetry, key=lambda x: x['timestamp'])[-10:]:  # Last 10 entries
            print(f"[{tel['timestamp']}] {tel['from_id']}: battery={tel['battery']}%, voltage={tel['voltage']}V")

    # Display network telemetry
    print("\n--- Previously Saved Network Telemetry ---")
    logger.debug("Attempting to retrieve network telemetry...")
    network_telemetry = await data_handler.get_formatted_network_telemetry()
    logger.debug(f"Retrieved {len(network_telemetry) if network_telemetry else 0} network telemetry records")
    if not network_telemetry:
        print("[No network telemetry found]")
    else:
        for tel in sorted(network_telemetry, key=lambda x: x['timestamp'])[-5:]:  # Last 5 entries
            print(f"[{tel['timestamp']}] {tel['from_id']}: {tel['online_nodes']}/{tel['total_nodes']} nodes online")


def on_text_message(packet, interface):
    """Callback for text messages."""
    logger.packet(f"on_text_message: {packet}")
    try:
        redis_update_queue.put_nowait({
            "type": "text",
            "packet": packet
        })
    except Exception as e:
        logger.error(f"Error in text message callback: {e}", exc_info=True)

def on_node_message(packet, interface):
    """Callback for node messages."""
    logger.packet(f"on_node_message: {packet}")
    try:
        redis_update_queue.put_nowait({
            "type": "node",
            "packet": packet
        })
    except Exception as e:
        logger.error(f"Error in node message callback: {e}", exc_info=True)

def on_telemetry_message(packet, interface):
    """Callback for telemetry messages."""
    logger.packet(f"on_telemetry_message: {packet}")
    try:
        redis_update_queue.put_nowait({
            "type": "telemetry",
            "packet": packet
        })
    except Exception as e:
        logger.error(f"Error in telemetry callback: {e}", exc_info=True)

def suggest_available_ports():
    """List available serial ports."""
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

async def redis_dispatcher(data_handler):
    """Process Redis updates from the queue."""
    try:
        logger.info("Redis dispatcher task started.")
        last_size = 0
        while True:
            try:
                current_size = redis_update_queue.qsize()
                if current_size != last_size:
                    logger.debug(f"Queue size changed to: {current_size}")
                    last_size = current_size

                # Use a shorter timeout to prevent hanging
                try:
                    update = await asyncio.wait_for(redis_update_queue.get(), timeout=1.0)
                    logger.debug(f"Received update type: {update['type']}")
                    
                    # Process the packet
                    await data_handler.process_packet(update["packet"], update["type"])
                    redis_update_queue.task_done()
                except asyncio.TimeoutError:
                    # Periodic heartbeat
                    logger.debug("Dispatcher heartbeat - no updates")
                    await asyncio.sleep(5.0)
                    continue
                    
            except Exception as e:
                logger.error(f"Error in dispatcher: {e}", exc_info=True)
                redis_update_queue.task_done()
                await asyncio.sleep(1.0)  # Prevent tight error loops
                
    except asyncio.CancelledError:
        logger.info("Dispatcher received cancellation signal")
        # Process remaining updates during shutdown
        remaining = redis_update_queue.qsize()
        if remaining > 0:
            logger.info(f"Processing {remaining} remaining updates during shutdown")
            while not redis_update_queue.empty():
                update = redis_update_queue.get_nowait()
                try:
                    await data_handler.process_packet(update["packet"], update["type"])
                except Exception as e:
                    logger.error(f"Error processing remaining update: {e}")
                finally:
                    redis_update_queue.task_done()
        logger.debug("Redis dispatcher completed final updates")
        raise  # Re-raise to ensure proper task cleanup

async def main():
    """Main function to set up the Meshtastic listener."""
    # Parse arguments and set up logging
    args = parse_arguments()
    
    global logger
    logger = configure_logger(
        name=__name__,
        log_levels=args.log_levels,
        use_threshold=args.threshold,
        log_file=None if args.no_file_logging else 'meshtastic.log',
        debugging=args.debugging
    )

    # First step: load config if specified
    config = None
    if args.config:
        logger.debug(f"Attempting to load config from: {args.config}")
        try:
            from src.station.config.base_config import BaseStationConfig
            logger.debug("Successfully imported BaseStationConfig")
            config = BaseStationConfig.load() # cls knows about directories
            logger.debug(f"Loaded configuration from {args.config}")
            logger.debug(f"Config contains: redis.host={config.redis.host}, redis.port={config.redis.port}")
        except Exception as e:
            logger.warning(f"Could not load configuration: {e}")
            logger.debug(f"Config load error details:", exc_info=True)
            logger.info("Continuing with command line settings")

# Initialize handlers
    try:
        redis_handler = RedisHandler(
            host=config.redis.host if config else "localhost",
            port=config.redis.port if config else 6379,
            logger=logger
        )    
        await redis_handler.verify_connection()
    except redis.exceptions.ConnectionError as e:
        logger.error(f"Could not connect to Redis at {config.redis.host if config else 'localhost'}:{config.redis.port if config else 6379}")
        logger.error("Please check Redis configuration and ensure Redis server is running")
        logger.debug(f"Redis connection error details:", exc_info=True)
        return  # Exit gracefully
    except Exception as e:
        logger.error(f"Unexpected error initializing Redis: {e}")
        logger.debug("Initialization error details:", exc_info=True)
        return  # Exit gracefully

    data_handler = MeshtasticDataHandler(redis_handler, logger=logger)

    # Display Redis data and exit if requested
    if args.display_redis:
        logger.info("Displaying Redis data ...")
        await display_stored_data(data_handler)
        await redis_handler.close()
        return

    # Initialize device connection
    try:
        interface = SerialInterface(args.device)
        logger.debug(f"Connected to serial device: {args.device}")
    except FileNotFoundError:
        logger.error(f"Cannot connect to serial device {args.device}: Device not found.")
        suggest_available_ports()
        await redis_handler.close()
        return
    except Exception as e:
        logger.error(f"Cannot connect to serial device {args.device}: {e}")
        suggest_available_ports()
        await redis_handler.close()
        return

    # Display stored data
    await display_stored_data(data_handler)

    # Subscribe to message topics
    pub.subscribe(on_text_message, "meshtastic.receive.text")
    pub.subscribe(on_node_message, "meshtastic.receive.user")
    pub.subscribe(on_telemetry_message, "meshtastic.receive.telemetry")
    logger.info("Subscribed to text, user, and telemetry messages.")

    # Start Redis dispatcher
    dispatcher_task = asyncio.create_task(redis_dispatcher(data_handler))
    logger.debug(f"Created redis_dispatcher task: {dispatcher_task}")

    try:
        logger.info("Listening for messages... Press Ctrl+C to exit.")
        await dispatcher_task
    except KeyboardInterrupt:
        logger.info("Shutdown initiated...")
        dispatcher_task.cancel()
        try:
            await dispatcher_task  # Wait for task to finish processing queue
        except asyncio.CancelledError:
            pass  # Expected during shutdown
    finally:
        interface.close()
        await redis_handler.close()
        logger.info("Interface closed.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program terminated.")
