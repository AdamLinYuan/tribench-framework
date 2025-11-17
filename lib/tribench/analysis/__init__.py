"""Analysis module for performance analysis and reporting."""

from .statistical import StatisticalAnalyzer
from .performance import PerformanceAnalyzer
from .comparison import ComparisonAnalyzer
from .scalability import ScalabilityAnalyzer
from .regression import RegressionDetector

__all__ = [
    "StatisticalAnalyzer",
    "PerformanceAnalyzer",
    "ComparisonAnalyzer",
    "ScalabilityAnalyzer",
    "RegressionDetector",
]
