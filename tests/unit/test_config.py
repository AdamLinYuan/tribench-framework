"""
Unit tests for configuration management system.
"""

import pytest
from pathlib import Path
import tempfile
import os
from pyhocon import ConfigFactory, ConfigTree

from tribench.utils.config import (
    ConfigurationLoader,
    ConfigurationTemplate,
    ConfigurationError,
    get_config_value
)


class TestConfigurationLoader:
    """Test suite for ConfigurationLoader."""
    
    def test_init_with_root_path(self, tmp_path):
        """Test initialization with explicit root path."""
        loader = ConfigurationLoader(root_path=tmp_path)
        assert loader.root_path == tmp_path
        assert loader.config_path == tmp_path / "config"
    
    def test_init_auto_detect(self):
        """Test auto-detection of root path."""
        loader = ConfigurationLoader()
        assert loader.root_path.exists()
        assert (loader.root_path / "config").exists()
    
    def test_load_reference_config(self):
        """Test loading reference configuration."""
        loader = ConfigurationLoader()
        config = loader._load_reference_config()
        
        assert config is not None
        assert "tribench" in config
        assert config["tribench"]["version"] == "1.0.0"
    
    def test_load_reference_config_missing(self, tmp_path):
        """Test error handling when reference config is missing."""
        loader = ConfigurationLoader(root_path=tmp_path)
        
        with pytest.raises(ConfigurationError, match="Reference configuration not found"):
            loader._load_reference_config()
    
    def test_load_host_config_auto_detect(self):
        """Test auto-detection of host configuration."""
        loader = ConfigurationLoader()
        
        # This may return None if no host config exists, which is OK
        host_config = loader._load_host_config()
        
        # Should not raise an error
        assert host_config is None or isinstance(host_config, ConfigTree)
    
    def test_load_host_config_explicit(self):
        """Test loading host config with explicit name."""
        loader = ConfigurationLoader()
        
        # Try localhost which should exist
        host_config = loader._load_host_config(host_name="localhost")
        
        if host_config:
            assert isinstance(host_config, ConfigTree)
            assert "tribench" in host_config
    
    def test_load_experiment_config(self, tmp_path):
        """Test loading experiment configuration."""
        # Create a test experiment config
        exp_config_path = tmp_path / "test_experiment.conf"
        exp_config_path.write_text("""
experiment {
    name = "test-experiment"
    runs = 3
    warmup = 1
    queries = [1, 2, 3]
}
        """)
        
        loader = ConfigurationLoader()
        config = loader._load_experiment_config(exp_config_path)
        
        assert config is not None
        assert config["experiment"]["name"] == "test-experiment"
        assert config["experiment"]["runs"] == 3
    
    def test_load_experiment_config_missing(self, tmp_path):
        """Test error when experiment config is missing."""
        loader = ConfigurationLoader()
        missing_path = tmp_path / "missing.conf"
        
        with pytest.raises(ConfigurationError, match="Experiment config not found"):
            loader._load_experiment_config(missing_path)
    
    def test_load_full_hierarchy(self, tmp_path):
        """Test loading and merging full configuration hierarchy."""
        # Create minimal reference config
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        
        reference_conf = config_dir / "reference.conf"
        reference_conf.write_text("""
tribench {
    version = "1.0.0"
    systems {
        trino {
            port = 8080
            memory = "2G"
        }
    }
}
        """)
        
        # Create host config that overrides memory
        hosts_dir = config_dir / "hosts" / "testhost"
        hosts_dir.mkdir(parents=True)
        
        host_conf = hosts_dir / "application.conf"
        host_conf.write_text("""
tribench {
    systems {
        trino {
            memory = "4G"
        }
    }
}
        """)
        
        # Create experiment config
        exp_config = tmp_path / "experiment.conf"
        exp_config.write_text("""
experiment {
    name = "test"
    runs = 5
}
tribench {
    systems {
        trino {
            port = 9090
        }
    }
}
        """)
        
        loader = ConfigurationLoader(root_path=tmp_path)
        config = loader.load(
            experiment_config=exp_config,
            host_name="testhost"
        )
        
        # Check hierarchy is properly merged
        assert config["tribench"]["version"] == "1.0.0"  # From reference
        assert config["tribench"]["systems"]["trino"]["memory"] == "4G"  # From host
        assert config["tribench"]["systems"]["trino"]["port"] == 9090  # From experiment
        assert config["experiment"]["name"] == "test"  # From experiment
    
    def test_validate_basic(self):
        """Test basic configuration validation."""
        loader = ConfigurationLoader()
        
        # Valid config
        valid_config = ConfigFactory.parse_string("""
tribench {
    version = "1.0.0"
}
systems {
    trino {
        port = 8080
    }
}
        """)
        
        errors = loader.validate(valid_config)
        assert len(errors) == 0
        
        # Invalid config (missing required keys)
        invalid_config = ConfigFactory.parse_string("""
tribench {
    version = "1.0.0"
}
        """)
        
        errors = loader.validate(invalid_config)
        assert len(errors) > 0
        assert any("systems" in err for err in errors)
    
    def test_validate_with_schema(self):
        """Test validation with custom schema."""
        loader = ConfigurationLoader()
        
        config = ConfigFactory.parse_string("""
trino {
    port = 8080
    memory = "2G"
    coordinator = true
}
        """)
        
        schema = {
            "trino": {
                "required": True,
                "schema": {
                    "port": {
                        "required": True,
                        "type": int,
                        "min": 1024,
                        "max": 65535
                    },
                    "memory": {
                        "required": True,
                        "type": str
                    },
                    "coordinator": {
                        "required": True,
                        "type": bool
                    }
                }
            }
        }
        
        errors = loader.validate(config, schema)
        assert len(errors) == 0
        
        # Test with invalid port
        invalid_config = ConfigFactory.parse_string("""
trino {
    port = 80
    memory = "2G"
    coordinator = true
}
        """)
        
        errors = loader.validate(invalid_config, schema)
        assert len(errors) > 0
        assert any("below minimum" in err for err in errors)


