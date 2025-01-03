# logger.py
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

import logging

PACKET_LEVEL = 15
REDIS_LEVEL  = 17

def add_custom_log_levels():
    """
    Add custom log levels PACKET and REDIS to the logging module.
    """
    logging.addLevelName(PACKET_LEVEL, "PACKET")
    logging.addLevelName(REDIS_LEVEL, "REDIS")

    def packet(self, message, *args, **kwargs):
        if self.isEnabledFor(PACKET_LEVEL):
            self._log(PACKET_LEVEL, message, args, **kwargs)

    def redis(self, message, *args, **kwargs):
        if self.isEnabledFor(REDIS_LEVEL):
            self._log(REDIS_LEVEL, message, args, **kwargs)

    logging.Logger.packet = packet
    logging.Logger.redis = redis

# This must run before configure_logger() is called
add_custom_log_levels()

def resolve_log_level(level_name):
    """
    Resolve log level name to a numeric value, including custom levels.

    :param level_name: Log level name (e.g., 'INFO', 'REDIS').
    :return: Numeric log level.
    """
    level_name = level_name.upper()
    custom_levels = {"PACKET": PACKET_LEVEL, "REDIS": REDIS_LEVEL}
    return custom_levels.get(level_name, getattr(logging, level_name, logging.INFO))

def configure_logger(name, log_level=logging.INFO, debugging=False):
    if debugging:
    	print(f"Initializing logger: {name}")
    	print(f"Received log level: {log_level} ({logging.getLevelName(log_level)})")

    logger = logging.getLogger(name)

    if logger.hasHandlers():
        if debugging:
            print("Logger already configured. Returning existing logger.")
        return logger

    # Set the logger level
    logger.setLevel(log_level)
    logger.propagate = False  # Prevent message propagation

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
    console_handler.setFormatter(console_formatter)

    # File handler for detailed logs
    file_handler = logging.FileHandler('meshtastic.log', mode='a')
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s')
    file_handler.setFormatter(file_formatter)

    # Attach handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


    if debugging:
        for handler in logger.handlers:
            print(f"Handler level: {handler.level} ({logging.getLevelName(handler.level)})")
        print(f"Logger configured with level: {logger.level} ({logging.getLevelName(logger.level)})")

    return logger

