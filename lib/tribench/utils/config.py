"""
Backwards compatibility wrapper for config module.

DEPRECATED: This module has been refactored into tribench.utils.config package.
Import from tribench.utils.config instead:
    from tribench.utils.config import ConfigurationLoader, ConfigurationTemplate
"""

import warnings
from tribench.utils.config import (
    ConfigurationLoader,
    ConfigurationError,
    ConfigurationTemplate,
    get_config_value,
    get_config_or_env,
)

# Issue deprecation warning
warnings.warn(
    "tribench.utils.config as a single module is deprecated. "
    "Use 'from tribench.utils.config import ConfigurationLoader, ConfigurationTemplate' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    "ConfigurationLoader",
    "ConfigurationError",
    "ConfigurationTemplate",
    "get_config_value",
    "get_config_or_env",
]