class TestConfigurationTemplate:
    """Test suite for ConfigurationTemplate."""
    
    def test_init(self, tmp_path):
        """Test template generator initialization."""
        templates_path = tmp_path / "templates"
        templates_path.mkdir()
        
        generator = ConfigurationTemplate(templates_path=templates_path)
        assert generator.templates_path == templates_path
        assert generator.env is not None
    
    def test_generate_from_string(self, tmp_path):
        """Test generating config from template string."""
        generator = ConfigurationTemplate()
        
        template_str = """
coordinator=true
http-server.http.port={{ config.trino.port }}
query.max-memory={{ config.trino.memory }}
        """
        
        config = ConfigFactory.parse_string("""
trino {
    port = 8080
    memory = "2G"
}
        """)
        
        output_path = tmp_path / "config.properties"
        result = generator.generate_from_string(template_str, config, output_path)
        
        assert "coordinator=true" in result
        assert "http-server.http.port=8080" in result
        assert "query.max-memory=2G" in result
        assert output_path.exists()
    
    def test_generate_from_file(self, tmp_path):
        """Test generating config from template file."""
        templates_path = tmp_path / "templates"
        templates_path.mkdir()
        
        template_file = templates_path / "trino.properties.j2"
        template_file.write_text("""
coordinator={{ config.coordinator }}
http-server.http.port={{ config.port }}
        """)
        
        generator = ConfigurationTemplate(templates_path=templates_path)
        
        config = ConfigFactory.parse_string("""
coordinator = true
port = 8080
        """)
        
        output_path = tmp_path / "output.properties"
        result = generator.generate("trino.properties.j2", config, output_path)
        
        assert "coordinator=True" in result
        assert "http-server.http.port=8080" in result
        assert output_path.exists()
    
    def test_generate_missing_template(self, tmp_path):
        """Test error handling for missing template."""
        templates_path = tmp_path / "templates"
        templates_path.mkdir()
        
        generator = ConfigurationTemplate(templates_path=templates_path)
        config = ConfigFactory.parse_string("test = true")
        
        with pytest.raises(ConfigurationError):
            generator.generate("missing.j2", config)


class TestConfigUtilities:
    """Test suite for configuration utility functions."""
    
    def test_get_config_value(self):
        """Test getting configuration values with dot notation."""
        config = ConfigFactory.parse_string("""
tribench {
    systems {
        trino {
            port = 8080
            memory = "2G"
        }
    }
}
        """)
        
        # Test getting nested value
        assert get_config_value(config, "tribench.systems.trino.port") == 8080
        assert get_config_value(config, "tribench.systems.trino.memory") == "2G"
        
        # Test default value
        assert get_config_value(config, "missing.path", default=9999) == 9999
        
        # Test with None default
        assert get_config_value(config, "missing.path") is None


class TestEnvironmentVariables:
    """Test environment variable substitution."""
    
    def test_env_var_substitution(self):
        """Test that environment variables are resolved."""
        # Set test environment variables
        os.environ["TEST_PORT"] = "9090"
        os.environ["TEST_MEMORY"] = "4G"
        
        try:
            config_str = """
trino {
    port = ${TEST_PORT}
    host = ${?MISSING_VAR}
    memory = ${TEST_MEMORY}
    default_memory = "2G"
}
            """
            
            config = ConfigFactory.parse_string(config_str)
            
            # Required env var
            assert config["trino"]["port"] == "9090"
            
            # Optional env var (not set, so key should not exist)
            assert "host" not in config["trino"]
            
            # Env var that is set
            assert config["trino"]["memory"] == "4G"
            
            # Regular value
            assert config["trino"]["default_memory"] == "2G"
            
        finally:
            del os.environ["TEST_PORT"]
            del os.environ["TEST_MEMORY"]
