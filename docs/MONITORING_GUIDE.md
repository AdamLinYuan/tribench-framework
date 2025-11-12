# TriBench Monitoring Guide

**Version:** 1.0  
**Last Updated:** November 2025

## Overview

TriBench provides comprehensive monitoring capabilities for tracking system resources, query performance, and experiment execution. This guide covers how to use the monitoring features effectively.

---

## Quick Start

### Automatic Monitoring (Recommended)

Monitoring is **automatically enabled** for all experiments by default:

```bash
# Run experiment - monitoring happens automatically
tribench exp run experiments/tpch-q1-tiny.yaml
```

Monitoring data is saved to `results/<experiment-name>/monitoring/` directory.

### Disable Monitoring via CLI

To run an experiment without monitoring:

```bash
# Disable monitoring for this run
tribench exp run experiments/tpch-q1-tiny.yaml --no-monitoring
```

Use this when:
- Testing experiment setup quickly
- Running on resource-constrained systems
- Debugging non-performance issues
- You only need result outcomes, not behavioral analysis

### Manual Monitoring Control

Disable monitoring for an experiment:

```python
from tribench.experiments import TrinoExperiment
from tribench.core.experiment import ExperimentConfig

config = ExperimentConfig.from_yaml("experiment.yaml")
experiment = TrinoExperiment(config, enable_monitoring=False)
```

---

## Features

### 1. System Resource Monitoring

Automatically collects:
- **CPU:** Per-core utilization, load average
- **Memory:** Used, available, cached, swap
- **Disk I/O:** Read/write bytes, operations per second
- **Network I/O:** Bytes/packets sent and received
- **Docker Containers:** Per-container CPU, memory, network

**Sampling Interval:** 1 second (configurable)

### 2. Trino Query Monitoring

Automatically tracks:
- **Query Execution:** Planning time, execution time, queued time
- **Resource Usage:** CPU time, peak memory, blocked time
- **Data Processing:** Input/output rows and bytes
- **Cluster Metrics:** Running queries, active nodes, queued queries
- **Query Plans:** Stage-level execution details

### 3. Alerts and Thresholds

Pre-configured alerts for:
- High memory usage (>90%)
- High CPU usage (>95%)
- Low disk space (>85%)
- Long-running queries (>5 minutes)

---

## Configuration

### Monitoring Configuration

Create `config/monitoring.conf` (optional):

```hocon
tribench {
  monitoring {
    # Enable/disable monitoring
    enabled = true
    
    # Sampling interval in seconds
    interval = 1.0
    
    # Storage configuration
    storage {
      path = "results/monitoring"
      compress = false  # Use gzip compression
      buffer_size = 1000  # Metrics before flush
    }
    
    # Resource monitoring
    resources {
      enabled = true
      collect_docker = true
    }
    
    # Trino monitoring
    trino {
      enabled = true
      track_queries = true
    }
    
    # Alerts
    alerts {
      enabled = true
      
      memory_threshold = 90.0  # percent
      cpu_threshold = 95.0  # percent
      disk_threshold = 85.0  # percent
      query_timeout = 300  # seconds
    }
  }
}
```

### Programmatic Configuration

```python
from tribench.monitoring import MonitoringConfig
from pathlib import Path

config = MonitoringConfig(
    enabled=True,
    interval=1.0,
    storage_path=Path("custom/monitoring/path"),
    buffer_size=1000,
)
```

---

## Usage Examples

### Example 1: Basic Experiment with Monitoring

```bash
# Run experiment (monitoring automatic)
tribench exp run experiments/tpch-q1-sf1.yaml

# View results including monitoring summary
tribench res show tpch-q1-sf1_20241103_120000
```

Output includes monitoring summary:
```json
{
  "experiment_name": "tpch-q1-sf1",
  "monitoring": {
    "enabled": true,
    "metrics_file": "results/tpch-q1-sf1/monitoring/metrics_20241103_120000.json",
    "summary": {
      "total_metrics": 15420,
      "duration_seconds": 257.3,
      "avg_cpu_percent": 45.2,
      "avg_memory_percent": 67.8,
      "peak_memory_bytes": 8589934592
    }
  }
}
```

### Example 2: Custom Monitoring Session

