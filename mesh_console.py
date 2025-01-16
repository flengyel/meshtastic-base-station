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
import serial.tools.list_ports
from meshtastic.serial_interface import SerialInterface

from src.station.cli.arg_parser import parse_args
from src.station.cli.display import display_nodes, display_messages, display_telemetry
from src.station.utils.logger import configure_logger
from src.station.handlers.redis_handler import RedisHandler
from src.station.handlers.data_handler import MeshtasticDataHandler
from src.station.utils.constants import LoggingConst
from src.station.config.base_config import BaseStationConfig
from src.station.handlers.meshtastic_handler import MeshtasticHandler
from src.station.ui.terminal_ui import TerminalUI

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

async def setup_redis(args, station_config, logger) -> RedisHandler:
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

async def setup_meshtastic(args, redis_handler, logger) -> tuple:
    """Initialize Meshtastic interface and handler."""
    try:
        interface = SerialInterface(args.device)
        logger.debug(f"Connected to serial device: {args.device}")
        
        meshtastic_handler = MeshtasticHandler(
            redis_handler=redis_handler,
            interface=interface,
            logger=logger
        )
        await meshtastic_handler.initialize_connected_node()
        return interface, meshtastic_handler
    except FileNotFoundError:
        logger.error(f"Cannot connect to serial device {args.device}: Device not found")
        suggest_available_ports(logger)
        return None, None
    except Exception as e:
        logger.error(f"Cannot connect to serial device {args.device}: {e}")
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

async def monitor_mode(data_handler, meshtastic_handler, interface, redis_handler, logger):
    """Run in continuous monitoring mode with terminal UI."""
    terminal = TerminalUI(data_handler, logger)
    publisher_task = None
    
    try:
        # Start Redis message publisher
        publisher_task = asyncio.create_task(redis_handler.message_publisher())
        
        # Start terminal UI
        await terminal.run()
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Error in monitor mode: {e}")
    finally:
        if publisher_task:
            publisher_task.cancel()
            try:
                await publisher_task
            except asyncio.CancelledError:
                pass
        
        meshtastic_handler.cleanup()
        interface.close()
        await redis_handler.close()
        logger.info("Cleanup completed")

async def run_console(logger, interface, meshtastic_handler, redis_handler, data_handler):
    """Run in basic console mode."""
    publisher_task = asyncio.create_task(redis_handler.message_publisher())
    try:
        await display_nodes(data_handler, logger)
        await display_messages(data_handler, logger)
        logger.info("Listening for messages... Press Ctrl+C to exit")
        await publisher_task
    except KeyboardInterrupt:
        logger.info("Shutdown initiated...")
        publisher_task.cancel()
    finally:
        meshtastic_handler.cleanup()
        interface.close()
        await redis_handler.close()
        logger.info("Interface closed")

async def main():
    """Main application entry point."""
    args = parse_args()
    
    # Configure logging
    logger = configure_logger(
        name=__name__,
        log_levels=args.log_levels,
        use_threshold=args.threshold,
        log_file=None if args.no_file_logging else LoggingConst.DEFAULT_FILE,
        debugging=args.debugging
    )

    try:
        # Load configuration
        station_config = BaseStationConfig.load(path=args.config, logger=logger)
        if args.redis_host:
            station_config.redis.host = args.redis_host
        if args.redis_port:
            station_config.redis.port = args.redis_port

        # Initialize handlers
        redis_handler = await setup_redis(args, station_config, logger)
        if not redis_handler:
            return

        data_handler = MeshtasticDataHandler(redis_handler, logger=logger)
        redis_handler.set_data_handler(data_handler)

        # Handle cleanup if requested
        if await handle_cleanup(args, redis_handler, logger):
            return

        # Handle display-only modes
        if await handle_display(args, data_handler, redis_handler, logger):
            return

        # Initialize Meshtastic
        interface, meshtastic_handler = await setup_meshtastic(args, redis_handler, logger)
        if not interface or not meshtastic_handler:
            await redis_handler.close()
            return

        # Run in selected UI mode
        if args.ui == "curses":
            await monitor_mode(data_handler, meshtastic_handler, interface, redis_handler, logger)
        elif args.ui == "dearpygui":
            logger.error("DearPyGui interface not yet implemented")
            return 1
        else:  # "none" or basic console mode
            await run_console(logger, interface, meshtastic_handler, redis_handler, data_handler)

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
