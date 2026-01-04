"""
Shared utilities for system commands.

Provides common functionality used across system command modules.
"""

from tribench.systems.kubernetes_system import KubernetesSystem
from tribench.defaults import Defaults


def get_k8s_system(config_tree=None):
    """Get configured KubernetesSystem instance."""
    # Try to detect context or use default
    context = Defaults.Kubernetes.CONTEXT
    
    # Check if context is defined in config
    if config_tree:
        context = config_tree.get("kubernetes.context", None)

    if not context:
        context = Defaults.Kubernetes.CONTEXT
        try:
            import subprocess
            # Check available contexts
            result = subprocess.run(["kubectl", "config", "get-contexts", "-o", "name"], capture_output=True, text=True)
            contexts = result.stdout.strip().split('\n')
            
            # Prioritize kind-tribench
            if Defaults.Kubernetes.CONTEXT in contexts:
                context = Defaults.Kubernetes.CONTEXT
            elif "docker-desktop" in contexts:
                context = "docker-desktop"
            # If neither, stick to default or maybe first available?
        except Exception:
            pass

    config = {
        "context": context,
        "namespace": Defaults.Kubernetes.NAMESPACE,
        "helm_chart": "trinodb/trino",
        "helm_release": Defaults.ServiceNames.TRINO,
        "minio_chart": "minio/minio",
        "minio_release": Defaults.ServiceNames.MINIO,
        "local_port": Defaults.Trino.PORT,
        "container_port": Defaults.Trino.PORT,
        "timeout": 600,
        "config_tree": config_tree,
        "kind_config": "config/kubernetes/kind-config.yaml",
    }
    return KubernetesSystem("k8s-system", config)
