# base_config.py
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

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import os
import platform
import yaml
import logging
from src.station.utils.constants import (
    RedisConst, DeviceConst, LoggingConst, BaseStationConst
)

@dataclass
class RedisConfig:
    """Redis connection configuration."""
    host: str = RedisConst.DEFAULT_HOST
    port: int = RedisConst.DEFAULT_PORT
    password: Optional[str] = None
    db: int = RedisConst.DEFAULT_DB
    decode_responses: bool = RedisConst.DEFAULT_DECODE_RESPONSES

@dataclass
class DeviceConfig:
    """Meshtastic device configuration."""
    port: str = field(default_factory=lambda: DeviceConfig.default_port())
    baud_rate: int = DeviceConst.DEFAULT_BAUD_RATE
    timeout: float = DeviceConst.DEFAULT_TIMEOUT

    @staticmethod
    def default_port() -> str:
        system = platform.system().lower()
        if system == 'linux':
            return DeviceConst.DEFAULT_PORT_LINUX
        elif system == 'windows':
            return DeviceConst.DEFAULT_PORT_WINDOWS
        elif system == 'darwin':  # macOS
            return DeviceConst.DEFAULT_PORT_MAC 
        return DeviceConst.DEFAULT_PORT_LINUX

@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = LoggingConst.DEFAULT_LEVEL
    file: Optional[str] = LoggingConst.DEFAULT_FILE
    use_threshold: bool = LoggingConst.DEFAULT_USE_THRESHOLD
    format: str = LoggingConst.FILE_FORMAT
    debugging: bool = LoggingConst.DEFAULT_DEBUGGING

@dataclass
class UIConfig:
    """GUI configuration."""
    monospace_font: str = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    monospace_bold: str = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf'

@dataclass
class BaseStationConfig:
    """Main configuration class for the Meshtastic base station."""
    redis: RedisConfig = field(default_factory=RedisConfig)
    device: DeviceConfig = field(default_factory=DeviceConfig)
    log_cfg: LoggingConfig = field(default_factory=LoggingConfig)
    ui_cfg: UIConfig = field(default_factory=UIConfig) 
    data_retention_days: int = BaseStationConst.DEFAULT_DATA_RETENTION_DAYS
    environment: str = BaseStationConst.DEFAULT_ENVIRONMENT

    @classmethod
    def from_yaml(cls, path: str) -> "BaseStationConfig":
        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls.from_dict(config_dict)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "BaseStationConfig":
        redis_config = RedisConfig(**config_dict.get('redis', {}))
        device_config = DeviceConfig(**config_dict.get('device', {}))
        logging_config = LoggingConfig(**config_dict.get('logging', {}))
        ui_config = UIConfig(**config_dict.get('ui_cfg', {}))
        return cls(
            redis=redis_config,
            device=device_config,
            log_cfg=logging_config,
            ui_cfg=ui_config, 
            data_retention_days=config_dict.get('data_retention_days', BaseStationConst.DEFAULT_DATA_RETENTION_DAYS),
            environment=config_dict.get('environment', BaseStationConst.DEFAULT_ENVIRONMENT)
        )

    @classmethod
    def load(
        cls,
        path: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ) -> "BaseStationConfig":
        """
        Load configuration from 'path' or from default paths.
        Use a child logger if one is passed; otherwise use our module-level logger.
        """
        logger = cls._get_logger(logger)
        config = cls._load_from_path(path, logger) if path else cls._load_from_default_paths(logger)
        cls._apply_env_overrides(config)
        return config

    @staticmethod
    def _get_logger(logger: Optional[logging.Logger]) -> logging.Logger:
        if logger:
            return logger.getChild("BaseStationConfig")
        return logging.getLogger(__name__)

    @classmethod
    def _load_from_path(cls, path: str, logger: logging.Logger) -> "BaseStationConfig":
        custom_path = Path(path)
        if custom_path.exists():
            try:
                config = cls.from_yaml(str(custom_path))
                logger.info(f"Loaded configuration from {custom_path}")
                return config
            except Exception as e:
                logger.warning(f"Error loading config from {custom_path}: {e}")
        else:
            logger.warning(f"Specified config file {custom_path} not found; using defaults.")
        return cls()

    @classmethod
    def _load_from_default_paths(cls, logger: logging.Logger) -> "BaseStationConfig":
        for config_path in [Path(p) for p in BaseStationConst.CONFIG_PATHS]:
            if config_path.exists():
                try:
                    config = cls.from_yaml(str(config_path))
                    logger.info(f"Loaded configuration from {config_path}")
                    return config
                except Exception as e:
                    logger.warning(f"Error loading config from {config_path}: {e}")
        logger.info("Using default configuration")
        return cls()

    @classmethod
    def _apply_env_overrides(cls, config: "BaseStationConfig") -> None:
        if os.getenv('MESHTASTIC_REDIS_HOST'):
            config.redis.host = os.getenv('MESHTASTIC_REDIS_HOST')
        if os.getenv('MESHTASTIC_REDIS_PORT'):
            config.redis.port = int(os.getenv('MESHTASTIC_REDIS_PORT'))
        if os.getenv('MESHTASTIC_REDIS_PASSWORD'):
            config.redis.password = os.getenv('MESHTASTIC_REDIS_PASSWORD')
        if os.getenv('MESHTASTIC_DEVICE_PORT'):
            config.device.port = os.getenv('MESHTASTIC_DEVICE_PORT')
        if os.getenv('MESHTASTIC_LOG_LEVEL'):
            config.log_cfg.level = os.getenv('MESHTASTIC_LOG_LEVEL')

