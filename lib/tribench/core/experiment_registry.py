"""
Experiment Registry - Maps system types to experiment implementations.

Temporary stub until full registry pattern is implemented (see FLEXIBILITY_ANALYSIS.md #2).
"""

from typing import Dict, Type
from tribench.core.experiment import Experiment, ExperimentConfig


class ExperimentRegistry:
    """
    Registry for experiment implementations by system type.
    Maps system name -> Experiment class.
    
    TODO: Full implementation in FLEXIBILITY_ANALYSIS.md #2
    """
    
    _experiments: Dict[str, Type[Experiment]] = {}
    
    @classmethod
    def register(cls, system: str, experiment_class: Type[Experiment]):
        """Register an experiment implementation for a system."""
        cls._experiments[system.lower()] = experiment_class
    
    @classmethod
    def create(cls, config: ExperimentConfig) -> Experiment:
        """
        Factory method to create experiment based on config.system.
        
        Args:
            config: Experiment configuration
        
        Returns:
            Appropriate Experiment subclass instance
        
        Raises:
            ValueError: If system not supported
        """
        exp_class = cls._experiments.get(config.system.lower())
        if not exp_class:
            # Fallback: hardcoded for now until full registry implemented
            if config.system.lower() == 'trino':
                from tribench.experiments import TrinoExperiment
                enable_monitoring = config.raw_config.get('monitoring', {}).get('enabled', True)
                return TrinoExperiment(config, enable_monitoring=enable_monitoring)
            
            available = list(cls._experiments.keys())
            raise ValueError(
                f"No experiment implementation for system '{config.system}'. "
                f"Supported: {available if available else ['trino']}"
            )
        
        enable_monitoring = config.raw_config.get('monitoring', {}).get('enabled', True)
        return exp_class(config, enable_monitoring=enable_monitoring)


# Auto-register known implementations
try:
    from tribench.experiments import TrinoExperiment
    ExperimentRegistry.register("trino", TrinoExperiment)
except ImportError:
    pass  # TrinoExperiment not yet available

