# src/station/handlers/meshtastic_handler.py

import asyncio
import logging

class MeshtasticHandler:
    """
    Bridge between Meshtastic's sync callbacks and async Redis operations.
    MeshtasticHandler only needs to know about the message queue and logger.
    but nothing about the RedisHandler class.
    """

    def __init__(self, message_queue: asyncio.Queue, logger=None):
        self.message_queue = message_queue
        self.logger = logger or logging.getLogger(__name__)

    def on_text_message(self, packet, interface):
        self.logger.packet(f"on_text_message: {packet}")
        try:
            self.message_queue.put_nowait({
                "type": "text",
                "packet": packet
            })
        except Exception as e:
            self.logger.error(f"Error in text message callback: {e}", exc_info=True)

    def on_node_message(self, packet: dict, interface: any) -> None:
        """Callback for node messages."""
        self.logger.packet(f"on_node_message: {packet}")
        try:
            self.message_queue.put_nowait({
                "type": "node",
                "packet": packet
            })
        except Exception as e:
            self.logger.error(f"Error in node message callback: {e}", exc_info=True)

    def on_telemetry_message(self, packet: dict, interface: any) -> None:
        """Callback for telemetry messages."""
        self.logger.packet(f"on_telemetry_message: {packet}")
        try:
            self.message_queue.put_nowait({
                "type": "telemetry",
                "packet": packet
            })
        except Exception as e:
            self.logger.error(f"Error in telemetry callback: {e}", exc_info=True)        