import asyncio
import logging
from typing import Optional
from src.station.handlers.redis_handler import RedisHandler
from src.station.utils.constants import RedisConst

class GuiRedisHandler(RedisHandler):
    def __init__(self, host: str = RedisConst.DEFAULT_HOST, port : int = RedisConst.DEFAULT_PORT, logger: Optional[logging.Logger] = None):
        super().__init__(host, port, logger)
        self.pubsub = self.client.pubsub()
        self.logger.debug("GUI Redis handler initialized")

    async def message_publisher(self):
        """Process messages, store in Redis, and publish GUI updates."""
        self.logger.info("GUI message publisher started")
        while True:
            try:
                if self.message_queue.qsize() > 0:
                    message = await self.message_queue.get()
                    await super().message_publisher()  # Call base message handling
                    # Publish to appropriate GUI channel
                    channel_map = {
                        "text": RedisConst.CHANNEL_TEXT,
                        "node": RedisConst.CHANNEL_NODE,
                        "telemetry": self._determine_telemetry_channel(message)
                    }
                    channel = channel_map.get(message["type"])
                    if channel:
                        await self.publish(channel, message)
                    self.message_queue.task_done()
                else:
                    await asyncio.sleep(RedisConst.DISPATCH_SLEEP)
            except Exception as e:
                self.logger.error(f"Error in GUI message publisher: {e}")

    def _determine_telemetry_channel(self, message):
        telemetry = message["packet"].get("decoded", {}).get("telemetry", {})
        if "deviceMetrics" in telemetry:
            return RedisConst.CHANNEL_TELEMETRY_DEVICE
        elif "localStats" in telemetry:
            return RedisConst.CHANNEL_TELEMETRY_NETWORK
        elif "environmentMetrics" in telemetry:
            return RedisConst.CHANNEL_TELEMETRY_ENVIRONMENT
        return None

    async def subscribe_gui(self, channels):
        try:
            await self.pubsub.subscribe(*channels)
            self.logger.info(f"Subscribed to channels: {channels}")
        except Exception as e:
            self.logger.error(f"Error subscribing to channels: {e}")
            raise

    async def listen_gui(self):
        try:
            async for message in self.pubsub.listen():
                if message['type'] == 'message':
                    yield message
        except Exception as e:
            self.logger.error(f"Error listening to Redis pubsub: {e}")
            raise

    async def cleanup(self):
        try:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
            await super().close()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")            