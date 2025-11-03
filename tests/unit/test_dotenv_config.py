"""Unit tests for environment-based configuration management."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from tribench.utils.config import ConfigurationLoader, get_config_or_env


class TestDotenvIntegration:
    """Test environment variable loading from .env files."""
    
    def test_env_file_loading(self, tmp_path):
        """Test that .env file is loaded on initialization."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value\nANOTHER_VAR=another_value")
        
        # Create minimal config structure
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('tribench { systems { } }')
        
        # Mock dotenv loading
        with patch('tribench.utils.config.load_dotenv') as mock_load:
            loader = ConfigurationLoader(root_path=tmp_path)
            
            # Verify load_dotenv was called with correct path
            mock_load.assert_called_once()
            call_args = mock_load.call_args
            assert call_args[0][0] == env_file
            assert call_args[1].get('override') is False
    
    def test_env_precedence_over_dotenv(self, tmp_path, monkeypatch):
        """Test that system environment variables override .env file."""
        # Set system environment variable
        monkeypatch.setenv("TEST_VAR", "from_system")
        
        # Create .env with different value
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=from_dotenv")
        
        # Create minimal config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('tribench { systems { } }')
        
        # System env should win (override=False in load_dotenv)
        loader = ConfigurationLoader(root_path=tmp_path)
        assert os.getenv("TEST_VAR") == "from_system"
    
    def test_dotenv_used_when_no_system_env(self, tmp_path, monkeypatch):
        """Test that .env values are used when system env not set."""
        # Ensure no system env variable
        monkeypatch.delenv("TEST_VAR", raising=False)
        
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=from_dotenv")
        
        # Create minimal config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('tribench { systems { } }')
        
        # Load environment
        with patch('tribench.utils.config.load_dotenv') as mock_load:
            # Simulate dotenv setting the variable
            def side_effect(*args, **kwargs):
                os.environ["TEST_VAR"] = "from_dotenv"
            mock_load.side_effect = side_effect
            
            loader = ConfigurationLoader(root_path=tmp_path)
            assert os.getenv("TEST_VAR") == "from_dotenv"
    
    def test_no_env_file_fallback(self, tmp_path):
        """Test that framework works without .env file."""
        # Don't create .env file
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('tribench { systems { } }')
        
        # Should not raise error
        loader = ConfigurationLoader(root_path=tmp_path)
        assert loader is not None
    
    def test_get_env_helper(self, tmp_path, monkeypatch):
        """Test get_env helper method."""
        monkeypatch.setenv("EXISTING_VAR", "existing_value")
        
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('tribench { systems { } }')
        
        loader = ConfigurationLoader(root_path=tmp_path)
        
        # Test existing variable
        assert loader.get_env("EXISTING_VAR") == "existing_value"
        
        # Test non-existing variable with default
        assert loader.get_env("NONEXISTENT_VAR", "default") == "default"
        
        # Test non-existing variable without default
        assert loader.get_env("NONEXISTENT_VAR") is None
    
    def test_disable_env_loading(self, tmp_path):
        """Test that env loading can be disabled."""
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_VAR=test_value")
        
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('tribench { systems { } }')
        
        # Create loader with load_env=False
        with patch('tribench.utils.config.load_dotenv') as mock_load:
            loader = ConfigurationLoader(root_path=tmp_path, load_env=False)
            mock_load.assert_not_called()


class TestGetConfigOrEnv:
    """Test get_config_or_env helper function."""
    
    def test_config_value_has_priority(self, monkeypatch):
        """Test that config value takes priority over environment."""
        from pyhocon import ConfigFactory
        
        # Set environment variable
        monkeypatch.setenv("TEST_VAR", "from_env")
        
        # Create config with value
        config = ConfigFactory.parse_string('test { var = "from_config" }')
        
        # Config should win
        result = get_config_or_env(config, "test.var", "TEST_VAR", "default")
        assert result == "from_config"
    
    def test_env_fallback_when_no_config(self, monkeypatch):
        """Test environment variable is used when config missing."""
        from pyhocon import ConfigFactory
        
        # Set environment variable
        monkeypatch.setenv("TEST_VAR", "from_env")
        
        # Create config without value
        config = ConfigFactory.parse_string('test { other = "value" }')
        
        # Env should be used
        result = get_config_or_env(config, "test.missing", "TEST_VAR", "default")
        assert result == "from_env"
    
    def test_default_fallback_when_both_missing(self, monkeypatch):
        """Test default is used when both config and env missing."""
        from pyhocon import ConfigFactory
        
        # Ensure env var not set
        monkeypatch.delenv("TEST_VAR", raising=False)
        
        # Create config without value
        config = ConfigFactory.parse_string('test { other = "value" }')
        
        # Default should be used
        result = get_config_or_env(config, "test.missing", "TEST_VAR", "default")
        assert result == "default"
    
    def test_none_default(self, monkeypatch):
        """Test None is returned when no default provided."""
        from pyhocon import ConfigFactory
        
        monkeypatch.delenv("TEST_VAR", raising=False)
        config = ConfigFactory.parse_string('test { other = "value" }')
        
        result = get_config_or_env(config, "test.missing", "TEST_VAR")
        assert result is None


