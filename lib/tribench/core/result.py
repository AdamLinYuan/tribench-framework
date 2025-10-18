"""Result representation for benchmark experiments."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional


@dataclass
class Result:
    """
    Represents the result of a benchmark experiment.
    """

    experiment_name: str
    experiment_type: str
    timestamp: datetime
    duration_seconds: float
    status: str  # success, failed, timeout

    # Query execution metrics
    execution_time: Optional[float] = None
    cpu_time: Optional[float] = None
    memory_usage: Optional[float] = None
    data_scanned: Optional[int] = None
    rows_returned: Optional[int] = None

    # System metrics
    system_metrics: Dict[str, Any] = field(default_factory=dict)

    # Validation results
    validation_passed: bool = True
    validation_errors: List[str] = field(default_factory=list)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Error information
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for serialization."""
        return {
            "experiment_name": self.experiment_name,
            "experiment_type": self.experiment_type,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "execution_time": self.execution_time,
            "cpu_time": self.cpu_time,
            "memory_usage": self.memory_usage,
            "data_scanned": self.data_scanned,
            "rows_returned": self.rows_returned,
            "system_metrics": self.system_metrics,
            "validation_passed": self.validation_passed,
            "validation_errors": self.validation_errors,
            "metadata": self.metadata,
            "error_message": self.error_message,
            "error_traceback": self.error_traceback,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Result":
        """Create Result from dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)
