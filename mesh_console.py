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
import logging
from meshtastic.serial_interface import SerialInterface
import serial.tools.list_ports
from src.station.utils.logger import configure_logger, get_available_levels
from src.station.handlers.redis_handler import RedisHandler
from src.station.handlers.data_handler import MeshtasticDataHandler
from src.station.utils.constants import DisplayConst, DeviceConst, LoggingConst
from src.station.config.base_config import BaseStationConfig
from src.station.handlers.meshtastic_handler import MeshtasticHandler
from src.station.utils.constants import RedisConst
import os

os.environ["KIVY_NO_ARGS"] = "1" # Prevent Kivy from parsing command-line arguments
os.environ["KIVY_NO_CONSOLELOG"] = "1" # Prevent Kivy from logging to console

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
  %(prog)s --gui                                    # Start in GUI mode
        """
    )

    # Device configuration
    parser.add_argument(
        "--device",
        type=str,
        default=DeviceConst.DEFAULT_PORT_LINUX,
        help=f"Serial interface device (default: {DeviceConst.DEFAULT_PORT_LINUX})"
    )

    # Logging configuration
    log_group = parser.add_argument_group('Logging Options')
    log_group.add_argument(
        "--log",
        type=str,
        default=LoggingConst.DEFAULT_LEVEL,
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

    # Other options
    parser.add_argument(
        "--display-redis",
        action="store_true",
        help="Display Redis data and exit"
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

    # GUI mode
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Start in GUI mode using Kivy interface"
    )

    # Cleanup options
    cleanup_group = parser.add_argument_group('Cleanup Options')
    cleanup_group.add_argument(
        "--cleanup-days",
        type=int,
        help="Remove data older than specified days"
    )
    cleanup_group.add_argument(
        "--cleanup-corrupted",
        action="store_true",
        help="Remove corrupted data entries"
    )

    args = parser.parse_args()
    args.log_levels = [level.strip() for level in args.log.split(",")]
    return args

async def display_stored_data(data_handler):
    """Display previously stored data."""
    # Display nodes
    print("\n--- Previously Saved Nodes ---")  # Always print headers
    data_handler.logger.debug("Attempting to retrieve formatted nodes...")
    nodes = await data_handler.get_formatted_nodes()
    data_handler.logger.debug(f"Retrieved {len(nodes) if nodes else 0} nodes")
    if not nodes:
        print("[No nodes found]")
    else:
        for node in sorted(nodes, key=lambda x: x['timestamp']):
            print(f"[{node['timestamp']}] Node {node['id']}: {node['name']}")

    # Display messages
    print("\n--- Previously Saved Messages ---")
    data_handler.logger.debug("Attempting to retrieve formatted messages...")
    messages = await data_handler.get_formatted_messages()
    data_handler.logger.debug(f"Retrieved {len(messages) if messages else 0} messages")
    if not messages:
        print("[No messages found]")
    else:
        for msg in sorted(messages, key=lambda x: x['timestamp']):
            print(f"[{msg['timestamp']}] {msg['from']} -> {msg['to']}: {msg['text']}")

    # Display device telemetry
    print("\n--- Previously Saved Device Telemetry ---")
    data_handler.logger.debug("Attempting to retrieve device telemetry...")
    device_telemetry = await data_handler.get_formatted_device_telemetry()
    data_handler.logger.debug(f"Retrieved {len(device_telemetry) if device_telemetry else 0} device telemetry records")
    if not device_telemetry:
        print("[No device telemetry found]")
    else:
        for tel in sorted(device_telemetry, key=lambda x: x['timestamp'])[-DisplayConst.MAX_DEVICE_TELEMETRY:]:  # Last 10 entries
            print(f"[{tel['timestamp']}] {tel['from_id']}: battery={tel['battery']}%, voltage={tel['voltage']}V")

    # Display network telemetry
    print("\n--- Previously Saved Network Telemetry ---")
    data_handler.logger.debug("Attempting to retrieve network telemetry...")
    network_telemetry = await data_handler.get_formatted_network_telemetry()
    data_handler.logger.debug(f"Retrieved {len(network_telemetry) if network_telemetry else 0} network telemetry records")
    if not network_telemetry:
        print("[No network telemetry found]")
    else:
        for tel in sorted(network_telemetry, key=lambda x: x['timestamp'])[-DisplayConst.MAX_NETWORK_TELEMETRY:]:  # Last 5 entries
            print(f"[{tel['timestamp']}] {tel['from_id']}: {tel['online_nodes']}/{tel['total_nodes']} nodes online")

def suggest_available_ports(logger: logging.Logger) -> None:
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
    args = parse_arguments()

    # Configure logger
    logger = configure_logger(
        name=__name__,
        log_levels=args.log_levels,
        use_threshold=args.threshold,
        log_file=None if args.no_file_logging else LoggingConst.DEFAULT_FILE,
        debugging=args.debugging
    )

    # Load configuration into BaseStationConfig instance
    config = BaseStationConfig.load(path=args.config, logger=logger)
    if args.redis_host:
        config.redis.host = args.redis_host
    if args.redis_port:
        config.redis.port = args.redis_port

    # Initialize Redis handler
    redis_handler = None
    try:
        if args.gui:
            from src.station.ui.gui_redis_handler import GuiRedisHandler
            redis_handler = GuiRedisHandler(
                host=config.redis.host,
                port=config.redis.port,
                logger=logger
            )
        else:
            redis_handler = RedisHandler(
                host=config.redis.host,
                port=config.redis.port,
                logger=logger
            )

        if not await redis_handler.verify_connection():
            logger.error(f"Could not connect to Redis at {config.redis.host}:{config.redis.port}")
            return
    except Exception as e:
        logger.error(f"Unexpected error initializing Redis: {e}")
        if args.debugging:
            logger.debug("Initialization error details:", exc_info=True)
        return

    data_handler = MeshtasticDataHandler(redis_handler, logger=logger)
    # Set data handler for redis_handler or it will raise an error
    redis_handler.set_data_handler(data_handler) # Delayed assignment

    # Handle cleanup if requested
    if args.cleanup_days or args.cleanup_corrupted:
        if args.cleanup_days:
            logger.info(f"Cleaning up data older than {args.cleanup_days} days...")
            await redis_handler.cleanup_data(args.cleanup_days)
            
        if args.cleanup_corrupted:
            logger.info("Cleaning up corrupted data...")
            await redis_handler.cleanup_corrupted_data()
            
        await redis_handler.close()
        return
    
    # Display Redis data and exit
    if args.display_redis:
        logger.info("Displaying Redis data ...")
        await display_stored_data(data_handler)
        await redis_handler.close()
        return

    try:
        interface = SerialInterface(args.device)
        logger.debug(f"Connected to serial device: {args.device}, {interface}")

        # Start Meshtastic handler to subscribe to meshtastic events
        meshtastic_handler = MeshtasticHandler(redis_handler=redis_handler,
                interface=interface,
                logger=logger
        )    

        # Initialize connected node
        await meshtastic_handler.initialize_connected_node()

        # Start message publisher
        publisher_task = asyncio.create_task(redis_handler.message_publisher())
        logger.debug(f"Created publisher task: {publisher_task}")

    except FileNotFoundError:
        logger.error(f"Cannot connect to serial device {args.device}: Device not found.")
        suggest_available_ports(logger)
        await redis_handler.close()
        return
    except Exception as e:
        logger.error(f"Cannot connect to serial device {args.device}: {e}")
        suggest_available_ports(logger)
        await redis_handler.close()
        return

    if args.gui:
        try:
            from src.station.ui.mvc_app import MeshtasticBaseApp
            app = MeshtasticBaseApp(
                redis_handler=redis_handler,
                data_handler=data_handler,
                logger=logger,
                config=config  # Pass BaseStationConfig instance to GUI
            )

            # Ensure message publisher runs alongside GUI
            app._tasks.append(publisher_task)
            await app.start()
        except ImportError:
            logger.error("GUI mode requires Kivy. Please install with: pip install kivy")
            await redis_handler.close()
            return
        except Exception as e:
            logger.error(f"Error starting GUI: {e}")
            await redis_handler.close()
            return
    else:
        # CLI mode
        await display_stored_data(data_handler)
        logger.info("Listening for messages... Type Ctrl+C to exit.")

        try:
            await publisher_task  # Run message publisher in CLI mode
        except KeyboardInterrupt:
            logger.info("Shutdown initiated...")
            publisher_task.cancel()
        finally:
            meshtastic_handler.cleanup()
            interface.close()
            await redis_handler.close()
            logger.info("Interface closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated.")
