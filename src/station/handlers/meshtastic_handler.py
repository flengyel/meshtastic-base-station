# src/station/handlers/meshtastic_handler.py

import asyncio
import logging

class MeshtasticHandler:
    """
    Bridge between Meshtastic's sync callbacks and async processing.
    Only responsible for queuing messages for async processing.
    """

    def __init__(self, message_queue: asyncio.Queue, logger=None):
        self.message_queue = message_queue
        self.logger = logger or logging.getLogger(__name__)

    def on_text_message(self, packet, interface):
        """Queue text message for async processing."""
        self.logger.packet(f"on_text_message: {packet}")
        try:
            self.message_queue.put_nowait({
                "type": "text",
                "packet": packet
            })
        except Exception as e:
            self.logger.error(f"Error queueing text message: {e}", exc_info=True)

    def on_node_message(self, packet, interface):
        """Queue node message for async processing."""
        self.logger.packet(f"on_node_message: {packet}")
        try:
            self.message_queue.put_nowait({
                "type": "node",
                "packet": packet
            })
        except Exception as e:
            self.logger.error(f"Error queueing node message: {e}", exc_info=True)

    def on_telemetry_message(self, packet, interface):
        """Queue telemetry message for async processing."""
        self.logger.packet(f"on_telemetry_message: {packet}")
        try:
            self.message_queue.put_nowait({
                "type": "telemetry",
                "packet": packet
            })
        except Exception as e:
            self.logger.error(f"Error queueing telemetry message: {e}", exc_info=True)