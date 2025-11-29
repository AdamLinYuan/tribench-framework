import logging
import sys
import time
from tribench.systems.kubernetes_system import KubernetesSystem
from tribench.utils.config import ConfigurationLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("test_deployment")

def main():
    try:
        logger.info("Loading configuration...")
        loader = ConfigurationLoader()
        config = loader.load()
        
        # Initialize KubernetesSystem
        # We'll let it use the default context 'kind-tribench' or whatever is in config
        # If you need to override, you can pass "context": "docker-desktop" here
        k8s_config = {
            "config_tree": config,
            # "context": "docker-desktop" # Uncomment if needed
        }
        
        k8s = KubernetesSystem("tribench-k8s", k8s_config)
        
        logger.info(f"Using Kubernetes context: {k8s.context}")
        
        # 1. Setup (Generate Manifests)
        logger.info("--- Step 1: Setup (Generate Manifests) ---")
        k8s.setup("all")
        
        # 2. Teardown existing (Clean slate)
        logger.info("--- Step 2: Cleaning up existing resources ---")
        k8s.stop("all")
        time.sleep(5) # Give K8s a moment
        
        # 3. Start (Deploy)
        logger.info("--- Step 3: Deploying System ---")
        k8s.start("all")
        
        # 4. Check Status
        logger.info("--- Step 4: Checking Status ---")
        status = k8s.status()
        logger.info(f"System Status: {status}")
        
        if status.get("running"):
            logger.info("SUCCESS: Trino is running!")
        else:
            logger.warning("WARNING: Trino might not be fully running yet.")

    except Exception as e:
        logger.error(f"Deployment failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
