# src/station/ui/base.py

from abc import ABC, abstractmethod
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import asyncio

class MeshtasticUI(ABC):
    """Abstract base class defining the interface for Meshtastic UIs."""

    def __init__(self, data_handler, logger: Optional[logging.Logger] = None):
        """
        Initialize the UI.

        Args:
            data_handler: Handler for Meshtastic data operations
            logger: Optional logger instance
        """
        self.data_handler = data_handler
        self.logger = logger or logging.getLogger(__name__)
        self.running = False

    @abstractmethod
    async def start(self) -> None:
        """Initialize and start the UI."""
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        """Clean up and stop the UI."""
        raise NotImplementedError

    @abstractmethod
    async def update(self) -> None:
        """Update the UI with latest data."""
        raise NotImplementedError

    @abstractmethod
    def handle_input(self) -> None:
        """Handle user input."""
        raise NotImplementedError

    @abstractmethod
    async def refresh_nodes(self, nodes: List[Dict[str, Any]]) -> None:
        """
        Refresh the nodes display.

        Args:
            nodes: List of node data dictionaries
        """
        raise NotImplementedError

    @abstractmethod
    async def refresh_messages(self, messages: List[Dict[str, Any]]) -> None:
        """
        Refresh the messages display.

        Args:
            messages: List of message data dictionaries
        """
        raise NotImplementedError

    @abstractmethod
    async def refresh_device_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """
        Refresh the device telemetry display.

        Args:
            telemetry: List of device telemetry data dictionaries
        """
        raise NotImplementedError

    @abstractmethod
    async def refresh_network_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """
        Refresh the network telemetry display.

        Args:
            telemetry: List of network telemetry data dictionaries
        """
        raise NotImplementedError

    @abstractmethod
    async def refresh_environment_telemetry(self, telemetry: List[Dict[str, Any]]) -> None:
        """
        Refresh the environment telemetry display.

        Args:
            telemetry: List of environment telemetry data dictionaries
        """
        raise NotImplementedError

    @abstractmethod
    async def show_error(self, message: str) -> None:
        """
        Display an error message.

        Args:
            message: Error message to display
        """
        raise NotImplementedError

    @abstractmethod
    async def show_status(self, message: str) -> None:
        """
        Display a status message.

        Args:
            message: Status message to display
        """
        raise NotImplementedError

    async def run(self) -> None:
        """Main UI loop."""
        try:
            await self.start()
            self.running = True

            while self.running:
                try:
                    self.handle_input()
                    await self.update()
                    await asyncio.sleep(0.1)  # Prevent high CPU usage
                except Exception as e:
                    await self.show_error(f"Error in UI loop: {e}")
                    self.logger.error(f"Error in UI loop: {e}", exc_info=True)

        except Exception as e:
            self.logger.error(f"Error running UI: {e}", exc_info=True)
        finally:
            await self.stop()
            self.running = False

    async def load_initial_data(self) -> None:
        """Load and display initial data."""
        try:
            nodes = await self.data_handler.get_formatted_nodes()
            await self.refresh_nodes(nodes)

            messages = await self.data_handler.get_formatted_messages()
            await self.refresh_messages(messages)

            device_telemetry = await self.data_handler.get_formatted_device_telemetry()
            await self.refresh_device_telemetry(device_telemetry)

            network_telemetry = await self.data_handler.get_formatted_network_telemetry()
            await self.refresh_network_telemetry(network_telemetry)

            env_telemetry = await self.data_handler.get_formatted_environment_telemetry()
            await self.refresh_environment_telemetry(env_telemetry)

        except Exception as e:
            await self.show_error(f"Error loading initial data: {e}")
            self.logger.error(f"Error loading initial data: {e}", exc_info=True)