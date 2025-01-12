# src/station/handlers/meshtastic_handler.py

import asyncio
import logging
from src.station.utils.constants import RedisConst
from src.station.handlers.redis_handler import RedisHandler
from typing import Optional

class MeshtasticHandler:
    """Bridge between Meshtastic's sync callbacks and async Redis operations."""

    def __init__(self, redis_handler : RedisHandler, logger : Optional[logging.Logger] = None) -> None:
        self.redis_handler = redis_handler
        self.logger = logger or logging.getLogger(__name__)

    def on_text_message(self, packet: dict, interface: any) -> None:
        """Callback for text messages."""
        self.logger.packet(f"on_text_message: {packet}")
        try:
            asyncio.run_coroutine_threadsafe(
                self.redis_handler.publish(RedisConst.CHANNEL_TEXT, {
                    "type": "text",
                    "packet": packet
                }),
                asyncio.get_running_loop()
            )
        except Exception as e:
            self.logger.error(f"Error in text message callback: {e}", exc_info=True)

    def on_node_message(self, packet: dict, interface: any) -> None:
        """Callback for node messages."""
        self.logger.packet(f"on_node_message: {packet}")
        try:
            asyncio.run_coroutine_threadsafe(
                self.redis_handler.publish(RedisConst.CHANNEL_NODE, {
                    "type": "node",
                    "packet": packet
                }),
                asyncio.get_running_loop()
            )
        except Exception as e:
            self.logger.error(f"Error in node message callback: {e}", exc_info=True)

    def on_telemetry_message(self, packet: dict, interface: any) -> None:
        """Callback for telemetry messages."""
        self.logger.packet(f"on_telemetry_message: {packet}")
        try:
            # Determine telemetry type and publish to appropriate channel
            if 'deviceMetrics' in packet['decoded'].get('telemetry', {}):
                channel = RedisConst.CHANNEL_TELEMETRY_DEVICE
            elif 'localStats' in packet['decoded'].get('telemetry', {}):
                channel = RedisConst.CHANNEL_TELEMETRY_NETWORK
            elif 'environmentMetrics' in packet['decoded'].get('telemetry', {}):
                channel = RedisConst.CHANNEL_TELEMETRY_ENVIRONMENT
            else:
                self.logger.warning(f"Unknown telemetry type in packet: {packet}")
                return

            asyncio.run_coroutine_threadsafe(
                self.redis_handler.publish(channel, {
                    "type": "telemetry",
                    "packet": packet
                }),
                asyncio.get_running_loop()
            )
        except Exception as e:
            self.logger.error(f"Error in telemetry callback: {e}", exc_info=True)        