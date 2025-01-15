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
        
        try:
            self.logger.info("GUI message publisher started")
            # Start heartbeat coroutine
            heartbeat_task = asyncio.create_task(self.heartbeat())
            # is the heartbeat task running?
            self.logger.debug(f"Heartbeat task started with ID: {id(heartbeat_task)}")

            while self._running:
                try:
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
                        
                except Exception as e:
                    self.logger.error(f"Error processing message: {e}", exc_info=True)
                    continue
                    
        except asyncio.CancelledError:
            self.logger.info("GUI message publisher shutting down")
            self._running = False
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
            raise

    def _create_serializable_packet(self, packet):
        """Create a JSON-serializable version of the packet."""
        self.logger.debug("Creating serializable packet")
        try:
            # Convert packet to dict if it's not already
            packet_dict = dict(packet) if not isinstance(packet, dict) else packet.copy()
            
            # Handle decoded field specially
            if 'decoded' in packet_dict:
                decoded = dict(packet_dict['decoded']) if not isinstance(packet_dict['decoded'], dict) else packet_dict['decoded'].copy()
                
                # Handle payload
                if 'payload' in decoded:
                    if isinstance(decoded['payload'], bytes):
                        decoded['payload'] = str(decoded['payload'])
                
                # Handle telemetry
                if 'telemetry' in decoded:
                    telemetry = decoded['telemetry']
                    if not isinstance(telemetry, dict):
                        telemetry = dict(telemetry)
                    
                    # Convert all telemetry values to basic Python types
                    if 'deviceMetrics' in telemetry:
                        telemetry['deviceMetrics'] = dict(telemetry['deviceMetrics'])
                    if 'localStats' in telemetry:
                        telemetry['localStats'] = dict(telemetry['localStats'])
                    if 'environmentMetrics' in telemetry:
                        telemetry['environmentMetrics'] = dict(telemetry['environmentMetrics'])
                    
                    decoded['telemetry'] = telemetry
                
                packet_dict['decoded'] = decoded
            
            # Convert 'raw' field to string if present
            if 'raw' in packet_dict:
                packet_dict['raw'] = str(packet_dict['raw'])
                
            return packet_dict
            
        except Exception as e:
            self.logger.error(f"Error creating serializable packet: {e}", exc_info=True)
            raise

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
            # Add debug to see what's happening with subscription
            subscription = await self.pubsub.subscribe(*channels)
            self.logger.debug(f"Subscribe returned: {subscription}")
            self.logger.info(f"Successfully subscribed to channels: {channels}")
        except Exception as e:
            self.logger.error(f"Error subscribing to channels: {e}")
            raise

    async def listen_gui(self):
        """Listen for GUI update messages."""
        try:
            self.logger.debug("Starting GUI message listener")
            self.logger.debug("About to enter pubsub.listen() loop")
            async for message in self.pubsub.listen():
                self.logger.debug(f"In pubsub.listen() loop, got message type: {message['type']}")
                if message['type'] == 'message':
                    self.logger.debug(f"Got data message: {str(message['data'])[:200]}...")
                    yield message
                await asyncio.sleep(0)  # Your sleep is good to keep
        except Exception as e:
            self.logger.error(f"Error listening to Redis pubsub: {e}", exc_info=True)
            raise

    async def cleanup(self):
        """Clean up Redis connections."""
        try:
            self.logger.debug("Starting GUI cleanup")
            self._running = False  # Stop heartbeat and message processing
            await self.pubsub.unsubscribe()
            self.logger.debug("Unsubscribed from pubsub")
            await self.pubsub.close()
            self.logger.debug("Closed pubsub")
            # Don't call super().close() here since we handle it ourselves
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")