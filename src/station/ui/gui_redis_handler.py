import asyncio
import logging
import json
from datetime import datetime
from typing import Optional
from src.station.handlers.redis_handler import RedisHandler
from src.station.utils.constants import RedisConst

class GuiRedisHandler(RedisHandler):
    
    def __init__(self, 
                 host: str = RedisConst.DEFAULT_HOST, 
                 port: int = RedisConst.DEFAULT_PORT, 
                 logger: Optional[logging.Logger] = None):
        super().__init__(host, port, logger)
        self.pubsub = self.client.pubsub()
        self.logger.debug("GUI Redis handler initialized")

    async def message_publisher(self):
        """Process messages, store in Redis, and publish GUI updates."""
        if self.data_handler is None:
            self.logger.critical("Meshtastic Data handler not set")
            raise ValueError("Meshtastic Data handler not set")
        self.logger.info("GUI message publisher started")
    
        while True:
            try:
                self.logger.debug("Checking message queue...")
                if self.message_queue.qsize() > 0:
                    message = await self.message_queue.get()
                    try:
                        self.logger.debug(f"Processing message of type: {message['type']}")
                        await self.data_handler.process_packet(
                            message["packet"], message["type"]
                        )
                        clean_packet = self._create_serializable_packet(message["packet"])
                        channel = self._get_channel_for_message(message["type"])
                    
                        if channel:
                            self.logger.debug(f"Publishing to channel: {channel}")
                            await self.client.publish(channel, json.dumps({
                                "type": message["type"],
                                "packet": clean_packet,
                                "timestamp": datetime.now().isoformat()
                            }))
                            self.logger.debug("Successfully published to Redis")
                    finally:
                        self.message_queue.task_done()
                else:
                    await asyncio.sleep(RedisConst.DISPATCH_SLEEP)
            except Exception as e:
                self.logger.error(f"Error in message publisher: {e}", exc_info=True)
                # Continue the loop even if there's an error

    def _create_serializable_packet(self, packet):
        """Create a JSON-serializable version of the packet."""
        self.logger.debug("Creating serializable packet")
        clean_packet = packet.copy()
        if 'decoded' in clean_packet:
            decoded = clean_packet['decoded']
            if 'telemetry' in decoded:
                telemetry = decoded['telemetry']
                telemetry_dict = {
                    'time': telemetry.get('time'),
                    'deviceMetrics': {
                        'batteryLevel': telemetry.get('deviceMetrics', {}).get('batteryLevel'),
                        'voltage': telemetry.get('deviceMetrics', {}).get('voltage'),
                        'channelUtilization': telemetry.get('deviceMetrics', {}).get('channelUtilization'),
                        'airUtilTx': telemetry.get('deviceMetrics', {}).get('airUtilTx'),
                        'uptimeSeconds': telemetry.get('deviceMetrics', {}).get('uptimeSeconds')
                    }
                }
                decoded['telemetry'] = telemetry_dict
            if isinstance(decoded['payload'], bytes):
                decoded['payload'] = str(decoded['payload'])
        self.logger.debug("Packet cleaned for serialization")
        return clean_packet

    def _get_channel_for_message(self, msg_type: str) -> Optional[str]:
        """Get the appropriate Redis channel for a message type."""
        channel_map = {
            "text": RedisConst.CHANNEL_TEXT,
            "node": RedisConst.CHANNEL_NODE,
            "telemetry": RedisConst.CHANNEL_TELEMETRY_DEVICE,
        }
        channel = channel_map.get(msg_type)
        self.logger.debug(f"Channel for message type {msg_type}: {channel}")
        return channel
    
    async def subscribe_gui(self, channels):
        """Subscribe to GUI update channels."""
        try:
            self.logger.debug(f"Attempting to subscribe to channels: {channels}")
            await self.pubsub.subscribe(*channels)
            self.logger.info(f"Successfully subscribed to channels: {channels}")
        except Exception as e:
            self.logger.error(f"Error subscribing to channels: {e}")
            raise

    async def listen_gui(self):
        """Listen for GUI update messages."""
        try:
            self.logger.debug("Starting GUI message listener")
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    self.logger.debug(f"Received pubsub message: {str(message['data'])[:200]}...")
                    yield message
        except Exception as e:
            self.logger.error(f"Error listening to Redis pubsub: {e}")
            raise

    async def cleanup(self):
        """Clean up Redis connections."""
        try:
            self.logger.debug("Starting cleanup")
            await self.pubsub.unsubscribe()
            self.logger.debug("Unsubscribed from pubsub")
            await self.pubsub.close()
            self.logger.debug("Closed pubsub")
            await super().close()
            self.logger.debug("Cleanup complete")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")