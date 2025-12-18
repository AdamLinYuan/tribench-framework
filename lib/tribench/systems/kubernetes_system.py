"""
DEPRECATED: This module has been restructured.

The KubernetesSystem implementation has been split into focused modules
in the `tribench.systems.kubernetes` package for better maintainability.

This file now serves as a backwards-compatibility wrapper and will be
removed in a future version.

Please update imports:
    from tribench.systems.kubernetes_system import KubernetesSystem
to:
    from tribench.systems.kubernetes import KubernetesSystem
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "tribench.systems.kubernetes_system is deprecated. "
    "Use tribench.systems.kubernetes instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from new location
from tribench.systems.kubernetes.system import KubernetesSystem

__all__ = ['KubernetesSystem']
