"""
Configuration management for TriBench.

This module provides hierarchical configuration loading using HOCON format,
supporting multiple configuration layers (reference → host → experiment)
with validation and template generation capabilities.
"""

import os
import platform
from pathlib import Path
from typing import Any, Dict, Optional, List
from pyhocon import ConfigFactory, ConfigTree
from jinja2 import Environment, FileSystemLoader, Template
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
    
    def __init__(self, root_path: Optional[Path] = None):
        """
        Initialize the configuration loader.
        
        Args:
            root_path: Root path of the TriBench framework.
                      If None, auto-detect from this file's location.
        """
        if root_path is None:
            # Auto-detect: go up from lib/tribench/utils/config.py to root
            self.root_path = Path(__file__).parent.parent.parent.parent
        else:
            self.root_path = Path(root_path)
        
        self.config_path = self.root_path / "config"
        self.reference_config_path = self.config_path / "reference.conf"
        self.hosts_path = self.config_path / "hosts"
        
        logger.debug(f"ConfigurationLoader initialized with root: {self.root_path}")
    
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
            
            # Resolve environment variables
            config = self._resolve_env_vars(config)
            
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
    
    def _load_host_config(self, host_name: Optional[str] = None) -> Optional[ConfigTree]:
        """
        Load host-specific configuration.
        
        Args:
            host_name: Host name. If None, auto-detect using platform.node()
        
        Returns:
            Host configuration or None if not found
        """
        if host_name is None:
            host_name = platform.node().split('.')[0]  # Get hostname without domain
        
        # Try multiple config file formats
        possible_paths = [
            self.hosts_path / host_name / "application.conf",
            self.hosts_path / f"{host_name}.conf",
        ]
        
        for config_path in possible_paths:
            if config_path.exists():
                logger.debug(f"Loading host config from: {config_path}")
                try:
                    return ConfigFactory.parse_file(str(config_path))
                except Exception as e:
                    logger.warning(f"Failed to parse host config {config_path}: {e}")
                    continue
        
        logger.warning(f"No host configuration found for: {host_name}")
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
    
    def _resolve_env_vars(self, config: ConfigTree) -> ConfigTree:
        """
        Resolve environment variable references in configuration.
        
        HOCON already supports ${?ENV_VAR} syntax, but this provides
        additional resolution for nested structures.
        
        Args:
            config: Configuration tree
        
        Returns:
            Configuration with resolved environment variables
        """
        # HOCON's ConfigFactory already resolves ${?VAR} syntax
        # This is handled automatically during parsing
        return config
    
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


class ConfigurationTemplate:
    """
    Template-based system configuration generator.
    
    Generates system-specific configuration files (e.g., Trino's config.properties)
    from HOCON configuration using Jinja2 templates.
    """
    
    def __init__(self, templates_path: Optional[Path] = None):
        """
        Initialize the template generator.
        
        Args:
            templates_path: Path to template directory.
                          If None, use config/templates/
        """
        if templates_path is None:
            root_path = Path(__file__).parent.parent.parent.parent
            templates_path = root_path / "config" / "templates"
        
        self.templates_path = Path(templates_path)
        
        if self.templates_path.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(self.templates_path)),
                trim_blocks=True,
                lstrip_blocks=True,
                keep_trailing_newline=True
            )
        else:
            logger.warning(f"Templates directory not found: {self.templates_path}")
            self.env = None
    
    def generate(self, 
                template_name: str, 
                config: ConfigTree, 
                output_path: Optional[Path] = None) -> str:
        """
        Generate configuration file from template.
        
        Args:
            template_name: Name of the template file
            config: Configuration data
            output_path: Optional path to write generated config
        
        Returns:
            Generated configuration as string
        
        Raises:
            ConfigurationError: If template not found or rendering fails
        """
        if self.env is None:
            raise ConfigurationError(
                f"Templates directory not found: {self.templates_path}"
            )
        
        try:
            template = self.env.get_template(template_name)
            rendered = template.render(config=config)
            
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered)
                logger.info(f"Generated config file: {output_path}")
            
            return rendered
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to generate config from template {template_name}: {e}"
            ) from e
    
    def generate_from_string(self, 
                            template_str: str, 
                            config: ConfigTree,
                            output_path: Optional[Path] = None) -> str:
        """
        Generate configuration from template string.
        
        Args:
            template_str: Template string
            config: Configuration data
            output_path: Optional path to write generated config
        
        Returns:
            Generated configuration as string
        """
        try:
            template = Template(template_str)
            rendered = template.render(config=config)
            
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(rendered)
                logger.info(f"Generated config file: {output_path}")
            
            return rendered
            
        except Exception as e:
            raise ConfigurationError(
                f"Failed to generate config from template string: {e}"
            ) from e


def get_config_value(config: ConfigTree, 
                     path: str, 
                     default: Any = None) -> Any:
    """
    Get configuration value using dot-notation path.
    
    Args:
        config: Configuration tree
        path: Dot-notation path (e.g., "trino.coordinator.port")
        default: Default value if path not found
    
    Returns:
        Configuration value or default
    
    Examples:
        >>> config = ConfigFactory.parse_string('trino { port = 8080 }')
        >>> get_config_value(config, 'trino.port')
        8080
        >>> get_config_value(config, 'trino.missing', default=9999)
        9999
    """
    try:
        return config.get(path, default)
    except Exception:
        return default
