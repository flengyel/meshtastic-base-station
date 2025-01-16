# src/station/cli/display.py

import logging
from datetime import datetime
from typing import Any, Dict, List
from src.station.utils.constants import DisplayConst

async def display_nodes(data_handler, logger: logging.Logger) -> None:
    """Display previously stored nodes in a formatted table."""
    print("\n=== Previously Saved Nodes ===")
    logger.debug("Retrieving formatted nodes...")
    nodes = await data_handler.get_formatted_nodes()
    logger.debug(f"Retrieved {len(nodes)} nodes")
    
    if not nodes:
        print("[No nodes found]")
        return

    # Calculate column widths
    timestamp_width = max(len("Timestamp"), max(len(node['timestamp']) for node in nodes))
    id_width = max(len("Node ID"), max(len(node['id']) for node in nodes))
    name_width = max(len("Name"), max(len(node['name']) for node in nodes))

    # Print header
    header = (f"{'Timestamp':<{timestamp_width}} | "
             f"{'Node ID':<{id_width}} | "
             f"{'Name':<{name_width}}")
    print(header)
    print("-" * len(header))

    # Print rows
    for node in sorted(nodes, key=lambda x: x['timestamp']):
        print(f"{node['timestamp']:<{timestamp_width}} | "
              f"{node['id']:<{id_width}} | "
              f"{node['name']:<{name_width}}")

async def display_messages(data_handler, logger: logging.Logger) -> None:
    """Display previously stored messages in a formatted table."""
    print("\n=== Previously Saved Messages ===")
    logger.debug("Retrieving formatted messages...")
    messages = await data_handler.get_formatted_messages()
    logger.debug(f"Retrieved {len(messages)} messages")

    if not messages:
        print("[No messages found]")
        return

    # Calculate column widths
    timestamp_width = max(len("Timestamp"), max(len(msg['timestamp']) for msg in messages))
    from_width = max(len("From"), max(len(msg['from']) for msg in messages))
    to_width = max(len("To"), max(len(msg['to']) for msg in messages))

    # Print header
    header = (f"{'Timestamp':<{timestamp_width}} | "
             f"{'From':<{from_width}} | "
             f"{'To':<{to_width}} | "
             f"Message")
    print(header)
    print("-" * len(header))

    # Print rows
    for msg in sorted(messages, key=lambda x: x['timestamp']):
        print(f"{msg['timestamp']:<{timestamp_width}} | "
              f"{msg['from']:<{from_width}} | "
              f"{msg['to']:<{to_width}} | "
              f"{msg['text']}")

async def display_telemetry(data_handler, logger: logging.Logger) -> None:
    """Display all types of telemetry data."""
    await _display_device_telemetry(data_handler, logger)
    await _display_network_telemetry(data_handler, logger)
    await _display_environment_telemetry(data_handler, logger)

async def _display_device_telemetry(data_handler, logger: logging.Logger) -> None:
    """Display device telemetry data."""
    print("\n=== Device Telemetry ===")
    device_telemetry = await data_handler.get_formatted_device_telemetry()
    
    if device_telemetry:
        # Calculate column widths
        timestamp_width = max(len("Timestamp"), 
                            max(len(t['timestamp']) for t in device_telemetry))
        id_width = max(len("Node ID"), 
                      max(len(t['from_id']) for t in device_telemetry))
        
        # Print header
        header = (f"{'Timestamp':<{timestamp_width}} | "
                 f"{'Node ID':<{id_width}} | "
                 f"{'Battery':<8} | "
                 f"{'Voltage':<8} | "
                 f"{'Ch Util':<8}")
        print(header)
        print("-" * len(header))
        
        for tel in sorted(device_telemetry, 
                         key=lambda x: x['timestamp'])[-DisplayConst.MAX_DEVICE_TELEMETRY:]:
            print(f"{tel['timestamp']:<{timestamp_width}} | "
                  f"{tel['from_id']:<{id_width}} | "
                  f"{tel['battery']:>7}% | "
                  f"{float(tel['voltage']):>7.2f}V | "
                  f"{float(tel['channel_util']):>7.2f}%")
    else:
        print("[No device telemetry found]")

async def _display_network_telemetry(data_handler, logger: logging.Logger) -> None:
    """Display network telemetry data."""
    print("\n=== Network Telemetry ===")
    network_telemetry = await data_handler.get_formatted_network_telemetry()
    
    if network_telemetry:
        timestamp_width = max(len("Timestamp"), 
                            max(len(t['timestamp']) for t in network_telemetry))
        id_width = max(len("Node ID"), 
                      max(len(t['from_id']) for t in network_telemetry))
        
        header = (f"{'Timestamp':<{timestamp_width}} | "
                 f"{'Node ID':<{id_width}} | "
                 f"{'Nodes':<12} | "
                 f"{'TX':<6} | "
                 f"{'RX':<6}")
        print(header)
        print("-" * len(header))
        
        for tel in sorted(network_telemetry, 
                         key=lambda x: x['timestamp'])[-DisplayConst.MAX_NETWORK_TELEMETRY:]:
            print(f"{tel['timestamp']:<{timestamp_width}} | "
                  f"{tel['from_id']:<{id_width}} | "
                  f"{tel['online_nodes']}/{tel['total_nodes']:>8} | "
                  f"{tel['packets_tx']:>5} | "
                  f"{tel['packets_rx']:>5}")
    else:
        print("[No network telemetry found]")

async def _display_environment_telemetry(data_handler, logger: logging.Logger) -> None:
    """Display environment telemetry data."""
    print("\n=== Environment Telemetry ===")
    env_telemetry = await data_handler.get_formatted_environment_telemetry()
    
    if env_telemetry:
        timestamp_width = max(len("Timestamp"), 
                            max(len(t['timestamp']) for t in env_telemetry))
        id_width = max(len("Node ID"), 
                      max(len(t['from_id']) for t in env_telemetry))
        
        header = (f"{'Timestamp':<{timestamp_width}} | "
                 f"{'Node ID':<{id_width}} | "
                 f"{'Temperature':<12} | "
                 f"{'Humidity':<8} | "
                 f"{'Pressure':<10}")
        print(header)
        print("-" * len(header))
        
        for tel in sorted(env_telemetry, key=lambda x: x['timestamp']):
            print(f"{tel['timestamp']:<{timestamp_width}} | "
                  f"{tel['from_id']:<{id_width}} | "
                  f"{tel['temperature']:<12} | "
                  f"{tel['humidity']:<8} | "
                  f"{tel['pressure']:<10}")
    else:
        print("[No environment telemetry found]")