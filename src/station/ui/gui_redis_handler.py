# src/station/ui/gui_redis_handler.py

from src.station.handlers.redis_handler import RedisHandler
from pubsub import pub
import asyncio
from src.station.utils.constants import RedisConst

class GuiRedisHandler(RedisHandler):
    """Redis handler that publishes updates for GUI consumption."""
    
    async def redis_dispatcher(self, data_handler):
        """Process Redis updates and publish for GUI."""
        try:
            self.logger.info("Redis dispatcher task started.")
            while True:
                try:
                    if self.redis_queue.qsize() > 0:
                        update = await self.redis_queue.get()
                        self.logger.debug(f"Processing update type: {update['type']}")
                        await data_handler.process_packet(update["packet"], update["type"])
                        # Publish processed update for GUI
                        pub.sendMessage("meshtastic.processed", update=update)
                        self.redis_queue.task_done()
                    else:
                        await asyncio.sleep(RedisConst.DISPATCH_SLEEP)
                except Exception as e:
                    self.logger.error(f"Error in dispatcher: {e}", exc_info=True)
                    self.redis_queue.task_done()
        except asyncio.CancelledError:
            self.logger.info("Dispatcher received cancellation signal")
            raise