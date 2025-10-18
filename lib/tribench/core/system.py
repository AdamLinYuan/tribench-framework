"""System abstraction for managing benchmark systems."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class System(ABC):
    """
    Abstract base class for system components in the benchmarking framework.

    A System represents a component like Trino, PostgreSQL, MinIO, etc.
    that needs to be set up, started, stopped, and torn down as part of
    benchmark experiments.
    """

    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize a System.

        Args:
            name: Unique identifier for this system instance
            config: Configuration dictionary for the system
        """
        self.name = name
        self.config = config
        self._is_running = False

    @abstractmethod
    def setup(self) -> None:
        """
        Set up the system (download binaries, create directories, etc.).

        This is called once before the system is used for the first time.
        """
        pass

    @abstractmethod
    def start(self) -> None:
        """
        Start the system and wait for it to be ready.

        Should include health checks to ensure the system is operational.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the system gracefully.

        Should ensure all resources are properly released.
        """
        pass

    @abstractmethod
    def teardown(self) -> None:
        """
        Tear down the system (remove files, clean up resources).

        This is called when the system is no longer needed.
        """
        pass

    @abstractmethod
    def status(self) -> Dict[str, Any]:
        """
        Get the current status of the system.

        Returns:
            Dictionary containing status information (running, health, etc.)
        """
        pass

    @property
    def is_running(self) -> bool:
        """Check if the system is currently running."""
        return self._is_running
