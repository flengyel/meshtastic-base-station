# Meshtastic Base Station

A Python-based base station for Meshtastic devices providing persistent storage and real-time processing of network traffic. Built on modern async Python and Redis, it implements a lightweight, resource-efficient management system suitable for 24/7 operation on devices like Raspberry Pi.

## Features

- **Asynchronous Architecture:**
  - Built on asyncio for non-blocking I/O and efficient resource usage
  - Clean separation between network I/O, processing, and storage
  - Graceful shutdown handling with proper resource cleanup
  
- **Message and Node Handling:**
  - Real-time processing of network messages
  - Node tracking with status updates
  - Efficient queuing system for packet processing

- **Telemetry Processing:**
  - Device metrics (battery, voltage, channel utilization)
  - Network statistics (node counts, packet rates)
  - Environmental data (temperature, humidity, pressure)

- **Persistent Redis Storage:**
  - Optimized JSON storage for all packet types
  - Separate data streams for messages, nodes, and telemetry
  - Atomic operations for data consistency

- **Flexible Logging:**
  - Custom levels: PACKET, DATA, REDIS
  - Multiple output formats and filtering
  - Threshold or exact level matching

## Prerequisites

### Hardware
- Meshtastic-compatible device with serial connection
- Computer or Raspberry Pi running Linux (tested on Raspberry Pi 5)

### Software
- Python 3.8+
- Redis server
- Required packages:
  ```
  redis-py-async
  meshtastic
  pyserial
  pypubsub
  protobuf
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/meshtastic-base-station.git
   cd meshtastic-base-station
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start Redis:
   ```bash
   redis-server
   ```

## Usage

### Basic Operation

```bash
python mesh_console.py
```

### Command Line Options

```
usage: mesh_console.py [-h] [--device DEVICE] [--log LOG] [--threshold]
                      [--no-file-logging] [--display-redis] [--debugging]

options:
  -h, --help       show this help message and exit
  --device DEVICE  Serial interface device (default: /dev/ttyACM0)

Logging Options:
  --log LOG        Comma-separated list of log levels
  --threshold      Treat log level as threshold
  --no-file-logging
                   Disable logging to file

Other Options:
  --display-redis  Display Redis data and exit
  --debugging      Print diagnostic statements
```

### Example Commands

View packet data:
```bash
python mesh_console.py --log PACKET
```

Monitor telemetry:
```bash
python mesh_console.py --log DATA
```

Display stored data:
```bash
python mesh_console.py --display-redis
```

### Log Levels
- Standard: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Custom: PACKET (mesh traffic), DATA (telemetry), REDIS (storage)

### Redis Data Structure

```
meshtastic:messages               # Text messages
meshtastic:nodes                 # Node information
meshtastic:telemetry:device      # Device metrics
meshtastic:telemetry:network     # Network statistics
meshtastic:telemetry:environment # Environmental readings
```

Messages and telemetry are stored as JSON, preserving complete packet information for analysis and replay.

### Redis CLI Examples

View recent telemetry:
```bash
redis-cli LRANGE meshtastic:telemetry:device 0 10
```

Check node status:
```bash
redis-cli HGETALL meshtastic:nodes
```

## Architecture

The project uses modern Python async patterns and Redis for efficient data handling:

- **Async Core:**
  - `mesh_console.py`: Entry point and async event loop
  - `redis_handler.py`: Async Redis operations
  - `meshtastic_data_handler.py`: Packet processing

- **Data Flow:**
  1. Async packet reception
  2. Non-blocking queue processing
  3. JSON conversion
  4. Atomic Redis storage
  5. Persistent data retrieval

## Future Development

- Kivy-based GUI interface
- RSSI visualization
- Geographic tracking
- Web interface integration
- Enhanced configuration
- Extended metrics

## Contributing

Contributions welcome! Submit issues or pull requests via GitHub.

## License

GNU General Public License v3.0 - see [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

## Acknowledgments

- Meshtastic Project (https://meshtastic.org)
- Contributors to the Meshtastic Python API
