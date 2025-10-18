# Utilities Directory

This directory contains utility scripts, SQL queries, and tools that complement the main framework.

## Structure

```
utils/
├── sql/                   # Utility SQL queries
│   ├── analysis/         # Result analysis queries
│   ├── monitoring/       # System monitoring queries
│   └── validation/       # Data validation queries
├── scripts/              # Shell and Python utilities
│   ├── deployment/       # Deployment helpers
│   ├── monitoring/       # Monitoring scripts
│   └── analysis/         # Analysis utilities
├── plotting/             # Visualization scripts
│   ├── performance.py    # Performance plotting
│   ├── comparison.py     # Suite comparison plots
│   └── templates/        # Plot templates
└── docker/               # Docker utilities
    ├── Dockerfile.trino
    └── docker-compose.monitoring.yml
```

## SQL Utilities

### Analysis Queries
```sql
-- utils/sql/analysis/query_performance.sql
SELECT 
    experiment_name,
    query_name,
    avg(execution_time_ms) as avg_time_ms,
    min(execution_time_ms) as min_time_ms,
    max(execution_time_ms) as max_time_ms,
    stddev(execution_time_ms) as stddev_time_ms
FROM experiment_results 
WHERE suite_name = ?
GROUP BY experiment_name, query_name
ORDER BY avg_time_ms DESC;
```

### Monitoring Queries
```sql  
-- utils/sql/monitoring/cluster_health.sql
SELECT 
    node_id,
    node_state,
    last_heartbeat,
    cpu_usage_pct,
    memory_usage_pct,
    active_queries
FROM trino.system.runtime.nodes;
```

## Script Utilities

### Deployment Helper
```bash
# utils/scripts/deployment/setup_cluster.sh
#!/bin/bash
# Automated cluster setup script

NODES="${1:-localhost}"
TRINO_VERSION="${2:-434}"

echo "Setting up Trino cluster on nodes: $NODES"
echo "Trino version: $TRINO_VERSION"

for node in $NODES; do
    echo "Configuring node: $node"
    # Node setup logic here
done
```

### Monitoring Script
```python
# utils/scripts/monitoring/resource_monitor.py
#!/usr/bin/env python3
"""
Real-time resource monitoring during benchmark execution
"""

import psutil
import time
import json
from datetime import datetime

class ResourceMonitor:
    def monitor(self, interval=5, output_file="metrics.json"):
        metrics = []
        
        while True:
            metric = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_io": psutil.disk_io_counters()._asdict(),
                "network_io": psutil.net_io_counters()._asdict()
            }
            
            metrics.append(metric)
            
            with open(output_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            time.sleep(interval)

if __name__ == "__main__":
    monitor = ResourceMonitor()
    monitor.monitor()
```

## Plotting Utilities

### Performance Visualization
```python
# utils/plotting/performance.py
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

def plot_query_performance(results_file, output_file):
    """Plot query execution times"""
    df = pd.read_json(results_file)
    
    plt.figure(figsize=(12, 8))
    sns.barplot(data=df, x='query_name', y='execution_time_ms')
    plt.title('Query Execution Times')
    plt.xlabel('Query')
    plt.ylabel('Execution Time (ms)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_file)

def plot_scalability(results_dir, output_file):
    """Plot scalability across different scale factors"""
    # Implementation here
    pass
```

## Docker Utilities

### Trino Dockerfile
```dockerfile
# utils/docker/Dockerfile.trino
FROM trinodb/trino:434

# Custom configurations
COPY trino-config/ /etc/trino/

# Custom catalogs
COPY catalogs/ /etc/trino/catalog/

EXPOSE 8080
```

### Monitoring Stack
```yaml
# utils/docker/docker-compose.monitoring.yml
version: '3.8'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-storage:/var/lib/grafana

volumes:
  grafana-storage:
```

## Usage Examples

```bash
# Run analysis query
tribench.sh db:query utils/sql/analysis/query_performance.sql

# Generate performance plots
python utils/plotting/performance.py results/tpch.sf1/

# Setup monitoring
docker-compose -f utils/docker/docker-compose.monitoring.yml up -d

# Deploy to cluster
utils/scripts/deployment/setup_cluster.sh "node1 node2 node3"
```