```python
from tribench.monitoring import (
    MonitoringSession,
    MonitoringConfig,
    ResourceMonitor,
    TrinoMonitor,
)
from pathlib import Path

# Create configuration
config = MonitoringConfig(
    enabled=True,
    interval=1.0,
    storage_path=Path("monitoring_data"),
)

# Create collectors
resource_monitor = ResourceMonitor(interval=1.0, collect_docker=True)
trino_monitor = TrinoMonitor(host="localhost", port=8080)

# Create session
session = MonitoringSession(
    config=config,
    collectors=[resource_monitor, trino_monitor],
    experiment_name="my_experiment",
)

# Start monitoring
session.start()

# ... run your workload ...

# Stop and save
session.stop()
metrics_file = session.save_metrics()
print(f"Metrics saved to: {metrics_file}")
```

### Example 3: Setting Up Alerts

```python
from tribench.monitoring import (
    AlertManager,
    AlertThreshold,
    AlertSeverity,
    ThresholdCondition,
    create_memory_alert,
    create_cpu_alert,
)

# Create alert manager
alerts = AlertManager()

# Add pre-configured alerts
alerts.add_threshold(create_memory_alert(threshold_percent=90.0))
alerts.add_threshold(create_cpu_alert(threshold_percent=95.0))

# Add custom alert
custom_alert = AlertThreshold(
    name="high_query_memory",
    metric_name="trino.query.memory.peak",
    condition=ThresholdCondition.GREATER_THAN,
    value=10 * 1024 * 1024 * 1024,  # 10 GB
    severity=AlertSeverity.WARNING,
    message="Query using excessive memory",
    consecutive_violations=2,
)
alerts.add_threshold(custom_alert)

# Check metrics against thresholds
fired_alerts = alerts.check_metrics(metrics)

# Get active alerts
active = alerts.get_active_alerts(severity=AlertSeverity.CRITICAL)
for alert in active:
    print(f"CRITICAL: {alert.message}")
```

### Example 4: Analyzing Monitoring Data

```python
from tribench.monitoring import MetricsStorage, TimeSeriesData
from pathlib import Path

# Load monitoring data
storage = MetricsStorage(storage_dir=Path("results/monitoring"))
data = storage.load_timeseries("experiment_20241103_120000.json")

# Filter metrics
cpu_metrics = data.filter_by_name("system.cpu.percent")
memory_metrics = data.filter_by_name("system.memory.percent")

# Compute statistics
summary = data.compute_summary()
print(f"CPU - Mean: {summary['system.cpu.percent']['mean']:.1f}%")
print(f"Memory - Peak: {summary['system.memory.percent']['max']:.1f}%")

# Export to CSV for analysis
storage.export_to_csv(data, Path("analysis/metrics.csv"))
```

### Example 5: Query-Level Analysis

```python
from tribench.monitoring import TrinoMonitor

# Create Trino monitor
monitor = TrinoMonitor(host="localhost", port=8080)
monitor.start()

# Get query metrics
query_id = "20241103_120000_00001_abcde"
query_metrics = monitor.get_query_metrics(query_id)

if query_metrics:
    print(f"Query: {query_metrics.query_id}")
    print(f"State: {query_metrics.state}")
    print(f"Execution Time: {query_metrics.execution_time_ms}ms")
    print(f"Peak Memory: {query_metrics.peak_memory_bytes / (1024**3):.2f} GB")
    print(f"Input Rows: {query_metrics.input_rows:,}")
    print(f"Output Rows: {query_metrics.output_rows:,}")

# Get stage-level metrics
stages = monitor.get_stage_metrics(query_id)
for stage in stages:
    print(f"\nStage {stage['stage_id']}:")
    print(f"  Tasks: {stage['completed_tasks']}/{stage['total_tasks']}")
    print(f"  CPU Time: {stage['total_cpu_time_ms']}ms")
    print(f"  Memory: {stage['peak_memory_bytes'] / (1024**2):.1f} MB")

# Get query plan
plan = monitor.get_query_plan(query_id)
if plan:
    print(f"\nQuery Plan:")
    print(f"  Root Stage: {plan['root_stage']['stage_id']}")
    print(f"  Sub-stages: {len(plan['root_stage']['sub_stages'])}")

monitor.stop()
```

---

## Metrics Reference

### System Metrics

| Metric Name | Type | Unit | Description |
|-------------|------|------|-------------|
| `system.cpu.percent` | gauge | percent | Total CPU utilization |
| `system.cpu.core.N.percent` | gauge | percent | Per-core CPU utilization |
| `system.memory.percent` | gauge | percent | Memory usage percentage |
| `system.memory.used` | gauge | bytes | Used memory |
| `system.memory.available` | gauge | bytes | Available memory |
| `system.disk.read_bytes` | counter | bytes | Disk bytes read |
| `system.disk.write_bytes` | counter | bytes | Disk bytes written |
| `system.network.sent_bytes` | counter | bytes | Network bytes sent |
| `system.network.recv_bytes` | counter | bytes | Network bytes received |

