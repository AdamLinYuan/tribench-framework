"""
Trino metrics data models.

Defines data structures for query and cluster metrics.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class QueryMetrics:
    """Metrics for a single Trino query."""
    
    query_id: str
    state: str
    query: str
    
    # Timing metrics (milliseconds)
    queued_time_ms: Optional[int] = None
    planning_time_ms: Optional[int] = None
    analysis_time_ms: Optional[int] = None
    execution_time_ms: Optional[int] = None
    elapsed_time_ms: Optional[int] = None
    
    # Resource metrics
    cpu_time_ms: Optional[int] = None
    scheduled_time_ms: Optional[int] = None
    blocked_time_ms: Optional[int] = None
    peak_memory_bytes: Optional[int] = None
    
    # Data processing metrics
    input_rows: Optional[int] = None
    input_bytes: Optional[int] = None
    output_rows: Optional[int] = None
    output_bytes: Optional[int] = None
    physical_input_bytes: Optional[int] = None
    
    # Query state
    create_time: Optional[str] = None
    end_time: Optional[str] = None
    user: Optional[str] = None
    session_properties: Dict[str, Any] = field(default_factory=dict)
    
    # Error information
    error_code: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class ClusterMetrics:
    """Metrics for Trino cluster state."""
    
    # Cluster information
    version: str
    coordinator: bool
    starting: bool
    
    # Query statistics
    active_queries: int = 0
    queued_queries: int = 0
    running_queries: int = 0
    blocked_queries: int = 0
    
    # Node statistics
    active_nodes: int = 0
    inactive_nodes: int = 0
    shutting_down_nodes: int = 0
    
    # Resource statistics
    total_available_processors: int = 0
    running_drivers: int = 0
    running_tasks: int = 0
    reserved_memory_bytes: int = 0
