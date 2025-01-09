import argparse
import asyncio
from pubsub import pub
from meshtastic.serial_interface import SerialInterface
import serial.tools.list_ports
from src.station.utils.logger import configure_logger, get_available_levels
from src.station.handlers.redis_handler import RedisHandler
from src.station.handlers.data_handler import MeshtasticDataHandler
from src.station.utils.constants import RedisConst, DisplayConst, DeviceConst, LoggingConst
from src.station.config.base_config import BaseStationConfig

# Initialize asyncio queue for Redis updates (preserve existing queue)
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
  %(prog)s --gui                                    # Start in GUI mode
        """
    )
    
    # Keep all existing arguments
    parser.add_argument(
        "--device",
        type=str,
        default=DeviceConst.DEFAULT_PORT_LINUX,        
        help=f"Serial interface device (default: {DeviceConst.DEFAULT_PORT_LINUX})"
    )
    
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
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )
    
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
    
    # Add GUI mode option
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Start in GUI mode using Kivy interface"
    )
    
    args = parser.parse_args()
    args.log_levels = [level.strip() for level in args.log.split(",")]
    
    return args

# Keep all existing callback functions unchanged
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

                try:
                    update = await asyncio.wait_for(redis_update_queue.get(), timeout=RedisConst.QUEUE_TIMEOUT)
                    logger.debug(f"Received update type: {update['type']}")
                    
                    await data_handler.process_packet(update["packet"], update["type"])
                    redis_update_queue.task_done()
                except asyncio.TimeoutError:
                    logger.debug("Dispatcher heartbeat - no updates")
                    await asyncio.sleep(RedisConst.HEARTBEAT_INTERVAL)
                    continue
                    
            except Exception as e:
                logger.error(f"Error in dispatcher: {e}", exc_info=True)
                redis_update_queue.task_done()
                await asyncio.sleep(RedisConst.ERROR_SLEEP)
                
    except asyncio.CancelledError:
        logger.info("Dispatcher received cancellation signal")
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
        raise

async def main():
    """Main function to set up the Meshtastic listener."""
    args = parse_arguments()
    
    # Set up logging (keep existing configuration)
    global logger
    logger = configure_logger(
        name=__name__,
        log_levels=args.log_levels,
        use_threshold=args.threshold,
        log_file=None if args.no_file_logging else LoggingConst.DEFAULT_FILE,
        debugging=args.debugging
    )

    # Load config
    config = None
    if args.config:
        config = BaseStationConfig.load(path=args.config, logger=logger)
    else:
        config = BaseStationConfig.load(logger=logger)
        logger.debug(f"Loaded default config from known locations")

    # Override Redis settings if provided in arguments
    if args.redis_host:
        config.redis.host = args.redis_host
    if args.redis_port:
        config.redis.port = args.redis_port

    # Initialize Redis handler
    try:
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

    if args.display_redis:
        logger.info("Displaying Redis data ...")
        await display_stored_data(data_handler)
        await redis_handler.close()
        return

    if args.gui:
        try:
            from src.station.ui.meshtastic_app import MeshtasticBaseApp
            app = MeshtasticBaseApp(
                redis_handler=redis_handler,
                data_handler=data_handler,
                redis_queue=redis_update_queue,
                logger=logger,
                config=config
            )
            # Subscribe to message topics (needed for GUI too)
            pub.subscribe(on_text_message, "meshtastic.receive.text")
            pub.subscribe(on_node_message, "meshtastic.receive.user")
            pub.subscribe(on_telemetry_message, "meshtastic.receive.telemetry")
            
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
        # Original CLI mode
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
                await dispatcher_task
            except asyncio.CancelledError:
                pass
        finally:
            interface.close()
            await redis_handler.close()
            logger.info("Interface closed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Program terminated.")