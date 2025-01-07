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
  - Support for remote Redis servers

- **Flexible Configuration:**
  - YAML-based configuration files
  - Environment variable support
  - Command-line overrides
  - Platform-aware defaults
  - Remote Redis connectivity

- **Flexible Logging:**
  - Custom levels: PACKET, DATA, REDIS
  - Multiple output formats and filtering
  - Threshold or exact level matching

## Project Structure

```bash
meshtastic-base-station/
├── src/
│   └── station/ 
│       ├── __init__.py
│       ├── config/               # Configuration management
│       │   ├── __init__.py
│       │   └── base_config.py    # Core configuration classes
│       ├── handlers/
│       │   ├── __init__.py
│       │   ├── redis_handler.py  # Redis interface
│       │   └── data_handler.py   # Data processing
│       ├── types/
│       │   ├── __init__.py
│       │   └── meshtastic_types.py  # Type definitions
│       └── utils/
│           ├── __init__.py
│           ├── logger.py         # Logging setup
│           ├── log_filter.py     # Log filtering
│           └── validation.py     # Type validation
├── tests/
│   ├── __init__.py
│   └── test_*.py files
├── config.yaml                   # Default configuration
└── mesh_console.py              # Main entry point
```

## Prerequisites

### Hardware

- Meshtastic-compatible device with serial connection
- Computer or Raspberry Pi running Linux (tested on Raspberry Pi 5)
- Optional: Separate Redis server for remote storage

### Software

- Python 3.8+
- Redis server
- Required packages:

```python
redis-py-async
meshtastic
pyserial
pypubsub
protobuf
pyyaml    # For configuration
```

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/flengyel/meshtastic-base-station.git
   cd meshtastic-base-station
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create configuration (optional):

   ```bash
   cp config.yaml.example config.yaml
   # Edit config.yaml with your settings
   ```

4. Start Redis:

   ```bash
   redis-server
   ```

## Configuration

### Configuration File (config.yaml)

```yaml
# Environment (development, testing, production)
environment: development

# Redis configuration
redis:
  host: localhost      # or remote host like pironman5.local
  port: 6379
  password: null       # Set if using authentication
  db: 0

# Device configuration
device:
  port: /dev/ttyACM0  # Linux default
  # port: COM3        # Windows example
  baud_rate: 115200
  timeout: 1.0

# Logging configuration
logging:
  level: INFO
  file: meshtastic.log
  use_threshold: false
  debugging: false
```

### Environment Variables

```bash
export MESHTASTIC_REDIS_HOST=pironman5.local
export MESHTASTIC_DEVICE_PORT=COM3
export MESHTASTIC_LOG_LEVEL=INFO
```

## Usage

### Basic Operation

```bash
python mesh_console.py                      # Use default config
python mesh_console.py --config custom.yaml # Use custom config
```

### Command Line Options

```bash
usage: mesh_console.py [-h] [--config CONFIG] [--device DEVICE] 
                      [--redis-host HOST] [--redis-port PORT]
                      [--log LOG] [--threshold] [--no-file-logging]
                      [--display-redis] [--debugging]

options:
  -h, --help       show this help message and exit
  --config CONFIG  Path to configuration file
  --device DEVICE  Serial interface device (overrides config)
  --redis-host HOST Redis host (overrides config)
  --redis-port PORT Redis port (overrides config)

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

View packet data with remote Redis:

```bash
python mesh_console.py --redis-host pironman5.local --log PACKET
```

Monitor telemetry on Windows:

```bash
python mesh_console.py --device COM3 --log DATA
```

Display stored data:

```bash
python mesh_console.py --display-redis
```

### Log Levels

- Standard: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Custom: PACKET (mesh traffic), DATA (telemetry), REDIS (storage)

### Redis Data Structure

```python
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
redis-cli -h pironman5.local LRANGE meshtastic:telemetry:device 0 10
```

Check node status:

```bash
redis-cli -h pironman5.local HGETALL meshtastic:nodes
```

## Architecture

The project uses modern Python async patterns and Redis for efficient data handling:

- **Configuration Management:**
  - YAML-based configuration
  - Environment variable support
  - Command-line argument processing
  - Platform-specific defaults

- **Async Core:**
  - `mesh_console.py`: Entry point and async event loop
  - `redis_handler.py`: Async Redis operations
  - `data_handler.py`: Packet processing

- **Type System:**
  - TypedDict definitions for all packets
  - Runtime type validation
  - Comprehensive error handling

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
- Data retention policies
- Health monitoring system

## Contributing

Contributions welcome! Submit issues or pull requests via GitHub.

## License

GNU General Public License v3.0 - see [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

## Acknowledgments

- [Meshtastic Project](https://meshtastic.org)
- Contributors to the Meshtastic Python API
