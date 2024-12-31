# Meshtastic Console

Meshtastic Console (`mesh_console.py`) is a Python program to interface with Meshtastic devices through a serial connection. It implements monitoring, managing, and interacting with nodes in a Meshtastic mesh network. 

## Features

Node Activity Monitoring: Shows network nodes and their last activity timestamps.

- **Message Handling:** Receives and displays text messages sent through the network.

- **Node Management:** Keeps track of node names and their associated station IDs, synchronizing changes.

- **Redis integration:** Provides persistence and scalability by storing and retrieving messages and node information.

- **Asynchronous Updates:** Uses an asyncio queue to manage updates to Redis, ensuring non-blocking operations.

- **Connected Node Initialization:** The program queries the Meshtastic API for the station ID of the connected node.

- **Extensibility:** Designed with features like Kivy interfaces, RSSI indicators, and mapping capabilities in mind for future development.

## Features Overview

This project implements lightweight, resource-efficient management of Meshtastic networks, ensuring that even resource-constrained devices like Raspberry Pi will serve as reliable base stations.

## Requirements

### Hardware

You will need a Meshtastic-compatible device that has a serial connection.

### Software

- Python 3.8+

- Redis

- Required Python Libraries:

  - asyncio

  - pubsub

  - meshtastic

  - redis

  - json

Install dependencies with:

```bash

pip install -r requirements.txt

```

## Usage

### Running the Console

```bash

python mesh_console.py

```

### Redis Keys and Structure

A Redis backend database of time-stamped node and message data provides persistence and scalability. The database keeps data across sessions for protection against system outages, to facilitate system maintenance, and to keep a detailed network history. 

- **`meshtastic:nodes`**:

  - **Key**: Station ID.

  - **Value**: Node name.

- **`meshtastic:nodes:timestamps`**:

  - **Key**: Station ID.

  - **Value**: Timestamp.

- **`meshtastic:messages`**:

  - A list containing serialized message JSON objects with:

    - `timestamp`

    - `station_id`

    - `message`

### Interacting with Redis

To view the stored keys:

```bash

redis-cli KEYS *

```

To view nodes:

```bash

redis-cli HGETALL meshtastic:nodes

```

To delete a specific node:

```bash

redis-cli HDEL meshtastic:nodes <field>

redis-cli HDEL meshtastic:nodes:timestamps <field>

```

## Future Development

- **Prioritized Enhancements**:
  - **Kivy Interfaces**: Scrollable displays for nodes and messages.
  - **RSSI Indicators**: Track signal strength.
  - **Mapping Capabilities**: Correlate node activity and messages with geographic positions.

- **Advanced Node Insights**:
  - Extend node data to include battery metrics and geographic position.
  - Display geographic and signal data via a Leaflet map served by a Flask web server.

- **Device Configuration**: 
- Enhance the console to send messages and reconfigure devices.

## Contributing

Contributions are welcome! Please submit issues or pull requests on the GitHub repository.

## License

Project licensed under the GNU General Public License v3.0. For more details, see [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.html).


