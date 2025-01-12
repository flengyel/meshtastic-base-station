# src/station/ui/gui_redis_handler.py
import asyncio
from src.station.handlers.redis_handler import RedisHandler
from src.station.utils.constants import RedisConst
import logging
from typing import Optional

class GuiRedisHandler(RedisHandler):
    """Redis handler with GUI-specific pubsub functionality."""
    
    def __init__(self, host="localhost", port=6379, logger: Optional[logging.Logger] = None):
        super().__init__(host, port, logger)
        self.logger.debug("GUI Redis handler initialized")

    async def message_publisher(self):
        """Publishes messages and emits GUI updates."""
        try:
            self.logger.info("GUI message publisher task started")
            while True:
                try:
                    if self.message_queue.qsize() > 0:
                        message = await self.message_queue.get()
                        msg_type = message["type"]
                        
                        # First publish to type-specific channel
                        if msg_type == "text":
                            channel = RedisConst.CHANNEL_TEXT
                        elif msg_type == "node":
                            channel = RedisConst.CHANNEL_NODE
                        elif msg_type == "telemetry":
                            packet = message["packet"]
                            telemetry = packet['decoded'].get('telemetry', {})
                            if 'deviceMetrics' in telemetry:
                                channel = RedisConst.CHANNEL_TELEMETRY_DEVICE
                            elif 'localStats' in telemetry:
                                channel = RedisConst.CHANNEL_TELEMETRY_NETWORK
                            elif 'environmentMetrics' in telemetry:
                                channel = RedisConst.CHANNEL_TELEMETRY_ENVIRONMENT
                            else:
                                self.logger.warning(f"Unknown telemetry type: {packet}")
                                continue
                        
                        await self.publish(channel, message)
                        # Also publish to processed channel for GUI updates
                        await self.publish(RedisConst.CHANNEL_PROCESSED, message)
                        self.message_queue.task_done()
                    else:
                        await asyncio.sleep(RedisConst.DISPATCH_SLEEP)
                        
                except Exception as e:
                    self.logger.error(f"Error publishing GUI message: {e}", exc_info=True)
                    
        except asyncio.CancelledError:
            self.logger.info("GUI message publisher shutting down")
            raise
        