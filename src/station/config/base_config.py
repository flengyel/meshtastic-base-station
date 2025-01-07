from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import os
import platform
import yaml
import logging

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
        """Determine default port based on platform."""
        system = platform.system().lower()
        if system == 'linux':
            return '/dev/ttyACM0'
        elif system == 'windows':
            return 'COM1'
        elif system == 'darwin':  # macOS
            return '/dev/tty.usbmodem1'
        else:
            return '/dev/ttyACM0'  # Default to Linux

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
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    data_retention_days: int = 30
    environment: str = "development"

    @classmethod
    def from_yaml(cls, path: str) -> 'BaseStationConfig':
        """Load configuration from YAML file."""
        with open(path, 'r') as f:
            config_dict = yaml.safe_load(f)
            return cls.from_dict(config_dict)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'BaseStationConfig':
        """Create configuration from dictionary."""
        redis_config = RedisConfig(**config_dict.get('redis', {}))
        device_config = DeviceConfig(**config_dict.get('device', {}))
        logging_config = LoggingConfig(**config_dict.get('logging', {}))
        
        return cls(
            redis=redis_config,
            device=device_config,
            logging=logging_config,
            data_retention_days=config_dict.get('data_retention_days', 30),
            environment=config_dict.get('environment', 'development')
        )

    @classmethod
    def load(cls) -> 'BaseStationConfig':
        """
        Load configuration from environment variables or default config file.
        Environment variables take precedence over config file.
        """
        # Default config locations
        config_locations = [
            Path.cwd() / 'config.yaml',
            Path.home() / '.config' / 'meshtastic' / 'config.yaml',
            Path('/etc/meshtastic/config.yaml')
        ]

        # Try loading from config file
        config = None
        for config_path in config_locations:
            if config_path.exists():
                try:
                    config = cls.from_yaml(str(config_path))
                    logging.info(f"Loaded configuration from {config_path}")
                    break
                except Exception as e:
                    logging.warning(f"Error loading config from {config_path}: {e}")

        # If no config file found, use defaults
        if config is None:
            config = cls()
            logging.info("Using default configuration")

        # Override with environment variables
        if os.getenv('MESHTASTIC_REDIS_HOST'):
            config.redis.host = os.getenv('MESHTASTIC_REDIS_HOST')
        if os.getenv('MESHTASTIC_REDIS_PORT'):
            config.redis.port = int(os.getenv('MESHTASTIC_REDIS_PORT'))
        if os.getenv('MESHTASTIC_REDIS_PASSWORD'):
            config.redis.password = os.getenv('MESHTASTIC_REDIS_PASSWORD')
        if os.getenv('MESHTASTIC_DEVICE_PORT'):
            config.device.port = os.getenv('MESHTASTIC_DEVICE_PORT')
        if os.getenv('MESHTASTIC_LOG_LEVEL'):
            config.logging.level = os.getenv('MESHTASTIC_LOG_LEVEL')

        return config