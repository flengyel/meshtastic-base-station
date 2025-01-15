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
                await self._process_message_queue()
            except Exception as e:
                self.logger.error(f"Error in GUI message publisher: {e}")

    async def _process_message_queue(self):
        if self.message_queue.qsize() > 0:
            message = await self.message_queue.get()
            await self._process_message(message)
            self.message_queue.task_done()
        else:
            await asyncio.sleep(RedisConst.DISPATCH_SLEEP)

    async def _process_message(self, message):
        try:
            await self.data_handler.process_packet(
                message["packet"], message["type"]
            )
            clean_packet = self._create_serializable_packet(message["packet"])
            channel = self._get_channel_for_message(message["type"])
            if channel:
                await self.client.publish(channel, json.dumps({
                    "type": message["type"],
                    "packet": clean_packet,
                    "timestamp": datetime.now().isoformat()
                }))
        except Exception as e:
            self.logger.error(f"Error processing {message['type']} packet {message['packet']}: {e}")

    def _create_serializable_packet(self, packet):
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
        return clean_packet

    def _get_channel_for_message(self, msg_type: str) -> Optional[str]:
        """Get the appropriate Redis channel for a message type."""
        channel_map = {
            "text": RedisConst.CHANNEL_TEXT,
            "node": RedisConst.CHANNEL_NODE,
            "telemetry": RedisConst.CHANNEL_TELEMETRY_DEVICE,
        }
        return channel_map.get(msg_type)
    
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