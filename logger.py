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

PACKET_LEVEL = 15  # Custom level between DEBUG and INFO

def configure_logging(log_level="INFO"):
    """
    Configure logging globally and set up the custom 'PACKET' log level.
    """
    if not hasattr(logging, "PACKET"):
        logging.addLevelName(PACKET_LEVEL, "PACKET")

        def packet(self, message, *args, **kwargs):
            if self.isEnabledFor(PACKET_LEVEL):
                self._log(PACKET_LEVEL, message, args, **kwargs)

        logging.Logger.packet = packet

    formatter_with_timestamp = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    formatter_without_timestamp = logging.Formatter("%(levelname)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter_without_timestamp)

    file_handler = logging.FileHandler("meshtastic.log", mode="a")
    file_handler.setFormatter(formatter_with_timestamp)

    # Convert log_level to numeric if it's a custom level
    if log_level.upper() == "PACKET":
        level = PACKET_LEVEL
    else:
        level = getattr(logging, log_level.upper(), logging.INFO)

    console_handler.setLevel(level)
    file_handler.setLevel(level)

    root_logger = logging.getLogger()  # Configure the root logger
    root_logger.setLevel(level)  # This ensures PACKET is properly applied
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Log configuration details
    root_logger.info(f"Configured logging level: {log_level}")
    root_logger.info(f"Effective logger level: {root_logger.getEffectiveLevel()}")


def get_logger(module_name):
    """
    Create or retrieve a logger for a specific module.
    """
    return logging.getLogger(module_name)

