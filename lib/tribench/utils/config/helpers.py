"""
Configuration helper functions.

Utility functions for accessing configuration values.
"""

import os
from typing import Any
from pyhocon import ConfigTree


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


def get_config_or_env(config: ConfigTree,
                     config_path: str,
                     env_var: str,
                     default: Any = None) -> Any:
    """
    Get configuration value from config first, then environment variable.
    
    This helper function implements the precedence:
    1. Configuration file value (if present)
    2. Environment variable (if set)
    3. Default value
    
    Args:
        config: Configuration tree
        config_path: Dot-notation path in config
        env_var: Environment variable name
        default: Default value if neither config nor env is set
    
    Returns:
        Configuration value, environment value, or default
    
    Examples:
        >>> # Prefer config value over environment
        >>> config = ConfigFactory.parse_string('db { password = "from_config" }')
        >>> os.environ['DB_PASSWORD'] = 'from_env'
        >>> get_config_or_env(config, 'db.password', 'DB_PASSWORD', 'default')
        'from_config'
        
        >>> # Fall back to environment if config missing
        >>> get_config_or_env(config, 'db.missing', 'DB_PASSWORD', 'default')
        'from_env'
        
        >>> # Use default if both missing
        >>> get_config_or_env(config, 'db.missing', 'MISSING_VAR', 'default')
        'default'
    """
    # First try config
    value = get_config_value(config, config_path, None)
    if value is not None:
        return value
    
    # Then try environment variable
    env_value = os.getenv(env_var)
    if env_value is not None:
        return env_value
    
    # Finally return default
    return default