### Trino Cluster Metrics

| Metric Name | Type | Unit | Description |
|-------------|------|------|-------------|
| `trino.cluster.queries.running` | gauge | count | Currently running queries |
| `trino.cluster.queries.queued` | gauge | count | Queued queries |
| `trino.cluster.queries.blocked` | gauge | count | Blocked queries |
| `trino.cluster.nodes.active` | gauge | count | Active worker nodes |
| `trino.cluster.memory.reserved` | gauge | bytes | Reserved cluster memory |
| `trino.cluster.tasks.running` | gauge | count | Running tasks |

### Trino Query Metrics

| Metric Name | Type | Unit | Description |
|-------------|------|------|-------------|
| `trino.query.time.queued` | gauge | milliseconds | Time spent queued |
| `trino.query.time.planning` | gauge | milliseconds | Query planning time |
| `trino.query.time.execution` | gauge | milliseconds | Query execution time |
| `trino.query.time.elapsed` | gauge | milliseconds | Total elapsed time |
| `trino.query.cpu_time` | gauge | milliseconds | Total CPU time |
| `trino.query.memory.peak` | gauge | bytes | Peak memory usage |
| `trino.query.data.input.rows` | gauge | count | Input rows processed |
| `trino.query.data.input.bytes` | gauge | bytes | Input bytes processed |
| `trino.query.data.output.rows` | gauge | count | Output rows produced |
| `trino.query.data.output.bytes` | gauge | bytes | Output bytes produced |

---

## Output Files

### JSON Format

Metrics are stored in JSON format:

```json
{
  "experiment_name": "tpch-q1-sf1",
  "start_time": "2024-11-03T12:00:00.000000",
  "end_time": "2024-11-03T12:04:17.300000",
  "metrics": [
    {
      "timestamp": "2024-11-03T12:00:01.000000",
      "type": "gauge",
      "name": "system.cpu.percent",
      "value": 45.2,
      "unit": "percent",
      "labels": {"host": "localhost"}
    },
    ...
  ],
  "summary": {
    "system.cpu.percent": {
      "count": 257,
      "min": 12.5,
      "max": 98.3,
      "mean": 45.2,
      "median": 43.8,
      "stddev": 15.7
    }
  }
}
```

### CSV Format

Export metrics to CSV for external analysis:

```csv
timestamp,type,name,value,unit,host
2024-11-03T12:00:01.000000,gauge,system.cpu.percent,45.2,percent,localhost
2024-11-03T12:00:02.000000,gauge,system.cpu.percent,46.1,percent,localhost
...
```

---

## Best Practices

1. **Keep Monitoring Enabled:** Minimal overhead (<1% CPU, <50MB memory)

2. **Use Alerts:** Configure thresholds for critical resources

3. **Archive Data:** Compress old monitoring files with gzip

4. **Analyze Trends:** Export to CSV for pandas/R analysis

5. **Track Query IDs:** Use query IDs to correlate metrics with results

6. **Monitor Long Runs:** Essential for multi-hour experiments

7. **Check Summaries:** Review monitoring summaries after experiments

---

## Troubleshooting

### High Monitoring Overhead

If monitoring consumes too much resources:
- Increase sampling interval to 2-5 seconds
- Disable Docker container monitoring
- Reduce buffer size for more frequent flushes

### Missing Metrics

If some metrics are missing:
- Check collector is enabled in configuration
- Verify Trino is accessible on configured host/port
- Check Docker daemon is running (for container metrics)
- Review log files for errors

### Large Metric Files

For long-running experiments:
- Enable gzip compression (`compress = true`)
- Increase buffer size to reduce file I/O
- Implement periodic archival

---

## API Reference

See inline documentation for detailed API reference:

```python
help(MonitoringSession)
help(ResourceMonitor)
help(TrinoMonitor)
help(AlertManager)
help(MetricsStorage)
```

---

## Examples

Complete examples are available in:
- `tests/manual_test_monitoring.py` - Manual testing script
- `examples/monitoring/` - Additional examples (coming soon)

---

## Support

For issues or questions:
- Check logs in `log/` directory
- Review PHASE_3_1_SUMMARY.md for implementation details
- Open an issue on GitHub
