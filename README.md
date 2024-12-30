# Meshtastic Console

Meshtastic Console (`mesh_console.py`) is a Python console program to display the text and user messages received by a Meshtastic device connected to the console interface through a serial connection. 


## Features

- **Monitor Node Activity:** Displays nodes in the network along with timestamps of their last activity.
- **Message Handling:** Receives and displays text messages sent through the network.
- **Node Management:** Keeps track of node names and their associated station IDs, synchronizing changes.
- **Redis Integration:** Stores and retrieves messages and node information using Redis for persistence.
- **Queue-Based Updates:** Uses an asyncio queue to manage updates to Redis, ensuring non-blocking operations.
- **Connected Node Initialization:** Automatically initializes the console with the station ID of the connected node.
- **Extensibility:** Designed with features like Kivy interfaces, RSSI indicators, and mapping capabilities in mind for future development.

## Requirements

### Hardware
- A Meshtastic-compatible device with a serial connection.

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
The program uses Redis hashes to store node and message information:

- **`meshtastic:nodes`**:
  - **Key**: Station ID
  - **Value**: Node name

- **`meshtastic:nodes:timestamps`**:
  - **Key**: Station ID
  - **Value**: Timestamp of the last node update

- **`meshtastic:messages`**:
  - A list containing serialized message JSON objects with:
    - `timestamp`
    - `station_id`
    - `message`

### Interacting with Redis
To view all stored keys:
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
- **Kivy Interfaces**: Scrollable displays for nodes and messages.
- **RSSI Indicators**: Track signal strength.
- **Mapping Capabilities**: Correlate node activity and messages with geographic positions.
- **Device Configuration**: Extend the console to send messages and configure devices.

## Contributing
Contributions are welcome! Please submit issues or pull requests on the GitHub repository.

## License
This project is licensed under the MIT License.

