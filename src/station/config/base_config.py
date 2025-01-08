import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import os
import platform
import yaml

@dataclass
class RedisConfig:
    """Redis connection configuration."""
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    decode_responses: bool = True

@dataclass
class DeviceConfig:
    """Meshtastic device configuration."""
    port: str = field(default_factory=lambda: DeviceConfig.default_port())
    baud_rate: int = 115200
    timeout: float = 1.0

    @staticmethod
    def default_port() -> str:
        system = platform.system().lower()
        if system == 'linux':
            return '/dev/ttyACM0'
        elif system == 'windows':
            return 'COM1'
        elif system == 'darwin':  # macOS
            return '/dev/tty.usbmodem1'
        return '/dev/ttyACM0'

@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: Optional[str] = "meshtastic.log"
    use_threshold: bool = False
    format: str = "%(asctime)s %(levelname)s:%(name)s:%(message)s"
    debugging: bool = False

@dataclass
class BaseStationConfig:
    """Main configuration class for the Meshtastic base station."""
    redis: RedisConfig = field(default_factory=RedisConfig)
    device: DeviceConfig = field(default_factory=DeviceConfig)
    log_cfg: LoggingConfig = field(default_factory=LoggingConfig)
    data_retention_days: int = 30
    environment: str = "development"

    @classmethod
    def from_yaml(cls, path: str) -> 'BaseStationConfig':
        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)
        return cls.from_dict(config_dict)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BaseStationConfig':
        redis_config = RedisConfig(**config_dict.get('redis', {}))
        device_config = DeviceConfig(**config_dict.get('device', {}))
        logging_config = LoggingConfig(**config_dict.get('logging', {}))
        return cls(
            redis=redis_config,
            device=device_config,
            log_cfg=logging_config,
            data_retention_days=config_dict.get('data_retention_days', 30),
            environment=config_dict.get('environment', 'development')
        )

    @classmethod
    def load(
        cls,
        path: Optional[str] = None,
        logger: Optional[logging.Logger] = None
    ) -> 'BaseStationConfig':
        """
        Load configuration from 'path' or from default paths.
        Use a child logger if one is passed; otherwise use our module-level logger.
        """
        # If a logger is provided, nest logs under '...BaseStationConfig'
        if logger:
            logger = logger.getChild("BaseStationConfig")
        else:
            logger = logging.getLogger(__name__)

        if path:
            custom_path = Path(path)
            if custom_path.exists():
                try:
                    config = cls.from_yaml(str(custom_path))
                    logger.info(f"Loaded configuration from {custom_path}")
                except Exception as e:
                    logger.warning(f"Error loading config from {custom_path}: {e}")
                    config = cls()
            else:
                logger.warning(f"Specified config file {custom_path} not found; using defaults.")
                config = cls()
        else:
            # Default search logic
            config = None
            for config_path in [
                Path.cwd() / 'config.yaml',
                Path.home() / '.config' / 'meshtastic' / 'config.yaml',
                Path('/etc/meshtastic/config.yaml'),
            ]:
                if config_path.exists():
                    try:
                        config = cls.from_yaml(str(config_path))
                        logger.info(f"Loaded configuration from {config_path}")
                        break
                    except Exception as e:
                        logger.warning(f"Error loading config from {config_path}: {e}")
            if config is None:
                config = cls()
                logger.info("Using default configuration")

        # Environment variable overrides
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

        return config

