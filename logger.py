# logger.py
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

import logging
from typing import Union, List, Optional

# Custom log levels 
# PACKET will show REDIS but not conversely
PACKET_LEVEL = 15
DATA_LEVEL   = 16
REDIS_LEVEL  = 17

# Map level names to values
CUSTOM_LEVELS = {
    "PACKET": PACKET_LEVEL,
    "DATA": DATA_LEVEL,
    "REDIS": REDIS_LEVEL
}

def add_custom_log_levels():
    """Add custom log levels PACKET and REDIS to the logging module."""
    for name, level in CUSTOM_LEVELS.items():
        logging.addLevelName(level, name)

    def packet(self, message, *args, **kwargs):
        if self.isEnabledFor(PACKET_LEVEL):
            self._log(PACKET_LEVEL, message, args, **kwargs)
    
    def data(self, message, *args, **kwargs):
        if self.isEnabledFor(DATA_LEVEL):
            self._log(DATA_LEVEL, message, args, **kwargs)

    def redis(self, message, *args, **kwargs):
        if self.isEnabledFor(REDIS_LEVEL):
            self._log(REDIS_LEVEL, message, args, **kwargs)

    logging.Logger.packet = packet
    logging.Logger.data   = data
    logging.Logger.redis = redis

# Add custom levels before they're used
add_custom_log_levels()

def get_available_levels():
    """Get all available log level names including custom levels."""
    standard_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    return standard_levels + list(CUSTOM_LEVELS.keys())

def resolve_log_levels(level_names: Union[str, List[str]]) -> List[int]:
    """
    Resolve one or more log level names to their numeric values.
    
    :param level_names: Single level name or list of names
    :return: List of numeric log levels
    """
    if isinstance(level_names, str):
        level_names = [level_names]
    
    resolved = []
    for name in level_names:
        name = name.upper()
        if name in CUSTOM_LEVELS:
            resolved.append(CUSTOM_LEVELS[name])
        else:
            try:
                resolved.append(getattr(logging, name))
            except AttributeError:
                raise ValueError(f"Invalid log level: {name}")
    
    return resolved

def configure_logger(
    name: str,
    log_levels: Union[str, List[str]],
    use_threshold: bool = False,
    log_file: Optional[str] = 'meshtastic.log',
    debugging: bool = False
) -> logging.Logger:
    """
    Configure a logger with console and optional file output.
    
    :param name: Logger name
    :param log_levels: Level name(s) to include
    :param use_threshold: If True, use minimum level as threshold
    :param log_file: Log file path, or None to disable file logging
    :param debugging: Enable debug output about logger configuration
    :return: Configured logger
    """
    if debugging:
        print(f"Initializing logger: {name}")
        print(f"Log levels: {log_levels}")
        print(f"Using threshold: {use_threshold}")

    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        if debugging:
            print("Logger already configured. Returning existing logger.")
        return logger

    # Resolve numeric levels
    numeric_levels = resolve_log_levels(log_levels)
    base_level = min(numeric_levels)

    # Set the logger's base level
    logger.setLevel(base_level)
    logger.propagate = False

    # Create filter
    from log_level_filter import LogLevelFilter
    log_filter = LogLevelFilter(numeric_levels, threshold=use_threshold)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(base_level)
    console_formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(log_filter)
    logger.addHandler(console_handler)

    # File handler (if enabled)
    if log_file:
        file_handler = logging.FileHandler(log_file, mode='a')
        file_handler.setLevel(base_level)
        file_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(log_filter)
        logger.addHandler(file_handler)

    if debugging:
        print(f"Logger configured with levels: {[logging.getLevelName(lvl) for lvl in numeric_levels]}")
        print(f"Base level: {logging.getLevelName(base_level)}")
        print(f"Using threshold: {use_threshold}")

    return logger

