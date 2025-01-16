# src/station/cli/arg_parser.py

import argparse
from typing import List
from src.station.utils.logger import get_available_levels
from src.station.utils.constants import DeviceConst, LoggingConst

def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Meshtastic Base Station Console",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --device /dev/ttyACM0                    # Use default INFO level
  %(prog)s --log INFO,PACKET                        # Show INFO and PACKET messages
  %(prog)s --log DEBUG --threshold                  # Show DEBUG and above
  %(prog)s --log PACKET,REDIS --no-file-logging     # Show only PACKET and REDIS, console only
  %(prog)s --monitor                                # Start monitoring mode
        """
    )

    _add_device_args(parser)
    _add_logging_args(parser)
    _add_mode_args(parser)
    _add_config_args(parser)
    _add_redis_args(parser)
    _add_cleanup_args(parser)
    _add_debug_args(parser)

    return parser

def _add_device_args(parser: argparse.ArgumentParser) -> None:
    """Add device-related arguments."""
    parser.add_argument(
        "--device",
        type=str,
        default=DeviceConst.DEFAULT_PORT_LINUX,
        help=f"Serial interface device (default: {DeviceConst.DEFAULT_PORT_LINUX})"
    )

def _add_logging_args(parser: argparse.ArgumentParser) -> None:
    """Add logging-related arguments."""
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

from src.station.utils.platform_utils import UIType, get_available_uis, get_default_ui

def _add_mode_args(parser: argparse.ArgumentParser) -> None:
    """Add operating mode arguments."""
    mode_group = parser.add_argument_group('Operating Modes')
    
    # Get available UI types for this platform
    available_uis = get_available_uis()
    default_ui = get_default_ui()
    
    # Create list of UI choices
    ui_choices = [ui.name.lower() for ui in available_uis]
    
    mode_group.add_argument(
        "--ui",
        choices=ui_choices,
        default=default_ui.name.lower(),
        help=f"Select UI mode (default: {default_ui.name.lower()})"
    )
    mode_group.add_argument(
        "--display-redis",
        action="store_true",
        help="Display Redis data and exit"
    )
    mode_group.add_argument(
        "--display-nodes",
        action="store_true",
        help="Display only node information and exit"
    )
    mode_group.add_argument(
        "--display-messages",
        action="store_true",
        help="Display only messages and exit"
    )
    mode_group.add_argument(
        "--display-telemetry",
        action="store_true",
        help="Display only telemetry data and exit"
    )

def _add_config_args(parser: argparse.ArgumentParser) -> None:
    """Add configuration-related arguments."""
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file"
    )

def _add_redis_args(parser: argparse.ArgumentParser) -> None:
    """Add Redis-related arguments."""
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

def _add_cleanup_args(parser: argparse.ArgumentParser) -> None:
    """Add cleanup-related arguments."""
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

def _add_debug_args(parser: argparse.ArgumentParser) -> None:
    """Add debugging-related arguments."""
    parser.add_argument(
        "--debugging",
        action="store_true",
        help="Print diagnostic debugging statements"
    )

def parse_args() -> argparse.Namespace:
    """Parse and process command line arguments."""
    parser = create_parser()
    args = parser.parse_args()
    args.log_levels = [level.strip() for level in args.log.split(",")]
    return args