class TestSecretsConfiguration:
    """Test secrets configuration in real scenarios."""
    
    def test_postgres_password_from_env(self, tmp_path, monkeypatch):
        """Test PostgreSQL password loaded from environment."""
        monkeypatch.setenv("POSTGRES_PASSWORD", "secure_password_123")
        
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('''
        tribench {
          systems {
            postgresql {
              password = ${?POSTGRES_PASSWORD}"default_password"
            }
          }
        }
        ''')
        
        loader = ConfigurationLoader(root_path=tmp_path)
        config = loader.load()
        
        password = config.get("tribench.systems.postgresql.password")
        assert password == "secure_password_123"
    
    def test_minio_credentials_from_env(self, tmp_path, monkeypatch):
        """Test MinIO credentials loaded from environment."""
        monkeypatch.setenv("MINIO_ACCESS_KEY", "my_access_key")
        monkeypatch.setenv("MINIO_SECRET_KEY", "my_secret_key")
        
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('''
        tribench {
          systems {
            minio {
              access_key = ${?MINIO_ACCESS_KEY}"default_access"
              secret_key = ${?MINIO_SECRET_KEY}"default_secret"
            }
          }
        }
        ''')
        
        loader = ConfigurationLoader(root_path=tmp_path)
        config = loader.load()
        
        assert config.get("tribench.systems.minio.access_key") == "my_access_key"
        assert config.get("tribench.systems.minio.secret_key") == "my_secret_key"
    
    def test_multiple_secrets_from_dotenv(self, tmp_path):
        """Test multiple secrets loaded from .env file."""
        # Create .env with multiple secrets
        env_file = tmp_path / ".env"
        env_file.write_text("""
POSTGRES_PASSWORD=db_password_123
MINIO_ACCESS_KEY=minio_access_123
MINIO_SECRET_KEY=minio_secret_123
TRINO_PASSWORD=trino_password_123
        """.strip())
        
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('''
        tribench {
          systems {
            postgresql {
              password = ${?POSTGRES_PASSWORD}"default"
            }
            minio {
              access_key = ${?MINIO_ACCESS_KEY}"default"
              secret_key = ${?MINIO_SECRET_KEY}"default"
            }
            trino {
              password = ${?TRINO_PASSWORD}""
            }
          }
        }
        ''')
        
        # Mock load_dotenv to set environment variables
        with patch('tribench.utils.config.load_dotenv') as mock_load:
            def side_effect(*args, **kwargs):
                os.environ["POSTGRES_PASSWORD"] = "db_password_123"
                os.environ["MINIO_ACCESS_KEY"] = "minio_access_123"
                os.environ["MINIO_SECRET_KEY"] = "minio_secret_123"
                os.environ["TRINO_PASSWORD"] = "trino_password_123"
            mock_load.side_effect = side_effect
            
            loader = ConfigurationLoader(root_path=tmp_path)
            config = loader.load()
            
            assert config.get("tribench.systems.postgresql.password") == "db_password_123"
            assert config.get("tribench.systems.minio.access_key") == "minio_access_123"
            assert config.get("tribench.systems.minio.secret_key") == "minio_secret_123"
            assert config.get("tribench.systems.trino.password") == "trino_password_123"


class TestConfigurationSecurity:
    """Test security aspects of configuration management."""
    
    def test_env_file_not_required(self, tmp_path):
        """Test framework works without .env file (security: no default secrets)."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('tribench { systems { } }')
        
        # Should work without .env
        loader = ConfigurationLoader(root_path=tmp_path)
        config = loader.load()
        assert config is not None
    
    def test_sensitive_values_not_logged(self, tmp_path, caplog):
        """Test that sensitive values are not exposed in logs."""
        import logging
        caplog.set_level(logging.DEBUG)
        
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET_PASSWORD=super_secret_123")
        
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('tribench { systems { } }')
        
        loader = ConfigurationLoader(root_path=tmp_path)
        
        # Verify password is not in logs
        log_text = "\n".join([record.message for record in caplog.records])
        assert "super_secret_123" not in log_text
    
    def test_env_file_path_logged_only(self, tmp_path, caplog):
        """Test only .env file path is logged, not contents."""
        import logging
        caplog.set_level(logging.INFO)
        
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=my_secret")
        
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        ref_config = config_dir / "reference.conf"
        ref_config.write_text('tribench { systems { } }')
        
        loader = ConfigurationLoader(root_path=tmp_path)
        
        # Should log file path
        log_text = "\n".join([record.message for record in caplog.records])
        assert str(env_file) in log_text or "environment variables" in log_text.lower()
        
        # Should NOT log secret value
        assert "my_secret" not in log_text
