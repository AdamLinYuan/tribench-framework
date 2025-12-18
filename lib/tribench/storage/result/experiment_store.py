"""
Experiment storage operations.

Handles CRUD operations for Experiment entities.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from ..connection import get_db_session
from ..models import Experiment

logger = logging.getLogger(__name__)


class ExperimentStore:
    """Service for experiment-level database operations."""
    
    def create_or_get_experiment(
        self,
        name: str,
        experiment_type: str,
        config: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        dataset_name: Optional[str] = None,
        system_name: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> int:
        """
        Create a new experiment or get existing one by name.
        
        Args:
            name: Experiment name (unique identifier)
            experiment_type: Type of experiment (e.g., "trino")
            config: Full experiment configuration
            description: Optional description
            dataset_name: Dataset used (e.g., "tpch-sf1")
            system_name: System name (e.g., "trino")
            tags: Optional tags for categorization
            
        Returns:
            Experiment ID
        """
        with get_db_session() as session:
            # Check if experiment already exists
            experiment = session.query(Experiment).filter_by(name=name).first()
            
            if experiment:
                # Update configuration if changed
                experiment.config = config
                experiment.description = description or experiment.description
                experiment.dataset_name = dataset_name or experiment.dataset_name
                experiment.system_name = system_name or experiment.system_name
                experiment.tags = tags or experiment.tags
                experiment.updated_at = datetime.now()
                session.commit()
                logger.info(f"Updated existing experiment: {name} (ID: {experiment.id})")
            else:
                # Create new experiment
                experiment = Experiment(
                    name=name,
                    experiment_type=experiment_type,
                    config=config,
                    description=description,
                    dataset_name=dataset_name,
                    system_name=system_name,
                    tags=tags,
                )
                session.add(experiment)
                session.commit()
                logger.info(f"Created new experiment: {name} (ID: {experiment.id})")
            
            return experiment.id
    
    def get_experiment_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get experiment by name."""
        with get_db_session() as session:
            experiment = session.query(Experiment).filter_by(name=name).first()
            if not experiment:
                return None
            
            return self._experiment_to_dict(experiment)
    
    def get_experiment_by_id(self, experiment_id: int) -> Optional[Dict[str, Any]]:
        """
        Get experiment by ID.
        
        Args:
            experiment_id: Experiment ID
            
        Returns:
            Experiment dictionary or None if not found
        """
        with get_db_session() as session:
            experiment = session.query(Experiment).filter(Experiment.id == experiment_id).first()
            if not experiment:
                return None
            
            return self._experiment_to_dict(experiment)
    
    def list_experiments(
        self,
        experiment_type: Optional[str] = None,
        dataset_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List experiments with optional filtering.
        
        Args:
            experiment_type: Filter by experiment type
            dataset_name: Filter by dataset name
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of experiment dictionaries
        """
        with get_db_session() as session:
            query = session.query(Experiment)
            
            if experiment_type:
                query = query.filter_by(experiment_type=experiment_type)
            if dataset_name:
                query = query.filter_by(dataset_name=dataset_name)
            
            experiments = query.order_by(Experiment.created_at.desc()).limit(limit).offset(offset).all()
            
            return [
                {
                    "id": exp.id,
                    "name": exp.name,
                    "description": exp.description,
                    "experiment_type": exp.experiment_type,
                    "dataset_name": exp.dataset_name,
                    "system_name": exp.system_name,
                    "tags": exp.tags,
                    "created_at": exp.created_at,
                    "updated_at": exp.updated_at,
                    "run_count": len(exp.runs),
                }
                for exp in experiments
            ]
    
    @staticmethod
    def _experiment_to_dict(experiment: Experiment) -> Dict[str, Any]:
        """Convert Experiment ORM object to dictionary."""
        return {
            "id": experiment.id,
            "name": experiment.name,
            "description": experiment.description,
            "experiment_type": experiment.experiment_type,
            "dataset_name": experiment.dataset_name,
            "system_name": experiment.system_name,
            "config": experiment.config,
            "tags": experiment.tags,
            "created_at": experiment.created_at,
            "updated_at": experiment.updated_at,
        }
