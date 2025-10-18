# TriBench - Trino Benchmarking Framework

A framework for benchmarking SQL workloads on distributed data lakehouses using Apache Trino, inspired by the PEEL framework architecture.

## Overview

TriBench provides a systematic approach to:
- **Define** benchmark experiments with structured configurations
- **Execute** SQL workloads on Trino clusters with proper lifecycle management
- **Monitor** hardware resource usage and system performance
- **Analyze** results with structured reporting and visualization
- **Share** reproducible benchmark bundles

## Architecture

This framework follows a bundle-based architecture similar to PEEL:

```
tribench-framework/
├── bin/                    # Command-line interface
├── apps/                   # Benchmark applications and SQL workloads
├── config/                 # Environment and experiment configurations
├── datagens/              # Data generators (TPC-DS, TPC-H, custom)
├── datasets/              # Static datasets
├── downloads/             # System binaries and archives
├── lib/                   # Framework libraries
├── log/                   # Execution logs
├── results/               # Benchmark results and reports
├── systems/               # Running system installations
└── utils/                 # Utility scripts and tools
```

## Quick Start

1. **Setup Environment:**
   ```bash
   # Setup Python environment with Conda
   conda env create -f environment.yml
   conda activate tribench
   
   # Install TriBench in development mode
   pip install -e .
   
   # Verify installation
   tribench --version
   ```

2. **Configure Systems:**
   ```bash
   # Setup Trino system
   tribench sys setup trino
   
   # Start Trino
   tribench sys start trino
   
   # Check status
   tribench sys status trino
   ```

3. **Run Benchmark:**
   ```bash
   # Execute an experiment
   tribench exp run experiments/tpch-sf1.yaml
   
   # Run with dry-run mode
   tribench exp run experiments/tpch-sf1.yaml --dry-run
   
   # Run with multiple iterations
   tribench exp run experiments/tpch-sf1.yaml --runs 3 --warmup 1
   ```

4. **Analyze Results:**
   ```bash
   # Show experiment results
   tribench res show exp-001
   
   # List all results
   tribench res list
   
   # Analyze suite results
   tribench res analyze tpch-sf1 --report detailed
   
   # Export results
   tribench res export exp-001 --format csv
   ```

## Command Line Interface

TriBench provides a comprehensive CLI with the following command groups:

### System Management (`sys`)
```bash
tribench sys setup <system>      # Setup a system (trino, postgresql, minio)
tribench sys start <system>      # Start a system
tribench sys stop <system>       # Stop a system
tribench sys status [system]     # Check system status
tribench sys teardown <system>   # Tear down a system
```

### Experiment Execution (`exp`)
```bash
tribench exp run <file>          # Execute an experiment
tribench exp list                # List available experiments
tribench exp status <id>         # Check experiment status
tribench exp cancel <id>         # Cancel running experiment
tribench exp config <file>       # Show experiment configuration
```

### Dataset Management (`data`)
```bash
tribench data generate <dataset> # Generate a dataset (tpch-sf1, etc.)
tribench data load <dataset>     # Load dataset into system
tribench data list               # List available datasets
tribench data info <dataset>     # Show dataset information
tribench data validate <dataset> # Validate dataset integrity
```

### Result Analysis (`res`)
```bash
tribench res show <id>           # Show experiment results
tribench res list                # List all results
tribench res compare <ids...>    # Compare multiple results
tribench res export <id>         # Export results to file
tribench res analyze <suite>     # Analyze suite results
tribench res delete <id>         # Delete experiment results
```

### Common Options
```bash
--dry-run                        # Show what would be done without executing
--verbose, -v                    # Enable verbose output
--config, -c <file>              # Specify configuration file
--help                           # Show command help
```

### Examples

```bash
# Setup and start Trino
tribench sys setup trino --version 434 --dry-run
tribench sys start trino --verbose

# Generate and load TPC-H data
tribench data generate tpch-sf1 --format parquet
tribench data load tpch-sf1 --system trino --catalog iceberg

# Run experiments
tribench exp run experiments/tpch-sf1.yaml --runs 3
tribench exp status exp-001 --follow

# Analyze results
tribench res compare exp-001 exp-002 exp-003
tribench res analyze tpch-sf1 --report performance --plot
tribench res export exp-001 --format json --output results.json
```

## Supported Systems

- **Apache Trino**: Distributed SQL query engine
- **Apache Iceberg**: Open table format for data lakehouses
- **MinIO**: S3-compatible object storage (for distributed setups)
- **PostgreSQL**: Results database for analysis
- **Grafana**: Monitoring and visualization (optional)

## Supported Benchmarks

- **TPC-H**: Decision support benchmark
- **TPC-DS**: Data warehousing benchmark  
- **Custom SQL**: User-defined workloads
- **Microbenchmarks**: Individual query performance tests

## Key Features

- **Structured Experiment Definition**: XML/YAML-based experiment configurations
- **Environment Management**: Host-specific configurations and system lifecycle
- **Resource Monitoring**: CPU, memory, I/O, and network usage tracking
- **Result Storage**: Structured storage in databases for analysis
- **Reproducibility**: Version-controlled bundles for sharing
- **Extensibility**: Plugin architecture for custom benchmarks

## Development Status

This framework is currently under development as part of a dissertation project on benchmarking SQL workloads on distributed data lakehouses.

## License

Apache License 2.0
