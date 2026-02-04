"""
Shared utilities for system commands.

Provides common functionality used across system command modules.
"""

from tribench.systems.kubernetes_system import KubernetesSystem
from tribench.defaults import Defaults


def get_k8s_system(config_tree=None):
    """Get configured KubernetesSystem instance.
    
    Args:
        config_tree: Configuration dictionary (ConfigTree or dict)
        
    Returns:
        KubernetesSystem instance with proper context from config hierarchy
    """
    # Build config dict with systems section for hierarchy
    config = {}
    if config_tree:
        # Extract kubernetes config if present (supports both ConfigTree and dict)
        # Use canonical path from reference.conf: tribench.kubernetes.context
        k8s_context = config_tree.get("tribench.kubernetes.context", None)
        k8s_namespace = config_tree.get("tribench.kubernetes.namespace", None)
        
        if k8s_context or k8s_namespace:
            config["systems"] = {
                "kubernetes": {}
            }
            if k8s_context:
                config["systems"]["kubernetes"]["context"] = k8s_context
            if k8s_namespace:
                config["systems"]["kubernetes"]["namespace"] = k8s_namespace

    config.update({
        "helm_chart": "trinodb/trino",
        "helm_release": Defaults.ServiceNames.TRINO,
        "minio_chart": "minio/minio",
        "minio_release": Defaults.ServiceNames.MINIO,
        "local_port": Defaults.Trino.PORT,
        "container_port": Defaults.Trino.PORT,
        "timeout": 600,
        "config_tree": config_tree,
        "kind_config": "config/kubernetes/kind-config.yaml",
    })
    
    return KubernetesSystem("k8s-system", config)
