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

- **Flexible UI Options:**
  - Basic console output
  - Terminal UI using curses
  - Optional graphical interface using DearPyGui
  - Real-time data visualization

- **Flexible Configuration:**
  - YAML-based configuration files
  - Environment variable support
  - Command-line overrides
  - Platform-aware defaults
  - Remote Redis connectivity

## Project Structure

```bash
meshtastic-base-station/
├── src/
│   └── station/
│       ├── __init__.py
│       ├── cli/                   # Command-line interface components
│       │   ├── __init__.py
│       │   ├── arg_parser.py     # Command line argument parsing
│       │   ├── display.py        # Console display formatting
│       │   └── commands.py       # Command implementations
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
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── base.py          # Abstract UI base class
│       │   ├── terminal_ui.py   # Curses-based UI
│       │   └── dearpygui_ui.py  # DearPyGui UI
│       └── utils/
│           ├── __init__.py
│           ├── constants.py  # Magic numbers & string defs
│           ├── logger.py     # Logging setup
│           ├── log_filter.py # Log filtering
│           └── validation.py # Type validation
├── tests/
│   ├── __init__.py
│   └── test_*.py files
├── examples/
│   ├── local.config.yaml        # Local Redis example
│   └── remote.config.yaml       # Remote Redis example
├── config.yaml                  # Default configuration
└── mesh_console.py             # Main entry point
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
meshtastic
protobuf
pypubsub
pyserial
redis
dearpygui  # Optional - for graphical interface
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
   # For graphical interface:
   pip install dearpygui
   ```

3. Start Redis:

   ```bash
   redis-server
   ```

## Usage

### Basic Operation

```bash
# Basic console output
python mesh_console.py

# Terminal UI (curses)
python mesh_console.py --ui curses

# Graphical interface (if DearPyGui is installed)
python mesh_console.py --ui dearpygui

# Use custom config
python mesh_console.py --config custom.yaml
```

### Command Line Options

```bash
usage: mesh_console.py [-h] [--config CONFIG] [--device DEVICE]
                      [--redis-host HOST] [--redis-port PORT]
                      [--log LOG] [--threshold] [--no-file-logging]
                      [--ui {none,curses,dearpygui}]
                      [--display-redis] [--display-nodes]
                      [--display-messages] [--display-telemetry]

options:
  -h, --help       show this help message and exit
  --config CONFIG  Path to configuration file
  --device DEVICE  Serial interface device
  --redis-host HOST Redis host (overrides config)
  --redis-port PORT Redis port (overrides config)
  --ui {none,curses,dearpygui}
                   Select UI mode (default: none)

Logging Options:
  --log LOG        Comma-separated list of log levels
  --threshold      Treat log level as threshold
  --no-file-logging
                   Disable logging to file

Display Options:
  --display-redis  Display Redis data and exit
  --display-nodes  Display only node information
  --display-messages
                   Display only messages
  --display-telemetry
                   Display only telemetry data

Other Options:
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

Monitor with graphical interface:

```bash
python mesh_console.py --ui dearpygui --log INFO
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

- **CLI System:**
  - `arg_parser.py`: Argument parsing and validation
  - `display.py`: Consistent output formatting
  - `commands.py`: Individual command implementations
  - Separation of concerns between parsing, display, and execution

- **UI System:**
  - Abstract base class defining UI interface
  - Console output for basic operation
  - Curses-based terminal UI
  - Optional DearPyGui graphical interface

- **Command Line Interface:**
  - Modular command structure
  - Argument parsing separated from command logic
  - Consistent display formatting
  - Composable command implementations

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
  6. UI updates

## Contributing

Contributions welcome! Submit issues or pull requests via GitHub.

## License

GNU General Public License v3.0 - see [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.html).

## Acknowledgments

- [Meshtastic Project](https://meshtastic.org)
- Contributors to the Meshtastic Python API  
  