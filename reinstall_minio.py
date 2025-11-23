from tribench.systems.kubernetes_system import KubernetesSystem
from tribench.utils.config import ConfigurationLoader
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

loader = ConfigurationLoader()
config = loader.load()

# Create KubernetesSystem instance
k8s_config = {
    "config_tree": config,
    "context": "docker-desktop"
}
k8s = KubernetesSystem("k8s", k8s_config)

logger.info("Uninstalling MinIO...")
k8s.stop("minio")

# Wait a bit for cleanup
time.sleep(10)

logger.info("Installing MinIO (Standalone)...")
k8s.start("minio")

logger.info("MinIO reinstallation complete.")
