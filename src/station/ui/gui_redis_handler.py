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
        self._tasks = []  # Store tasks for cleanup
        self.gui_queue = asyncio.Queue()  # Queue for GUI messages
        self.logger.debug("GUI Redis handler initialized")

    async def heartbeat(self):
        """Maintain Redis connection and monitor queues."""
        self.logger.info("Starting GUI Redis heartbeat")
        try:
            while self._running:
                try:
                    await self.client.ping()
                    self.logger.debug("Heartbeat ping successful")
                    msg_qsize = self.message_queue.qsize()
                    gui_qsize = self.gui_queue.qsize()
                    if msg_qsize > 0 or gui_qsize > 0:
                        self.logger.debug(f"Queue sizes - Message: {msg_qsize}, GUI: {gui_qsize}")
                    await asyncio.sleep(1.0)
                except Exception as e:
                    self.logger.error(f"Heartbeat error: {e}")
                    await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            self.logger.info("Heartbeat shutting down")
            raise

    async def message_publisher(self):
        """Process messages and enqueue for GUI."""
        if self.data_handler is None:
            self.logger.critical("Meshtastic Data handler not set")
            raise ValueError("Meshtastic Data handler not set")
    
        try:
            self.logger.info("GUI message publisher started")
            heartbeat_task = asyncio.create_task(self.heartbeat())
            self._tasks.append(heartbeat_task)
            
            while self._running:
                try:
                    # Get message from main queue
                    message = await self.message_queue.get()
                    try:
                        self.logger.debug(f"Processing message of type: {message['type']}")
                        
                        # Let data handler process and store the packet
                        await self.data_handler.process_packet(
                            message["packet"], message["type"]
                        )
                        
                        # Prepare message for GUI
                        clean_packet = self._create_serializable_packet(message["packet"])
                        if clean_packet:
                            # Put processed message on GUI queue - use put_nowait to avoid blocking
                            self.gui_queue.put_nowait({
                                "type": message["type"],
                                "packet": clean_packet,
                                "timestamp": datetime.now().isoformat()
                            })
                            self.logger.debug("Successfully queued message for GUI")
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

    async def cleanup(self):
        """Clean up tasks and connections."""
        try:
            self.logger.debug("Starting GUI cleanup")
            self._running = False
            for task in self._tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
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
    
