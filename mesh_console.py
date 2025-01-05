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
from logger import configure_logger, get_available_levels
from redis_handler import RedisHandler
from meshtastic_data_handler import MeshtasticDataHandler
import logging

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
    
    args = parser.parse_args()
    
    # Convert comma-separated log levels to list
    args.log_levels = [level.strip() for level in args.log.split(",")]
    
    return args

async def display_stored_data(data_handler):
    """Display previously stored data."""
    logger.info("--- Previously Saved Nodes ---")
    nodes = await data_handler.get_formatted_nodes()
    if not nodes:
        logger.info("[No nodes found]")
    else:
        for node in sorted(nodes, key=lambda x: x['timestamp']):
            logger.info(f"[{node['timestamp']}] Node {node['id']}: {node['name']}")

    logger.info("\n--- Previously Saved Messages ---")
    messages = await data_handler.get_formatted_messages()
    if not messages:
        logger.info("[No messages found]")
    else:
        for msg in sorted(messages, key=lambda x: x['timestamp']):
            logger.info(f"[{msg['timestamp']}] {msg['from']} -> {msg['to']}: {msg['text']}")

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

    # Initialize handlers
    redis_handler = RedisHandler(logger=logger)
    data_handler = MeshtasticDataHandler(redis_handler, logger=logger)

    # Display Redis data and exit if requested
    if args.display_redis:
        logger.info("Displaying Redis data ...")
        await display_stored_data(data_handler)
        return

    # Initialize device connection
    try:
        interface = SerialInterface(args.device)
        logger.debug(f"Connected to serial device: {args.device}")
    except FileNotFoundError:
        logger.error(f"Cannot connect to serial device {args.device}: Device not found.")
        suggest_available_ports()
        return
    except Exception as e:
        logger.error(f"Cannot connect to serial device {args.device}: {e}")
        suggest_available_ports()
        return

    # Display stored data
    await display_stored_data(data_handler)

    # Subscribe to message topics
    pub.subscribe(on_text_message, "meshtastic.receive.text")
    pub.subscribe(on_node_message, "meshtastic.receive.user")
    logger.info("Subscribed to text and user messages.")

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
