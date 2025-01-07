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

# Initialize asyncio queue for Redis updates
redis_update_queue = asyncio.Queue()

def parse_arguments():
    """Parse command-line arguments with enhanced configuration options."""
    parser = argparse.ArgumentParser(
        description="Meshtastic Console",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --config config.yaml              # Use specific config file
  %(prog)s --device COM3                     # Override device port
  %(prog)s --redis-host pironman5.local      # Override Redis host
  %(prog)s --log INFO,PACKET                 # Show INFO and PACKET messages
        """
    )
    
    # Configuration
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    
    # Device configuration
    parser.add_argument(
        "--device",
        type=str,
        help="Serial interface device (overrides config)"
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
    parser.add_argument(
        "--display-redis",
        action="store_true",
        help="Display Redis data and exit without connecting to the serial device"
    )

    # Existing logging configuration
    log_group = parser.add_argument_group('Logging Options')
    log_group.add_argument(
        "--log",
        type=str,
        help=f"Comma-separated list of log levels to include. Available levels: {', '.join(get_available_levels())}"
    )
    log_group.add_argument(
        "--threshold",
        action="store_true",
        help="Treat log level as threshold"
    )
    log_group.add_argument(
        "--no-file-logging",
        action="store_true",
        help="Disable logging to file"
    )
    
    return parser.parse_args()

async def display_stored_data(data_handler):
    """Display previously stored data."""
    # Display nodes
    logger.info("--- Previously Saved Nodes ---")
    nodes = await data_handler.get_formatted_nodes()
    if not nodes:
        logger.info("[No nodes found]")
    else:
        for node in sorted(nodes, key=lambda x: x['timestamp']):
            logger.info(f"[{node['timestamp']}] Node {node['id']}: {node['name']}")

    # Display messages
    logger.info("\n--- Previously Saved Messages ---")
    messages = await data_handler.get_formatted_messages()
    if not messages:
        logger.info("[No messages found]")
    else:
        for msg in sorted(messages, key=lambda x: x['timestamp']):
            logger.info(f"[{msg['timestamp']}] {msg['from']} -> {msg['to']}: {msg['text']}")

    # Display device telemetry
    logger.info("\n--- Previously Saved Device Telemetry ---")
    device_telemetry = await data_handler.get_formatted_device_telemetry()
    if not device_telemetry:
        logger.info("[No device telemetry found]")
    else:
        for tel in sorted(device_telemetry, key=lambda x: x['timestamp'])[-10:]:  # Last 10 entries
            logger.info(f"[{tel['timestamp']}] {tel['from_id']}: battery={tel['battery']}%, voltage={tel['voltage']}V")

    # Display network telemetry
    logger.info("\n--- Previously Saved Network Telemetry ---")
    network_telemetry = await data_handler.get_formatted_network_telemetry()
    if not network_telemetry:
        logger.info("[No network telemetry found]")
    else:
        for tel in sorted(network_telemetry, key=lambda x: x['timestamp'])[-5:]:  # Last 5 entries
            logger.info(f"[{tel['timestamp']}] {tel['from_id']}: {tel['online_nodes']}/{tel['total_nodes']} nodes online")

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

                update = await asyncio.wait_for(redis_update_queue.get(), timeout=0.1)
                logger.debug(f"Received update type: {update['type']}")
                
                # Process the packet
                await data_handler.process_packet(update["packet"], update["type"])
                redis_update_queue.task_done()
                
            except asyncio.TimeoutError:
                continue  # No updates available, continue polling
            except Exception as e:
                logger.error(f"Error in dispatcher: {e}", exc_info=True)
                redis_update_queue.task_done()
                
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

# minimal implementation for now
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

async def main():
    """Main function to set up the Meshtastic listener."""
    # Parse arguments
    args = parse_arguments()
    
    try:
        # Load configuration
        if args.config:
            config = BaseStationConfig.from_yaml(args.config)
        else:
            config = BaseStationConfig.load()
        
        # Override config with command line arguments
        if args.device:
            config.device.port = args.device
        if args.redis_host:
            config.redis.host = args.redis_host
        if args.redis_port:
            config.redis.port = args.redis_port
        if args.log:
            config.logging.level = args.log
        if args.threshold:
            config.logging.use_threshold = True
        if args.no_file_logging:
            config.logging.file = None
            
        # Configure logging
        global logger
        logger = configure_logger(
            name=__name__,
            log_levels=config.logging.level.split(','),
            use_threshold=config.logging.use_threshold,
            log_file=config.logging.file,
            debugging=config.logging.debugging
        )

        # Initialize Redis handler with configuration
        logger.debug(f"Initializing Redis handler with {config.redis.host}:{config.redis.port}")
        redis_handler = RedisHandler(
            host=config.redis.host,
            port=config.redis.port,
            logger=logger
        )

        # Verify Redis connection with timeout
        try:
            await asyncio.wait_for(redis_handler.verify_connection(), timeout=10.0)
        except asyncio.TimeoutError:
            logger.error("Redis connection verification timed out")
            await redis_handler.close()
            return
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            await redis_handler.close()
            return

        data_handler = MeshtasticDataHandler(redis_handler, logger=logger)

        # Display Redis data and exit if requested
        if args.display_redis:
            logger.info("Displaying Redis data ...")
            await display_stored_data(data_handler)
            await redis_handler.close()
            return

        # Initialize device connection
        try:
            logger.debug(f"Connecting to device at {config.device.port}")
            interface = SerialInterface(config.device.port)
            logger.debug("Serial interface connected successfully")
        except FileNotFoundError:
            logger.error(f"Cannot connect to serial device {config.device.port}: Device not found.")
            suggest_available_ports()
            await redis_handler.close()
            return
        except Exception as e:
            logger.error(f"Cannot connect to serial device {config.device.port}: {e}")
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
            logger.info("Interfaces closed.")

    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
        if 'redis_handler' in locals():
            await redis_handler.close()
        if 'interface' in locals() and hasattr(interface, 'close'):
            interface.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program terminated.")
