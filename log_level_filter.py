# log_level_filter.py
#
# Copyright (C) 2025 Florian Lengyel WM2D
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

class LogLevelFilter(logging.Filter):
    """
    Filters to exclude logs other than the specified level.
    """
    def __init__(self, level):
        """
        Initialize the filter with a specific log level.

        :param level: The numeric log level to filter by.
        """
        super().__init__()
        self.level = level

    def filter(self, record):
        """
        Filter out logs unequal to the specified level.

        :param record: The log record to check.
        :return: True iff the record's level equals the filter's level.
        """
        return record.levelno == self.level

