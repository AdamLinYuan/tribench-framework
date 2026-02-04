"""
Configuration loading and merging.

Handles hierarchical configuration loading from reference, host, and experiment configs.
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any
from pyhocon import ConfigFactory, ConfigTree
from dotenv import load_dotenv, find_dotenv
import logging

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class ConfigurationLoader:
    """
    Hierarchical configuration loader for TriBench.
    
    Loads and merges configuration from multiple layers:
    1. Reference config (defaults)
    2. Host config (machine-specific)
    3. Experiment config (experiment-specific)
    
    Supports HOCON format with variable substitution and includes.
    """
    
    def __init__(self, root_path: Optional[Path] = None, load_env: bool = True):
        """
        Initialize the configuration loader.
        
        Args:
            root_path: Root path of the TriBench framework.
                      If None, auto-detect from this file's location.
            load_env: Whether to automatically load .env file from root_path.
                     Default is True. Set to False for testing.
        """
        if root_path is None:
            # Auto-detect: go up from lib/tribench/utils/config/loader.py to root
            self.root_path = Path(__file__).parent.parent.parent.parent.parent
        else:
            self.root_path = Path(root_path)
        
        self.config_path = self.root_path / "config"
        self.reference_config_path = self.config_path / "reference.conf"
        self.hosts_path = self.config_path / "hosts"
        self.profile_file = self.root_path / ".tribench-profile"
        
        # Load environment variables from .env file
        if load_env:
            self._load_env_file()
        
        logger.debug(f"ConfigurationLoader initialized with root: {self.root_path}")
    
    def _load_env_file(self) -> None:
        """
        Load environment variables from .env file.
        
        Searches for .env file in the following order:
        1. Explicit .env file in root_path
        2. Auto-detected .env in parent directories (using find_dotenv)
        
        Environment variables from .env have LOWER priority than
        existing environment variables (doesn't override).
        """
        env_path = self.root_path / ".env"
        
        if env_path.exists():
            # Load from explicit path
            load_dotenv(env_path, override=False)
            logger.info(f"Loaded environment variables from: {env_path}")
        else:
            logger.debug("No .env file found - using system environment only")
    
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get environment variable value.
        
        Args:
            key: Environment variable name
            default: Default value if not set
        
        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)
    
    def load(self, 
             experiment_config: Optional[Path] = None,
             host_name: Optional[str] = None) -> ConfigTree:
        """
        Load and merge configuration from all layers.
        
        Args:
            experiment_config: Path to experiment configuration file (YAML/HOCON)
            host_name: Host name for host-specific config. If None, auto-detect.
        
        Returns:
            Merged configuration as ConfigTree
        
        Raises:
            ConfigurationError: If configuration loading or merging fails
        """
        try:
            # Layer 1: Load reference configuration (defaults)
            config = self._load_reference_config()
            logger.info("Loaded reference configuration")
            
            # Layer 2: Load and merge host configuration
            host_config = self._load_host_config(host_name)
            if host_config:
                config = ConfigTree.merge_configs(config, host_config)
                logger.info(f"Merged host configuration for: {host_name or 'auto-detected'}")
            
            # Layer 3: Load and merge experiment configuration
            if experiment_config:
                exp_config = self._load_experiment_config(experiment_config)
                config = ConfigTree.merge_configs(config, exp_config)
                logger.info(f"Merged experiment configuration: {experiment_config}")

            
            return config
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}") from e
    
    def _load_reference_config(self) -> ConfigTree:
        """Load the reference configuration (defaults)."""
        if not self.reference_config_path.exists():
            raise ConfigurationError(
                f"Reference configuration not found: {self.reference_config_path}"
            )
        
        try:
            return ConfigFactory.parse_file(str(self.reference_config_path))
        except Exception as e:
            raise ConfigurationError(
                f"Failed to parse reference config: {e}"
            ) from e
    
    def get_active_profile(self) -> Optional[str]:
        """
        Get the active configuration profile name.
        
        Returns:
            Profile name (without .conf extension) or None
        """
        if self.profile_file.exists():
            try:
                profile = self.profile_file.read_text().strip()
                if profile:
                    logger.debug(f"Active profile: {profile}")
                    return profile
            except Exception as e:
                logger.warning(f"Failed to read profile file: {e}")
        return None
    
    def set_active_profile(self, profile_name: str) -> bool:
        """
        Set the active configuration profile and switch kubectl context if needed.
        
        Args:
            profile_name: Profile name (with or without .conf extension)
        
        Returns:
            True if profile was set successfully
        """
        # Strip .conf extension if provided
        if profile_name.endswith('.conf'):
            profile_name = profile_name[:-5]
        
        # Verify profile exists
        config_path = self.hosts_path / f"{profile_name}.conf"
        if not config_path.exists():
            logger.error(f"Profile not found: {config_path}")
            return False
        
        try:
            # Load the profile config to get kubernetes context
            profile_config = ConfigFactory.parse_file(str(config_path))
            k8s_context = profile_config.get("tribench.kubernetes.context", None)
            
            # If profile has a kubernetes context, switch kubectl context
            if k8s_context:
                try:
                    result = subprocess.run(
                        ["kubectl", "config", "use-context", k8s_context],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    logger.info(f"✓ Switched kubectl context to: {k8s_context}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to switch kubectl context to {k8s_context}: {e.stderr.strip()}")
                    logger.warning("Continuing with profile switch, but kubectl context may be incorrect")
                except FileNotFoundError:
                    logger.warning("kubectl not found - skipping context switch")
            
            self.profile_file.write_text(profile_name)
            logger.info(f"✓ Active profile set to: {profile_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to set profile: {e}")
            return False
    
    def clear_active_profile(self) -> None:
        """Clear the active profile, reverting to hostname-based detection."""
        if self.profile_file.exists():
            self.profile_file.unlink()
            logger.info("✓ Active profile cleared (will use hostname detection)")
    
    def _load_host_config(self, host_name: Optional[str] = None) -> Optional[ConfigTree]:
        """
        Load host-specific configuration.
        
        Priority:
        1. Active profile (from .tribench-profile)
        2. Explicit host_name parameter
        3. Auto-detected hostname
        
        Args:
            host_name: Host name. If None, checks active profile then auto-detects.
        
        Returns:
            Host configuration or None if not found
        """
        # Priority 1: Check for active profile
        if host_name is None:
            active_profile = self.get_active_profile()
            if active_profile:
                host_name = active_profile
                logger.info(f"Using active profile: {host_name}")
        
        # Priority 2/3: Use provided host_name or auto-detect hostname
        if host_name is None:
            host_name = platform.node()
            logger.debug(f"Auto-detected hostname: {host_name}")
        
        # Look for flat file: hosts/{hostname}.conf
        config_path = self.hosts_path / f"{host_name}.conf"
        
        if config_path.exists():
            logger.debug(f"Loading host config from: {config_path}")
            try:
                return ConfigFactory.parse_file(str(config_path))
            except Exception as e:
                logger.warning(f"Failed to parse host config {config_path}: {e}")
                return None
        
        logger.warning(f"No host configuration is being applied")
        return None
    
    def _load_experiment_config(self, config_path: Path) -> ConfigTree:
        """
        Load experiment configuration from YAML or HOCON file.
        
        Args:
            config_path: Path to experiment configuration
        
        Returns:
            Experiment configuration
        
        Raises:
            ConfigurationError: If file doesn't exist or parsing fails
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigurationError(f"Experiment config not found: {config_path}")
        
        try:
            # ConfigFactory handles both YAML and HOCON
            return ConfigFactory.parse_file(str(config_path))
        except Exception as e:
            raise ConfigurationError(
                f"Failed to parse experiment config {config_path}: {e}"
            ) from e
    
    
    def validate(self, config: ConfigTree, schema: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Validate configuration against a schema.
        
        Args:
            config: Configuration to validate
            schema: Validation schema (optional)
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if schema is None:
            # Basic validation - check for required top-level keys
            required_keys = ["tribench", "systems"]
            for key in required_keys:
                if key not in config:
                    errors.append(f"Missing required configuration key: {key}")
        else:
            # Custom schema validation
            errors.extend(self._validate_schema(config, schema))
        
        return errors
    
    def _validate_schema(self, config: ConfigTree, schema: Dict[str, Any], 
                        path: str = "") -> List[str]:
        """
        Recursively validate configuration against schema.
        
        Args:
            config: Configuration to validate
            schema: Validation schema
            path: Current path in config tree (for error messages)
        
        Returns:
            List of validation errors
        """
        errors = []
        
        for key, rules in schema.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check if required key exists
            if rules.get("required", False) and key not in config:
                errors.append(f"Missing required field: {current_path}")
                continue
            
            if key not in config:
                continue
            
            value = config[key]
            
            # Type validation
            if "type" in rules:
                expected_type = rules["type"]
                if not isinstance(value, expected_type):
                    errors.append(
                        f"Invalid type for {current_path}: "
                        f"expected {expected_type.__name__}, got {type(value).__name__}"
                    )
            
            # Range validation for numbers
            if "min" in rules and isinstance(value, (int, float)):
                if value < rules["min"]:
                    errors.append(
                        f"Value for {current_path} below minimum: {value} < {rules['min']}"
                    )
            
            if "max" in rules and isinstance(value, (int, float)):
                if value > rules["max"]:
                    errors.append(
                        f"Value for {current_path} above maximum: {value} > {rules['max']}"
                    )
            
            # Choice validation
            if "choices" in rules and value not in rules["choices"]:
                errors.append(
                    f"Invalid value for {current_path}: {value} "
                    f"not in {rules['choices']}"
                )
            
            # Nested schema validation
            if "schema" in rules and isinstance(value, dict):
                errors.extend(
                    self._validate_schema(value, rules["schema"], current_path)
                )
        
        return errors
