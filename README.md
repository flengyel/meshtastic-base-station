# Meshtastic Base Station

A Python-based base station for Meshtastic devices that provides persistent storage of messages and node announcements using Redis. This project implements a lightweight, resource-efficient management system for Meshtastic networks, ensuring that even resource-constrained devices like Raspberry Pi can serve as reliable base stations.

## Features

- **Message Handling:** Receives and stores text messages sent through the network
- **Node Management:** Tracks node names and their associated station IDs
- **Persistent Storage:** Uses Redis for reliable storage of messages and node information
- **Flexible Logging:** 
  - Custom levels for packet and Redis operations
  - Multiple output formats and filtering options
  - Support for threshold or exact level matching
- **Resource Efficient:** Designed for reliable operation on Raspberry Pi and similar devices
- **Async Operation:** Uses asyncio for non-blocking operations and clean shutdown
- **Extensible Design:** Architecture supports future enhancements

## Prerequisites

### Hardware
- Meshtastic-compatible device with serial connection (e.g., LILYGO® T-Beam)
- Computer or Raspberry Pi running Linux (tested on Raspberry Pi 5)

### Software
- Python 3.8+
- Redis server
- Required Python packages:
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

3. Ensure Redis server is running:
   ```bash
   redis-server
   ```

## Usage

### Basic Operation

Start the base station with default settings:
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
  --log LOG        Comma-separated list of log levels to include
  --threshold      Treat log level as threshold
  --no-file-logging
                   Disable logging to file

Other Options:
  --display-redis  Display Redis data and exit
  --debugging      Print diagnostic debugging statements
```

### Example Commands

Show only packet data:
```bash
python mesh_console.py --log PACKET
```

Enable debug mode without file logging:
```bash
python mesh_console.py --log DEBUG --threshold --no-file-logging
```

Display stored data:
```bash
python mesh_console.py --display-redis --log INFO,REDIS
```

### Log Levels
- Standard levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Custom levels: PACKET (for mesh traffic), REDIS (for storage operations)

### Redis Data Structure

The base station uses the following Redis keys:

- **meshtastic:nodes**
  - Hash mapping station IDs to node names
  - Example: `HGET meshtastic:nodes !abcd1234`

- **meshtastic:nodes:timestamps**
  - Hash mapping station IDs to last seen timestamps
  - Example: `HGET meshtastic:nodes:timestamps !abcd1234`

- **meshtastic:messages**
  - List containing JSON-formatted messages with:
    - timestamp
    - station_id
    - message
    - to_id (recipient)

### Redis CLI Examples

View all nodes:
```bash
redis-cli HGETALL meshtastic:nodes
```

Delete specific node:
```bash
redis-cli HDEL meshtastic:nodes <station_id>
redis-cli HDEL meshtastic:nodes:timestamps <station_id>
```

## Architecture

The project consists of several key components:

- `mesh_console.py`: Main application entry point and CLI interface
- `redis_handler.py`: Minimal Redis storage operations
- `meshtastic_data_handler.py`: Processes Meshtastic packets and JSON conversion
- `logger.py`: Configurable logging system
- `log_level_filter.py`: Custom log filtering

### Data Flow

1. Meshtastic device sends messages/announcements
2. Callbacks capture and queue the packets
3. Redis dispatcher processes queued packets
4. MeshtasticDataHandler converts packets to JSON
5. RedisHandler stores JSON in Redis
6. Data persists for future retrieval

## Future Development

### Planned Features
- GUI interface with scrollable displays for nodes and messages
- RSSI (signal strength) monitoring and visualization
- Geographic position tracking and mapping
- Integration with web interfaces (e.g., Leaflet maps via Flask)
- Enhanced device configuration capabilities
- Extended node metrics (battery, position, etc.)

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

This project is licensed under the GNU General Public License v3.0 - see the [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.html) for details.

## Acknowledgments

- Meshtastic Project (https://meshtastic.org)
- Contributors to the Meshtastic Python API
