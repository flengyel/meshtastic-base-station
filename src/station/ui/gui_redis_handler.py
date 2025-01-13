import asyncio
from src.station.handlers.redis_handler import RedisHandler
from src.station.utils.constants import RedisConst
import logging
from typing import Optional, List
import json

class GuiRedisHandler(RedisHandler):
    """Redis handler with GUI-specific pubsub functionality."""
    
    def __init__(self, host="localhost", port=6379, logger: Optional[logging.Logger] = None):
        super().__init__(host, port, logger)
        self.pubsub = self.client.pubsub()
        self.logger.debug("GUI Redis handler initialized")

    async def message_publisher(self):
        """Process messages and publish GUI updates."""
        try:
            self.logger.info("GUI message publisher started")
            while True:
                try:
                    if self.message_queue.qsize() > 0:
                        message = await self.message_queue.get()
                        msg_type = message["type"]
                        packet = message["packet"]
                        
                        # First store in Redis
                        if msg_type == "text":
                            await self.store_message(json.dumps(packet))
                            channel = RedisConst.CHANNEL_TEXT
                        elif msg_type == "node":
                            await self.store_node(json.dumps(packet))
                            channel = RedisConst.CHANNEL_NODE
                        elif msg_type == "telemetry":
                            telemetry = packet['decoded'].get('telemetry', {})
                            if 'deviceMetrics' in telemetry:
                                await self.store_device_telemetry(json.dumps(packet))
                                channel = RedisConst.CHANNEL_TELEMETRY_DEVICE
                            elif 'localStats' in telemetry:
                                await self.store_network_telemetry(json.dumps(packet))
                                channel = RedisConst.CHANNEL_TELEMETRY_NETWORK
                            elif 'environmentMetrics' in telemetry:
                                await self.store_environment_telemetry(json.dumps(packet))
                                channel = RedisConst.CHANNEL_TELEMETRY_ENVIRONMENT
                            else:
                                self.logger.warning(f"Unknown telemetry type: {packet}")
                                continue

                        # Then publish to Redis channel for GUI
                        await self.publish(channel, message)
                        self.message_queue.task_done()
                    else:
                        await asyncio.sleep(RedisConst.DISPATCH_SLEEP)
                        
                except Exception as e:
                    self.logger.error(f"Error publishing GUI message: {e}", exc_info=True)
                    
        except asyncio.CancelledError:
            self.logger.info("GUI message publisher shutting down")
            raise

    async def subscribe_gui(self, channels: List[str]):
        """Subscribe to Redis channels for GUI updates."""
        try:
            await self.pubsub.subscribe(*channels)
            self.logger.info(f"Subscribed to channels: {channels}")
        except Exception as e:
            self.logger.error(f"Error subscribing to channels: {e}")
            raise

    async def listen_gui(self):
        """Listen for messages on subscribed channels."""
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    yield message
        except Exception as e:
            self.logger.error(f"Error listening to Redis pubsub: {e}")
            raise

    async def publish(self, channel: str, message: dict):
        """Publish message to Redis channel."""
        try:
            await self.client.publish(channel, json.dumps(message))
            self.logger.debug(f"Published message to {channel}")
        except Exception as e:
            self.logger.error(f"Error publishing to {channel}: {e}")
            raise

    async def cleanup(self):
        """Clean up Redis pubsub and connection."""
        try:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
            await super().close()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")