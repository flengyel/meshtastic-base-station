# mesh_console.py
#
# Copyright (C) 2024, 2025 Florian Lengyel WM2D
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import asyncio
import logging
import argparse
import serial.tools.list_ports
from typing import Optional, Tuple
from meshtastic.serial_interface import SerialInterface

from src.station.cli.arg_parser import parse_args
from src.station.cli.display import display_nodes, display_messages, display_telemetry
from src.station.utils.logger import configure_logger
from src.station.handlers.redis_handler import RedisHandler
from src.station.handlers.data_handler import MeshtasticDataHandler
from src.station.utils.constants import LoggingConst
from src.station.config.base_config import BaseStationConfig
from src.station.handlers.meshtastic_handler import MeshtasticHandler
from src.station.ui.factory import create_ui
from src.station.ui.terminal_ui import CursesUI
from src.station.utils.platform_utils import detect_platform, Platform

def suggest_available_ports(logger: logging.Logger) -> None:
    """List available serial ports."""
    try:
        ports = list(serial.tools.list_ports.comports())
        if ports:
            logger.info("Available serial ports:")
            for port in ports:
                logger.info(f"  - {port.device}")
        else:
            logger.info("  No serial ports detected")
    except Exception as e:
        logger.error(f"Cannot list available ports: {e}")

async def setup_redis(station_config: BaseStationConfig, logger: logging.Logger) -> Optional[RedisHandler]:
    """Initialize Redis handler."""
    try:
        redis_handler = RedisHandler(
            host=station_config.redis.host,
            port=station_config.redis.port,
            logger=logger
        )
        if not await redis_handler.verify_connection():
            logger.error(
                f"Could not connect to Redis at "
                f"{station_config.redis.host}:{station_config.redis.port}"
            )
            return None
        return redis_handler
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {e}")
        return None

async def setup_meshtastic(device_path, redis_handler, logger) -> tuple:
    """Initialize Meshtastic interface and handler."""
    try:
        interface = SerialInterface(device_path)
        logger.debug(f"Connected to serial device: {device_path}")
        
        meshtastic_handler = MeshtasticHandler(
            redis_handler=redis_handler,
            interface=interface,
            logger=logger
        )
        await meshtastic_handler.initialize_connected_node()
        return interface, meshtastic_handler
    except FileNotFoundError:
        logger.error(f"Cannot connect to serial device {device_path}: Device not found")
        suggest_available_ports(logger)
        return None, None
    except Exception as e:
        logger.error(f"Cannot connect to serial device {device_path}: {e}")
        suggest_available_ports(logger)
        return None, None

async def handle_cleanup(args, redis_handler, logger) -> bool:
    """Handle cleanup operations if requested."""
    if args.cleanup_days or args.cleanup_corrupted:
        if args.cleanup_days:
            logger.info(f"Cleaning up data older than {args.cleanup_days} days...")
            await redis_handler.cleanup_data(args.cleanup_days)
        if args.cleanup_corrupted:
            logger.info("Cleaning up corrupted data...")
            await redis_handler.cleanup_corrupted_data()
        await redis_handler.close()
        return True
    return False

async def handle_display(args, data_handler, redis_handler, logger) -> bool:
    """Handle display-only modes."""
    if args.display_redis or args.display_nodes or args.display_messages or args.display_telemetry:
        if args.display_nodes:
            await display_nodes(data_handler, logger)
        elif args.display_messages:
            await display_messages(data_handler, logger)
        elif args.display_telemetry:
            await display_telemetry(data_handler, logger)
        else:  # display_redis shows everything
            await display_nodes(data_handler, logger)
            await display_messages(data_handler, logger)
            await display_telemetry(data_handler, logger)
        await redis_handler.close()
        return True
    return False

async def run_ui(args, data_handler, redis_handler, interface, meshtastic_handler, logger):
    """Run the appropriate UI with proper terminal handling."""
    ui = None
    try:
        if args.ui == "curses":
            ui = await CursesUI.create(data_handler, logger)
        else:
            ui = create_ui(args.ui, data_handler, logger)
            await ui.start()

        # Create message publisher task
        publisher_task = asyncio.create_task(redis_handler.message_publisher())
        
        # Run UI
        await ui.run()
        
    except Exception as e:
        logger.error(f"Error running UI: {e}", exc_info=True)
    finally:
        # Cancel publisher task
        if publisher_task:
            publisher_task.cancel()
            try:
                await publisher_task
            except asyncio.CancelledError:
                pass
        
        # Cleanup
        if ui:
            await ui.stop()
        meshtastic_handler.cleanup()
        interface.close()
        await redis_handler.close()

def load_configuration(args, logger):
    """Load the station configuration."""
    station_config = BaseStationConfig.load(path=args.config, logger=logger)
    if args.redis_host:
        station_config.redis.host = args.redis_host
    if args.redis_port:
        station_config.redis.port = args.redis_port
    return station_config

async def run_main(args, logger):
    """Run the main logic of the application."""
    try:
        # Platform detection
        platform = detect_platform()
        logger.info(f"Running on platform: {platform.name}")

        # Load configuration
        station_config = load_configuration(args, logger)
        
        # Setup Redis
        redis_handler = await setup_redis(station_config, logger)
        if not redis_handler:
            return

        # Setup data handler
        data_handler = MeshtasticDataHandler(redis_handler, logger=logger)
        redis_handler.set_data_handler(data_handler)

        # Handle cleanup requests if any
        if await handle_cleanup(args, redis_handler, logger):
            return

        # Handle display-only modes
        if await handle_display(args, data_handler, redis_handler, logger):
            return

        # Setup Meshtastic interface
        interface, meshtastic_handler = await setup_meshtastic(args.device, redis_handler, logger)
        if not interface or not meshtastic_handler:
            await redis_handler.close()
            return

        # Run UI
        await run_ui(args, data_handler, redis_handler, interface, meshtastic_handler, logger)
                
    except Exception as e:
        logger.error(f"Error in main application: {e}", exc_info=True)
        return 1

async def main():
    """Main application entry point."""
    args = parse_args()
    logger = configure_logger(
        name=__name__,
        log_levels=args.log_levels,
        use_threshold=args.threshold,
        log_file=None if args.no_file_logging else LoggingConst.DEFAULT_FILE,
        debugging=args.debugging
    )

    try:
        await run_main(args, logger)
    except KeyboardInterrupt:
        logger.info("Program terminated by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        print(f"\nUnexpected error: {e}")