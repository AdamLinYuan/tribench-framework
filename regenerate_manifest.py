from tribench.systems.kubernetes_system import KubernetesSystem
from tribench.utils.config import ConfigurationLoader
import logging

logging.basicConfig(level=logging.INFO)

loader = ConfigurationLoader()
config = loader.load()

# Create KubernetesSystem instance
k8s = KubernetesSystem("k8s", {"config_tree": config})

# Regenerate manifest
k8s._generate_hive_metastore_manifest()
print("Manifest regenerated.")
