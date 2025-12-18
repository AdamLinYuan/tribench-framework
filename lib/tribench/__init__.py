"""
TriBench - Trino Benchmarking Framework

A systematic, reproducible framework for benchmarking SQL workloads on
distributed data lakehouses using Apache Trino.
"""

from tribench.__version__ import __version__
from tribench.defaults import Defaults

__all__ = ["__version__", "Defaults"]
