import asyncio
import logging
import json
from typing import Optional
from src.station.handlers.redis_handler import RedisHandler
from src.station.utils.constants import RedisConst

class GuiRedisHandler(RedisHandler):
    
    def __init__(self, host: str = RedisConst.DEFAULT_HOST, port: int = RedisConst.DEFAULT_PORT, 
                 logger: Optional[logging.Logger] = None):
        super().__init__(host, port, logger)
        self.pubsub = self.client.pubsub()
        self.logger.debug("GUI Redis handler initialized")

    async def message_publisher(self):
        """Process messages, store in Redis, and publish GUI updates."""
        if self.data_handler is None:  # Ensure data_handler is set
            self.logger.critical("Meshtastic Data handler not set")
            raise ValueError("Meshtastic Data handler not set")

        self.logger.info("GUI message publisher started")
        while True:
            try:
                if self.message_queue.qsize() > 0:
                    message = await self.message_queue.get()

                    # Validate and process the message
                    try:
                        processed_message = await self.data_handler.process_packet(
                            message["packet"], message["type"]
                        )
                    except Exception as e:
                        self.logger.error(f"Error processing {message['type']} packet: {e}")
                        self.message_queue.task_done()
                        continue

                    # Store the processed message in Redis
                    await self._store_message_in_redis(message["type"], processed_message)

                    # Publish to the appropriate GUI channel
                    channel_map = {
                        "text": RedisConst.CHANNEL_TEXT,
                        "node": RedisConst.CHANNEL_NODE,
                        "telemetry": self._determine_telemetry_channel(processed_message),
                    }
                    channel = channel_map.get(message["type"])
                    if channel:
                        await self.publish(channel, processed_message)

                    self.message_queue.task_done()
                else:
                    await asyncio.sleep(RedisConst.DISPATCH_SLEEP)
            except Exception as e:
                self.logger.error(f"Error in GUI message publisher: {e}")

    async def _store_message_in_redis(self, msg_type, processed_message):
        """Store processed messages in Redis based on type."""
        try:
            if msg_type == "text":
                await self.store_message(json.dumps(processed_message))
            elif msg_type == "node":
                await self.store_node(json.dumps(processed_message))
            elif msg_type == "telemetry":
                telemetry = processed_message.get("decoded", {}).get("telemetry", {})
                if "deviceMetrics" in telemetry:
                    await self.store_device_telemetry(json.dumps(processed_message))
                elif "localStats" in telemetry:
                    await self.store_network_telemetry(json.dumps(processed_message))
                elif "environmentMetrics" in telemetry:
                    await self.store_environment_telemetry(json.dumps(processed_message))
        except Exception as e:
            self.logger.error(f"Failed to store {msg_type} message in Redis: {e}")

    def _determine_telemetry_channel(self, processed_message):
        """Determine the appropriate GUI channel for telemetry messages."""
        telemetry = processed_message.get("decoded", {}).get("telemetry", {})
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