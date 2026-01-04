"""
Backwards compatibility wrapper for result_storage module.

DEPRECATED: This module has been refactored into tribench.storage.result package.
Import from tribench.storage.result instead:
    from tribench.storage.result import ResultStorage
"""

import warnings
from tribench.storage.result import ResultStorage

# Issue deprecation warning
warnings.warn(
    "tribench.storage.result_storage is deprecated. "
    "Use 'from tribench.storage.result import ResultStorage' instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = ["ResultStorage"]

