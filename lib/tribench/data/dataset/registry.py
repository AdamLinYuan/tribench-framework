"""
Dataset registry management.

Handles tracking and persistence of dataset metadata.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from .metadata import DatasetMetadata

logger = logging.getLogger(__name__)


class DatasetRegistry:
    """Registry for tracking available datasets and their metadata."""
    
    def __init__(self, registry_path: Path):
        """
        Initialize dataset registry.
        
        Args:
            registry_path: Path to registry file (YAML)
        """
        self.registry_path = Path(registry_path)
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._datasets: Dict[str, DatasetMetadata] = {}
        self._load()
    
    def _load(self) -> None:
        """Load registry from disk."""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                data = yaml.safe_load(f) or {}
                self._datasets = {
                    name: DatasetMetadata.from_dict(meta)
                    for name, meta in data.items()
                }
            logger.info(f"Loaded {len(self._datasets)} datasets from registry")
    
    def _save(self) -> None:
        """Save registry to disk."""
        data = {
            name: meta.to_dict()
            for name, meta in self._datasets.items()
        }
        with open(self.registry_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved {len(self._datasets)} datasets to registry")
    
    def register(self, metadata: DatasetMetadata) -> None:
        """Register a new dataset."""
        self._datasets[metadata.name] = metadata
        self._save()
        logger.info(f"Registered dataset: {metadata.name}")
    
    def get(self, name: str) -> Optional[DatasetMetadata]:
        """Get dataset metadata by name."""
        return self._datasets.get(name)
    
    def list(self) -> List[DatasetMetadata]:
        """List all registered datasets."""
        return list(self._datasets.values())
    
    def delete(self, name: str) -> bool:
        """Remove dataset from registry."""
        if name in self._datasets:
            del self._datasets[name]
            self._save()
            logger.info(f"Deleted dataset from registry: {name}")
            return True
        return False
    
    def update(self, name: str, metadata: DatasetMetadata) -> None:
        """Update dataset metadata."""
        self._datasets[name] = metadata
        self._save()
        logger.info(f"Updated dataset: {name}")
