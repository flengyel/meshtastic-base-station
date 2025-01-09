# log_lfilter.py
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
from typing import Union, List, Set

class LogLevelFilter(logging.Filter):
    """
    Flexible log filter that can handle single level, multiple levels, or level thresholds.
    """
    def __init__(self, levels: Union[int, List[int], Set[int]], threshold: bool = False):
        """
        Initialize the filter with specific levels or a threshold.

        :param levels: Single level or collection of levels to filter by
        :param threshold: If True, allow all levels >= min(levels)
        """
        super().__init__()
        self.levels = {levels} if isinstance(levels, int) else set(levels)
        self.threshold = threshold
        self._min_level = min(self.levels) if self.threshold else None

    def filter(self, record):
        """
        Filter log records based on level.

        :param record: The log record to check
        :return: True if the record should be logged
        """
        if self.threshold: # if threshold, show all above min
            return record.levelno >= self._min_level
        return record.levelno in self.levels # otherwise only those specified


