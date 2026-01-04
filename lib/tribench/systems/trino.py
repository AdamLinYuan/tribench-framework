"""
DEPRECATED: This module has been restructured.

The TrinoSystem implementation has been split into focused modules
in the `tribench.systems.trino` package for better maintainability.

This file now serves as a backwards-compatibility wrapper and will be
removed in a future version.

Please update imports:
    from tribench.systems.trino import TrinoSystem
(This import path remains the same and will continue to work)
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "tribench.systems.trino module has been restructured. "
    "The current import path still works but the internal structure has changed.",
    DeprecationWarning,
    stacklevel=2
)

# Import from new location
from tribench.systems.trino.system import TrinoSystem

__all__ = ['TrinoSystem']
