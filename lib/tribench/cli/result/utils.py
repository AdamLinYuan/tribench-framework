"""
Shared utilities for result commands.

Provides common functionality used across result command modules.
"""

import click
from typing import Optional

# Import storage components
try:
    from tribench.storage import (
        ResultStorage,
        init_database,
    )
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False

# Import analysis modules
try:
    from tribench.analysis import (
        StatisticalAnalyzer,
        PerformanceAnalyzer,
        ComparisonAnalyzer,
        ScalabilityAnalyzer,
        RegressionDetector,
    )
    ANALYSIS_AVAILABLE = True
except ImportError:
    ANALYSIS_AVAILABLE = False


def get_storage() -> Optional[ResultStorage]:
    """Get ResultStorage instance or None if unavailable."""
    if not STORAGE_AVAILABLE:
        click.secho("✗ Database storage not available", fg='red')
        return None
    
    try:
        init_database()
        return ResultStorage()
    except Exception as e:
        click.secho(f"✗ Failed to initialize database: {e}", fg='red')
        return None
