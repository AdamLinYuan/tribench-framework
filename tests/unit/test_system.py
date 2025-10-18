"""Unit tests for core System abstraction."""

import pytest
from tribench.core.system import System


class MockSystem(System):
    """Mock implementation of System for testing."""

    def setup(self):
        """Mock setup."""
        pass

    def start(self):
        """Mock start."""
        self._is_running = True

    def stop(self):
        """Mock stop."""
        self._is_running = False

    def teardown(self):
        """Mock teardown."""
        pass

    def status(self):
        """Mock status."""
        return {"running": self._is_running}


@pytest.mark.unit
class TestSystem:
    """Tests for System abstraction."""

    def test_system_initialization(self, sample_system_config):
        """Test system can be initialized with config."""
        system = MockSystem("test-system", sample_system_config)
        assert system.name == "test-system"
        assert system.config == sample_system_config
        assert not system.is_running

    def test_system_start_stop(self, sample_system_config):
        """Test system can be started and stopped."""
        system = MockSystem("test-system", sample_system_config)

        # Initially not running
        assert not system.is_running

        # Start system
        system.start()
        assert system.is_running

        # Stop system
        system.stop()
        assert not system.is_running

    def test_system_status(self, sample_system_config):
        """Test system status reporting."""
        system = MockSystem("test-system", sample_system_config)

        status = system.status()
        assert "running" in status
        assert not status["running"]

        system.start()
        status = system.status()
        assert status["running"]
