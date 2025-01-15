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
        self._tasks = []  # Store tasks for cleanup
        self.logger.debug("GUI Redis handler initialized")

    async def message_publisher(self):
        """Process messages and publish GUI updates."""
        if self.data_handler is None:
            self.logger.critical("Meshtastic Data handler not set")
            raise ValueError("Meshtastic Data handler not set")
        
        try:
            self.logger.info("GUI message publisher started")
            heartbeat_task = asyncio.create_task(self.heartbeat())
            self._tasks.append(heartbeat_task)
            
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
                    except Exception as e:
                        self.logger.error(f"Error processing message: {e}", exc_info=True)
                    finally:
                        self.message_queue.task_done()
                        
                except Exception as e:
                    self.logger.error(f"Error in message loop: {e}", exc_info=True)
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
        
    async def cleanup(self):
        """Clean up Redis connections."""
        try:
            self.logger.debug("Starting GUI cleanup")
            self._running = False
            await self.pubsub.unsubscribe()
            self.logger.debug("Unsubscribed from pubsub")
            await self.pubsub.close()
            self.logger.debug("Closed pubsub")
            await super().close()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def _create_serializable_packet(self, packet):
        """Create a JSON-serializable version of the packet."""
        self.logger.debug("Creating serializable packet")
        try:
            # Convert packet to dict if it's not already
            packet_dict = dict(packet) if not isinstance(packet, dict) else packet.copy()
        
            # Handle decoded field specially
            if 'decoded' in packet_dict:
                decoded = dict(packet_dict['decoded']) if not isinstance(packet_dict['decoded'], dict) else packet_dict['decoded'].copy()
            
                # Handle telemetry data
                if 'telemetry' in decoded:
                    telemetry = decoded['telemetry']
                    telemetry_dict = {}
                
                    # Extract deviceMetrics if present
                    if hasattr(telemetry, 'deviceMetrics') or 'deviceMetrics' in telemetry:
                        metrics = getattr(telemetry, 'deviceMetrics', telemetry.get('deviceMetrics', {}))
                        telemetry_dict['deviceMetrics'] = {
                            'batteryLevel': getattr(metrics, 'batteryLevel', metrics.get('batteryLevel')),
                            'voltage': float(getattr(metrics, 'voltage', metrics.get('voltage', 0))),
                            'channelUtilization': float(getattr(metrics, 'channelUtilization', metrics.get('channelUtilization', 0))),
                            'airUtilTx': float(getattr(metrics, 'airUtilTx', metrics.get('airUtilTx', 0))),
                            'uptimeSeconds': int(getattr(metrics, 'uptimeSeconds', metrics.get('uptimeSeconds', 0)))
                        }
                
                    # Extract localStats if present
                    if hasattr(telemetry, 'localStats') or 'localStats' in telemetry:
                        stats = getattr(telemetry, 'localStats', telemetry.get('localStats', {}))
                        telemetry_dict['localStats'] = {
                            'numOnlineNodes': int(getattr(stats, 'numOnlineNodes', stats.get('numOnlineNodes', 0))),
                            'numTotalNodes': int(getattr(stats, 'numTotalNodes', stats.get('numTotalNodes', 0))),
                            'numPacketsRx': int(getattr(stats, 'numPacketsRx', stats.get('numPacketsRx', 0))),
                            'numPacketsTx': int(getattr(stats, 'numPacketsTx', stats.get('numPacketsTx', 0))),
                            'channelUtilization': float(getattr(stats, 'channelUtilization', stats.get('channelUtilization', 0)))
                        }
                
                    # Extract environmentMetrics if present
                    if hasattr(telemetry, 'environmentMetrics') or 'environmentMetrics' in telemetry:
                        env = getattr(telemetry, 'environmentMetrics', telemetry.get('environmentMetrics', {}))
                        telemetry_dict['environmentMetrics'] = {
                            'temperature': float(getattr(env, 'temperature', env.get('temperature', 0))),
                            'relativeHumidity': float(getattr(env, 'relativeHumidity', env.get('relativeHumidity', 0))),
                            'barometricPressure': float(getattr(env, 'barometricPressure', env.get('barometricPressure', 0)))
                        }
                
                    # Add time if present
                    if hasattr(telemetry, 'time') or 'time' in telemetry:
                        telemetry_dict['time'] = getattr(telemetry, 'time', telemetry.get('time'))
                
                    decoded['telemetry'] = telemetry_dict
            
                # Handle text messages
                if 'text' in decoded:
                    decoded['text'] = str(decoded['text'])
            
                # Handle payload (convert bytes to string)
                if 'payload' in decoded:
                    if isinstance(decoded['payload'], bytes):
                        decoded['payload'] = str(decoded['payload'])
            
                packet_dict['decoded'] = decoded
        
            # Convert 'raw' field to string if present
            if 'raw' in packet_dict:
                packet_dict['raw'] = str(packet_dict['raw'])
            
            return packet_dict
            
        except Exception as e:
            self.logger.error(f"Error creating serializable packet: {e}", exc_info=True)
            return None   
    
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
            async for message in self.pubsub.listen():
                if not self._running:
                    self.logger.debug("Listener shutting down")
                    break
                
                self.logger.debug(f"Got message type: {message['type']}")
                if message['type'] == 'message':
                    self.logger.debug(f"Got data message: {str(message['data'])[:200]}...")
                    yield message
            
                # Let other tasks run
                await asyncio.sleep(0.1)
            
        except asyncio.CancelledError:
            self.logger.info("Message listener cancelled")
            raise
        except Exception as e:
            self.logger.error(f"Error in message listener: {e}", exc_info=True)
            raise
