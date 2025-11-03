# TriBench Development Plan - PEEL-Inspired Architecture

This document outlines the development plan for restructuring your Trino benchmarking framework following the PEEL framework architecture(https://github.com/peelframework/peel).

## Project Overview

**Goal**: Create a systematic, reproducible framework for benchmarking SQL workloads on distributed data lakehouses using Apache Trino, inspired by the PEEL framework's proven architecture.

**Target Architecture**: Bundle-based framework with structured experiment definition, automated execution, resource monitoring, and result analysis.

**Project Type**: MSc/BSc Dissertation Project

**Timeline**: 26 weeks (October 2025 - April 2026)
- **Development**: 22 weeks (Oct 2025 - Feb 2026)
- **Dissertation Writing**: Concurrent + 4 weeks dedicated (Mar-Apr 2026)

## Research Questions

### Primary Research Question
**"How can we design and implement a systematic, reproducible benchmarking framework for Apache Trino that supports executing batch workloads, monitoring resource usage, and generating structured performance reports across single-node and distributed cluster environments?"**

### Secondary Research Questions
1. **Framework Design**: What are the key abstractions and architectural patterns needed for a flexible, extensible Trino benchmarking framework (inspired by PEEL)?
2. **Workload Support**: How can the framework support both standardized benchmarks (TPC-H, TPC-DS) and user-defined SQL workloads with minimal configuration overhead?
3. **Resource Monitoring**: What metrics and monitoring approaches effectively capture Trino's distributed query execution behavior and resource utilization?
4. **Reproducibility**: What mechanisms ensure experiments are reproducible across different environments (local development, cluster deployments)?
5. **Framework Validation**: How does the framework perform when used to conduct actual performance studies (e.g., comparing Iceberg vs. Hive table formats)?

### Expected Contributions
1. **TribBench Framework**: A comprehensive, open-source benchmarking tool for Apache Trino that fills the gap left by lack of systematic performance testing tools (analogous to PEEL for Spark)
2. **Flexible Architecture**: Modular design supporting multiple storage formats (Iceberg, Hive, Memory), dataset generators (TPC-H, TPC-DS, custom), and execution environments (Docker local, cluster)
3. **Automated Workflows**: End-to-end automation of dataset generation, workload execution, resource monitoring, and report generation
4. **Validation Case Study**: Empirical performance analysis using the framework to compare table formats and demonstrate framework capabilities
5. **Extensibility**: Well-documented APIs and patterns enabling community contributions and custom extensions
6. **Reproducible Research**: Structured experiment definitions (YAML), result artifacts (JSON), and comprehensive documentation enabling reproduction of benchmarking studies

### Success Criteria
1. **Framework Functionality**: Successfully executes TPC-H and TPC-DS workloads with <1% failure rate
2. **Reproducibility**: Identical experiments produce consistent results (variance < 5%) across multiple runs
3. **Usability**: Complete setup time < 30 minutes on standard hardware
4. **Monitoring Coverage**: Captures CPU, memory, I/O, and Trino-specific metrics (query plans, execution stats)
5. **Scalability**: Framework operates on both single-node (local development) and multi-node (cluster) deployments
6. **Documentation**: Comprehensive user guides, API documentation, and example experiments
7. **Validation Study**: Framework enables meaningful performance analysis (e.g., format comparison study) demonstrating its research utility

## Phase 0: Foundation & Setup (Weeks 1-2) ⭐ START HERE

### 0.1 Development Environment
- [x] Repository structure setup
- [x] Basic README and configuration templates
- [ ] Python virtual environment configuration
- [ ] Git workflow and branching strategy
- [ ] Development journal setup

### 0.2 Python Package Structure
- [x] Create `lib/tribench/` package with proper `__init__.py`
- [x] Set up module structure:
  - [x] `cli/` - Command-line interface modules
  - [x] `core/` - Core abstractions (System, Experiment, Dataset)
  - [x] `systems/` - System implementations (Trino, PostgreSQL)
  - [x] `data/` - Dataset and data generation
  - [x] `monitoring/` - Resource monitoring
  - [x] `analysis/` - Result analysis and reporting
  - [x] `utils/` - Utility functions
- [x] Create `__version__.py` with version management
- [x] Set up proper Python imports and package metadata

### 0.3 Testing Infrastructure
- [x] Create `tests/` directory structure:
  - [x] `tests/unit/` - Unit tests for individual components
  - [x] `tests/integration/` - Integration tests for system interactions
  - [x] `tests/fixtures/` - Test fixtures and mock data
  - [x] `tests/conftest.py` - Pytest configuration
- [x] Set up pytest configuration (`pytest.ini`)
- [x] Configure code coverage reporting
- [x] Create mock objects for testing (MockSystem, MockExperiment)
- [x] Write first smoke tests

### 0.4 Core Abstractions
- [x] Define `System` abstract base class
- [x] Define `Experiment` abstract base class
- [x] Define `Dataset` abstract base class
- [x] Define `Result` data class
- [x] Create configuration schema classes
- [x] Implement basic validation logic

### 0.5 Development Tools
- [x] Set up `black` for code formatting
- [x] Set up `flake8` for linting
- [x] Configure `mypy` for type checking (optional but recommended)
- [x] Create `Makefile` for common tasks
- [x] Set up pre-commit hooks (optional)

**Deliverables**:
- Working Python package structure
- Basic test framework with 5+ passing tests
- Core abstract classes defined
- Development environment documented

**Time Estimate**: 2 weeks (with 40% buffer = 2.8 weeks)

## Phase 1: Minimal Viable Framework (Weeks 3-10)

### 1.1 Command Line Interface
- [x] Implement Python-based CLI system using Click (`tribench.sh` dispatcher)
- [x] Create command modules:
  - [x] `base.py` - Base CLI setup and common utilities
  - [x] `system_commands.py` - System lifecycle management (setup, start, stop, status)
  - [x] `experiment_commands.py` - Experiment execution (run, list, status)
  - [x] `data_commands.py` - Dataset management (generate, load, list)
  - [x] `result_commands.py` - Result viewing and basic analysis
- [x] Implement argument parsing and validation
- [x] Add command help text and examples
- [x] Implement dry-run mode for testing

### 1.2 Configuration System
- [x] Implement hierarchical configuration loading (HOCON-based with pyhocon)
- [x] Configuration layers: reference → host → experiment
- [x] Configuration validation and error reporting
- [x] Template-based system configuration generation
- [x] Environment variable substitution

### 1.3 System Management (Docker-Based Only)
- [x] Trino system lifecycle:
  - [x] Download Trino binary (automated wget/curl)
  - [x] Generate Docker Compose configuration from HOCON
  - [x] Setup command: create directories, configs, Docker compose
  - [x] Start command: docker-compose up with health checks
  - [x] Stop command: graceful shutdown
  - [x] Status command: check running containers and endpoints
  - [x] Teardown command: cleanup
- [x] Version management and downloads (cache in `downloads/`)
- [x] Basic health checks (HTTP endpoint polling)
- [x] Log collection and streaming

### 1.4 Basic Experiment Engine
- [x] Experiment definition parser (YAML)
- [x] SQL query execution via trino-python-client:
  - [x] Connection management
  - [x] Query submission and execution
  - [x] Result fetching with streaming
  - [x] Timeout handling
  - [x] Error handling and retry logic
- [x] Result collection:
  - [x] Execution time measurement
  - [x] Row count and data volume
  - [x] Query statistics from Trino API
  - [x] Storage in structured JSON format
- [x] Logging and error handling:
  - [x] Per-experiment log files
  - [x] Structured logging with levels
  - [x] Error aggregation and reporting

### 1.5 Dataset Management (Simplified)
- [x] TPC-H dataset generation using tpch-dbgen:
  - [x] Docker-based dbgen execution
  - [x] Parquet conversion using PyArrow
  - [x] Data validation (row counts, checksums)
- [x] Loading data into Trino:
  - [x] Memory connector (for testing)
  - [x] Create tables via SQL (DDL generation)
  - [x] Basic data loading framework
- [x] Dataset registry and metadata
- [x] CLI commands (generate, load, list, info, validate)
- [x] Comprehensive unit tests (19 tests)
- [x] Configuration integration

**Deliverables**:
- Functional CLI for system and experiment management
- Trino Docker setup working end-to-end
- TPC-H queries 1-5 executable via framework
- Results stored in structured format

**Time Estimate**: 8 weeks (with 40% buffer = 11 weeks)

## Phase 2: Core Benchmarking Capabilities (Weeks 11-16)

### 2.1 Extended Dataset Management
- [x] TPC-H data generation integration (SF1, SF10)
- [x] Iceberg table format support:
  - [x] PostgreSQL setup (Docker-based, for Hive Metastore backend)
  - [x] Hive Metastore integration (Docker-based)
  - [x] MinIO object storage setup
  - [x] Iceberg catalog configuration
  - [x] Table creation and data loading scripts
- [x] Dataset validation and checksums
- [x] Dataset metadata tracking

### 2.2 Benchmark Implementation (Focused Scope)
- [x] TPC-H query suite (all 22 queries available in `apps/tpch/queries/`)
- [x] Multiple runs with warm-up execution
  - [x] `runs` parameter for measured executions
  - [x] `warmup_runs` parameter for cache warming
  - [x] CLI flags: `--runs`, `--warmup`
- [x] Query result validation:
  - [x] Row count verification against expected TPC-H counts
  - [x] Result checksums (SHA256 for deterministic queries)
  - [x] Comparison with expected results by scale factor
- [x] Custom benchmark support (flexible query definition: inline, files, or dict format)
- [x] Experiment suites with hierarchical configuration merging
- **Advanced query parameterization (optional enhancement):** 
  - [ ] Jinja2 templating for SQL queries (Jinja2 available but not wired for queries)
  - [ ] Parameter substitution in queries (e.g., dynamic dates, thresholds)
  - [ ] Query variant generation from templates

**Deliverables**:
- TPC-H SF1 and SF10 datasets generated and loaded
- Iceberg tables created and validated
- All 22 TPC-H queries executable with validation
- Experiment suites working end-to-end
- Documentation for local deployments

**Time Estimate**: 6 weeks (with 40% buffer = 8.4 weeks)

---

## Phase 2.3: Workload Definition (OPTIONAL - Deferred to Phase 7)

**Status**: **OPTIONAL** - Basic experiment suite support in Phase 2.2 is sufficient for dissertation. Advanced orchestration features deferred to future work.

**Rationale**: Phase 2.2 already includes experiment suites with hierarchical configuration. Advanced features below are "nice-to-have" but not essential for framework validation.

### Features (If Pursued Later)
- [ ] Advanced workload specification format (YAML)
- [ ] Query sequencing and timing control
- [ ] Parallel query execution
- [ ] Execution orchestration and dependencies

**Time Estimate**: 2 weeks (if pursued in Phase 7)

---

## Phase 2.4: Secrets Management (Week 17)

**Status**: **SIMPLIFIED** - Focus on essential secrets management only. Full hybrid configuration system deferred to Phase 7.

### 2.4.1 Environment-Based Configuration
- [x] Create `.env.example` template for sensitive configuration
- [x] Add `.env` to `.gitignore`
- [x] Implement python-dotenv integration
- [x] Support for:
  - [x] Database passwords (PostgreSQL, Trino)
  - [x] Object storage credentials (MinIO access keys)
  - [x] API tokens
- [x] Documentation for secrets management

**Deliverables**:
- `.env.example` template with all secrets documented
- Secrets management working for Docker deployment
- Security best practices documented

**Time Estimate**: 1 week

**Note**: Full hybrid HOCON+.env configuration system with remote infrastructure support deferred to Phase 7 (optional enhancements).

---

## Phase 3: Monitoring and Analysis (Weeks 18-25)

**Rationale**: Monitoring infrastructure must be solid **before** Phase 4 Kubernetes deployment. Distributed systems require robust instrumentation for debugging, performance analysis, and validation. Starting monitoring in Week 18 (immediately after TPC-H completion) provides **10 weeks** of development and testing before cluster deployment begins in Week 28.

### 3.1 Resource Monitoring
- [ ] System resource monitoring:
  - [ ] CPU utilization per core (via psutil or docker stats)
  - [ ] Memory usage (RSS, VMS, swap) per container
  - [ ] Disk I/O (read/write bytes, IOPS) per volume
  - [ ] Network I/O (bytes sent/received) per container
  - [ ] Time-series collection at configurable intervals (default: 1s)
- [ ] Trino-specific metrics collection via JMX:
  - [ ] Query execution metrics (planning time, execution time, wall time)
  - [ ] Data processing metrics (input/output rows, bytes scanned, bytes returned)
  - [ ] Resource usage per query (peak memory, CPU time, blocked time)
  - [ ] Cluster metrics (active workers, queued queries, running queries)
  - [ ] Connector-specific metrics (Iceberg snapshot reads, Hive partitions scanned)
- [ ] Query-level performance metrics:
  - [ ] Query plan collection and storage
  - [ ] Stage-level execution times
  - [ ] Operator-level statistics
  - [ ] Explain plan analysis
- [ ] Real-time monitoring during experiments:
  - [ ] Live dashboard (optional: simple web UI)
  - [ ] Progress tracking and ETA calculation
  - [ ] Alert thresholds (OOM, timeout warnings)
- [ ] Metrics storage in structured format:
  - [ ] Time-series JSON format for resource metrics
  - [ ] CSV export for analysis in external tools
  - [ ] Integration with results database

### 3.2 Result Storage
- [ ] Structured result database schema
- [ ] PostgreSQL integration for results
- [ ] Result archiving and compression
- [ ] Data export capabilities (CSV, JSON, Parquet)

### 3.3 Analysis Engine
- [ ] Performance analysis algorithms
- [ ] Statistical analysis (mean, median, stddev, percentiles)
- [ ] Scalability analysis (speed-up, scale-up)
- [ ] Regression detection
- [ ] Comparison analysis (baseline vs. current)

### 3.4 Visualization and Reporting
- [ ] HTML report generation (Jinja2 templates)
- [ ] Interactive performance plots (matplotlib, plotly)
- [ ] Comparison visualizations
- [ ] Executive summary reports
- [ ] Automated report generation pipeline

**Deliverables**:
- Resource monitoring working during experiments (single-node)
- Results stored in PostgreSQL database
- Basic statistical analysis implemented
- HTML reports with visualizations
- Monitoring framework ready for cluster instrumentation (Phase 4)

**Time Estimate**: 7 weeks (with 40% buffer = 9.8 weeks)

**Dependencies**: Phase 2.2 complete (TPC-H benchmark operational)

---

## Phase 4: Cluster Deployment & Distributed Execution (Weeks 26-34)

**Status**: **REQUIRED** for dissertation completion - framework must demonstrate scalability to distributed environments

**Note**: This phase sets up the infrastructure needed for distributed benchmarking before conducting validation studies in Phase 5.

### 4.1 Multi-Node Architecture Design
- [ ] Design distributed Trino cluster architecture:
  - [ ] Single coordinator + multiple workers configuration
  - [ ] Shared storage layer (MinIO/S3 for data files)
  - [ ] Distributed Hive Metastore configuration
  - [ ] Network topology and service discovery
- [ ] Framework abstractions for cluster deployment:
  - [ ] `ClusterSystem` abstraction (extends `System`)
  - [ ] Node role management (coordinator vs worker)
  - [ ] Cluster configuration profiles
  - [ ] Dynamic worker scaling support
- [ ] Resource allocation strategy:
  - [ ] CPU/memory per node type
  - [ ] Storage requirements calculation
  - [ ] Network bandwidth considerations
  - [ ] Configuration validation for cluster resources

### 4.2 Kubernetes Deployment
- [ ] Kubernetes infrastructure setup:
  - [ ] Helm charts for Trino cluster
  - [ ] StatefulSets for coordinator and workers
  - [ ] Persistent volumes for data storage
  - [ ] ConfigMaps for Trino configuration
  - [ ] Services for internal communication
- [ ] Cluster orchestration:
  - [ ] Node affinity and pod placement
  - [ ] Resource requests and limits
  - [ ] Health checks and readiness probes
  - [ ] Rolling updates and zero-downtime deployments
- [ ] School cluster deployment:
  - [ ] Kubernetes namespace setup
  - [ ] Resource quota configuration
  - [ ] Ingress for external access
  - [ ] Storage class configuration
- [ ] Alternative: Docker Compose multi-node (fallback):
  - [ ] Coordinator service definition
  - [ ] Worker service template (replicable)
  - [ ] Shared volume mounts for data
  - [ ] Network bridge configuration

### 4.3 Distributed Monitoring & Orchestration
- [ ] Cluster-wide resource monitoring:
  - [ ] Per-node metrics collection (CPU, memory, network, disk I/O)
  - [ ] Coordinator-specific metrics (query coordination overhead)
  - [ ] Worker-specific metrics (task execution, data shuffling)
  - [ ] Aggregate cluster metrics (total throughput, utilization)
- [ ] Distributed experiment execution:
  - [ ] Cluster health checks before experiments
  - [ ] Coordinated data loading across nodes
  - [ ] Distributed query execution tracking
  - [ ] Node failure detection and handling
- [ ] Result aggregation:
  - [ ] Coordinator collects results from all workers
  - [ ] Distributed tracing for query execution paths
  - [ ] Per-node performance breakdown
  - [ ] Network overhead measurement

### 4.4 Cluster Configuration Management
- [ ] Environment-specific configurations:
  - [ ] Local development (Docker Compose)
  - [ ] School cluster (Kubernetes)
  - [ ] Configuration templating (Jinja2)
  - [ ] Environment variable management
- [ ] Framework integration:
  - [ ] Automatic environment detection
  - [ ] Cluster-aware experiment execution
  - [ ] Distributed result collection
  - [ ] Cluster lifecycle management (start/stop/scale)

### 4.5 Documentation & User Guidance
- [ ] Kubernetes deployment guide:
  - [ ] Prerequisites (kubectl, helm, cluster access)
  - [ ] Step-by-step deployment instructions
  - [ ] Configuration examples for different cluster sizes
  - [ ] Troubleshooting common issues
- [ ] School cluster-specific documentation:
  - [ ] Resource request procedures
  - [ ] Job submission workflows
  - [ ] Storage access patterns
  - [ ] Example experiment configurations
- [ ] Migration guide:
  - [ ] Converting single-node experiments to cluster-ready
  - [ ] Configuration changes needed
  - [ ] Expected behavior changes (timing, resource usage)

**Time Estimate**: 8 weeks (with 40% buffer = 11.2 weeks)

**Deliverables**:
- Kubernetes deployment with Helm charts working end-to-end
- Framework supports both single-node and cluster execution modes
- School cluster deployment validated (or Docker multi-node fallback)
- Cluster-aware monitoring and orchestration operational
- Comprehensive documentation for cluster deployment

**Risks**:
- **High Priority**: School cluster access timing and resource availability
- **High Priority**: Kubernetes learning curve if unfamiliar
- **Medium**: Network complexity in distributed setup
- **Medium**: Hive Metastore distributed configuration complexity

**Dependencies**:
- Phase 2.2 complete (TPC-H benchmark operational)
- **Phase 3 complete** (Monitoring infrastructure solid and tested on single-node)
- School cluster access secured (initiate request early - **ACTION: Apply Week 1**)
- Basic Kubernetes knowledge (can learn in parallel during Phase 3)

---

## Phase 5: Framework Validation & Case Studies (Weeks 35-42)

**Note**: This phase focuses on **validating the framework itself** through comprehensive testing and demonstrating its utility via performance studies. Cluster infrastructure from Phase 4 enables distributed validation.

### 5.1 Framework Validation Testing
- [ ] Reproducibility study:
  - [ ] Run identical experiments 10 times (single-node and cluster)
  - [ ] Measure variance across runs (target: <5%)
  - [ ] Document sources of variance (caching, OS scheduling, etc.)
  - [ ] Test reproducibility across different hardware configurations
- [ ] Scalability testing:
  - [ ] Single-node baseline performance (local Docker)
  - [ ] Multi-node performance on School cluster (Kubernetes)
  - [ ] Worker scaling experiments (1, 2, 4 workers)
  - [ ] Speed-up ratio and scale-up efficiency measurement
  - [ ] Multi-node coordination overhead measurement
  - [ ] Resource utilization efficiency analysis
- [ ] Usability evaluation:
  - [ ] Setup time measurement on fresh system
  - [ ] Documentation completeness check
  - [ ] External user testing (if possible - classmates, supervisor)
  - [ ] Common failure scenarios and error handling validation
- [ ] Framework overhead measurement:
  - [ ] Framework instrumentation overhead vs raw Trino execution
  - [ ] Target: <5% overhead for query execution
  - [ ] Monitoring impact on performance
  - [ ] Result collection and storage overhead

### 5.2 Performance Case Study: Table Format Comparison
**Purpose**: Demonstrate framework capabilities through a meaningful research study

- [ ] Experimental design:
  - [ ] Compare Iceberg vs Hive vs Memory connectors
  - [ ] Use TPC-H SF10 dataset across all formats
  - [ ] Select representative queries (simple, medium, complex)
  - [ ] Control variables (same hardware, same Trino config)
  - [ ] Run on both single-node and cluster deployments
- [ ] Iceberg-specific experiments:
  - [ ] Time travel query performance
  - [ ] Schema evolution overhead
  - [ ] Partition pruning effectiveness (partitioned vs non-partitioned)
  - [ ] Snapshot metadata overhead
- [ ] Distributed execution analysis:
  - [ ] Single-node vs multi-node comparison for same workload
  - [ ] Query types benefiting most from distribution
  - [ ] Network overhead in distributed Iceberg reads
  - [ ] Break-even points for cluster usage
- [ ] Data collection:
  - [ ] 5 runs per configuration
  - [ ] Full resource monitoring enabled
  - [ ] Query plan analysis
  - [ ] Statistical significance testing
- [ ] Analysis and insights:
  - [ ] Performance comparison by query type
  - [ ] Resource utilization patterns
  - [ ] Identify when Iceberg overhead is justified
  - [ ] Recommendations for format selection

### 5.3 Workload Study: TPC-H Characteristics (Optional: TPC-DS Comparison)
**Purpose**: Validate framework with standard benchmark workload

- [ ] TPC-H workload characterization:
  - [ ] Query complexity distribution (22 queries)
  - [ ] Execution time patterns
  - [ ] Resource consumption patterns
  - [ ] Join complexity and selectivity
- [ ] Framework stress testing:
  - [ ] Run full TPC-H suite (22 queries) on single-node
  - [ ] Run full TPC-H suite on cluster (2-4 workers)
  - [ ] Long-running experiment stability (>4 hours)
  - [ ] Failure recovery and retry mechanisms
- [ ] **Optional**: TPC-DS comparison (if Phase 2.5 completed):
  - [ ] Run TPC-DS subset (20 representative queries)
  - [ ] Compare TPC-H vs TPC-DS execution patterns
  - [ ] Document framework behavior differences
- [ ] Documentation of findings:
  - [ ] Framework strengths and limitations discovered
  - [ ] Performance bottlenecks identified
  - [ ] Recommended best practices for users

### 5.4 Additional Study (Choose ONE based on time/interest)

**Option A: Storage Format Comparison**
- [ ] Parquet vs ORC performance on TPC-H
- [ ] Compression algorithm comparison (SNAPPY, GZIP, ZSTD)
- [ ] File size vs query performance trade-offs
- [ ] Storage format selection guidelines

**Option B: Workload Optimization Study**
- [ ] Query pattern analysis (scans, joins, aggregations)
- [ ] Resource usage prediction models
- [ ] Workload classification framework
- [ ] Query optimization opportunities

**Option C: Cluster Scaling Deep Dive**
- [ ] Detailed analysis of 1, 2, 4 worker configurations
- [ ] Network bandwidth impact on performance
- [ ] Memory vs CPU bottleneck identification
  - [ ] Cost-performance analysis for cluster sizing

### 5.5 Documentation and Examples
- [ ] Comprehensive user documentation
- [ ] Developer guides and API documentation
- [ ] Example benchmark bundles
- [ ] Tutorial: Creating custom experiments
- [ ] Troubleshooting guide
- [ ] Case study write-ups for dissertation

**Deliverables**:
- Framework validation results (reproducibility, scalability, overhead)
- Performance case study completed (Iceberg vs Hive comparison)
- TPC-H workload analysis
- Insights and recommendations documented
- Framework fully documented

**Time Estimate**: 7 weeks (with 40% buffer = 9.8 weeks)

---

## Phase 6: TPC-DS Benchmark Support (OPTIONAL - Future Work)

**Status**: Truly optional - pursue only if time permits and interest exists after Phase 5 complete

**Note**: TPC-DS implementation moved to optional phase since TPC-H provides sufficient workload diversity for framework validation and dissertation requirements.

### 6.1 TPC-DS Dataset Generation
- [ ] Integrate TPC-DS data generator (dsdgen)
- [ ] Support SF1, SF10 scale factors
- [ ] Parquet conversion for 24 TPC-DS tables
- [ ] Row count validation against spec

### 6.2 TPC-DS Query Subset
- [ ] Implement 20-30 representative queries (not full 99)
- [ ] Focus on queries demonstrating different patterns
- [ ] Add Jinja2 templating for parameters
- [ ] Validate Trino compatibility

### 6.3 TPC-DS Workload Configuration
- [ ] Create TPC-DS experiment templates
- [ ] Query complexity categorization
- [ ] Comparison study vs TPC-H

**Time Estimate**: 3-4 weeks for subset implementation

---

## Phase 7: Additional Optional Enhancements (Post-Core)

**Status**: Truly optional - pursue only if significant time remains after Phase 5

### 7.1 Advanced Workload Orchestration (Deferred from Phase 2.3)
- [ ] Advanced workload specification format (YAML)
- [ ] Query sequencing and timing control
- [ ] Parallel query execution
- [ ] Execution orchestration and dependencies
- [ ] Experiment chaining

### 7.2 Flexible Configuration System (Deferred from Phase 2.4)
- [ ] Full hybrid HOCON+.env configuration system
- [ ] Remote infrastructure configuration:
  - [ ] Support for remote Trino clusters
  - [ ] Cloud object storage (AWS S3, MinIO endpoints)
  - [ ] External Hive Metastore (custom URIs)
  - [ ] External PostgreSQL (custom connection strings)
- [ ] Environment-specific configs (local, staging, production)
- [ ] Configuration validation and migration guides

### 7.3 Advanced Cloud Deployment
- [ ] AWS deployment guide (EMR or EKS)
- [ ] Azure deployment guide (AKS)
- [ ] Terraform modules for infrastructure as code

### 7.4 CI/CD Integration
- [ ] GitHub Actions workflow for automated testing
- [ ] Docker image builds and publishing
- [ ] Benchmark regression testing

### 7.5 Advanced Analytics
- [ ] Machine learning for performance prediction
- [ ] Query execution time prediction models
- [ ] Resource requirement estimation
- [ ] Anomaly detection in performance metrics

### 7.6 Advanced Visualization
- [ ] Interactive dashboards (Grafana/Prometheus)
- [ ] Query plan visualizations
- [ ] Performance trend analysis over time

**Note**: Pick MAX ONE-TWO items from Phase 7 if time permits after Phase 5 completion.

---

## Phase 8: Dissertation Writing & Final Polish (Weeks 18-42, Concurrent)

### 8.1 Documentation Completion
- [ ] Comprehensive user documentation
- [ ] API reference documentation
- [ ] Architecture documentation
- [ ] Deployment guides
- [ ] Example benchmark bundles

### 8.2 Dissertation Writing
- [ ] **Literature Review**: Benchmarking frameworks (PEEL, TPC benchmarks), distributed query engines, data lakehouse architectures, Kubernetes orchestration
- [ ] **Methodology Chapter**: Framework design principles, PEEL-inspired abstractions, architecture decisions, Kubernetes deployment strategy, extensibility approach
- [ ] **Implementation Chapter**: Core components (System, Experiment, Dataset abstractions), TPC-H integration, monitoring infrastructure, Kubernetes cluster deployment
- [ ] **Evaluation Chapter**: 
  - [ ] Framework validation (reproducibility, scalability, overhead measurement)
  - [ ] Performance case studies (table format comparison on single-node and cluster)
  - [ ] Distributed execution analysis (cluster scaling experiments)
  - [ ] Workload characterization (TPC-H analysis)
- [ ] **Comparison with Related Work**: TriBench vs PEEL, framework design trade-offs, contribution uniqueness
- [ ] **Conclusions and Future Work**: Framework contributions, limitations discovered, TPC-DS as future extension

### 8.3 Final Polish
- [ ] Code refactoring and cleanup
- [ ] Performance optimization
- [ ] Bug fixes and edge cases
- [ ] Final benchmark runs for dissertation (single-node and cluster)
- [ ] Prepare demo/presentation materials

**Deliverables**:
- Complete dissertation draft (10,000-15,000 words)
- Fully documented framework with Kubernetes deployment guides
- Reproducible benchmark results with data (single-node and cluster)
- Demo materials for presentation

**Time Estimate**: 4-6 weeks dedicated writing + concurrent work throughout phases

---

## Timeline Summary with Revised Estimates

| Phase | Description | With Buffer | Weeks | Milestone |
|-------|-------------|-------------|-------|-----------|
| **Phase 0** | Foundation & Testing Setup | 3 weeks | 1-3 | Project structure, CI/CD |
| **Phase 1** | Minimal Viable Framework | 11 weeks | 4-14 | Basic benchmarking working |
| **Phase 2.1-2.2** | Core Benchmarking (TPC-H, Iceberg) | 6 weeks | 15-16 | TPC-H suite complete |
| **Phase 2.3** | **Workload Orchestration (OPTIONAL)** | **Deferred** | **-** | **Moved to Phase 7** |
| **Phase 2.4** | Secrets Management | 1 week | 17 | .env configuration |
| **Phase 3** | **Monitoring & Analysis** | **10 weeks** | **18-27** | **Resource monitoring ready** |
| **Phase 4** | **Kubernetes Cluster Deployment** | **11 weeks** | **28-38** | **Multi-node capability** |
| **Phase 5** | Framework Validation & Case Studies | 10 weeks | 39-48 | Reproducibility, performance studies |
| **Phase 6** | **TPC-DS Subset (OPTIONAL)** | **~4 weeks** | **-** | **If time permits** |
| **Phase 7** | Additional Enhancements (OPTIONAL) | - | - | Deferred features, cloud, CI/CD |
| **Phase 8** | Writing & Polish | Concurrent | 18-48 | Dissertation completion |

**Revised Total Timeline**: 
- **Core Implementation (Phases 0-5)**: ~48 weeks with buffer
- **Previous estimate**: ~49 weeks
- **Time saved**: ~1 week by simplifying Phase 2.4
- **Key improvement**: **Phase 3 monitoring now has 10 weeks before Phase 4 cluster deployment** (vs 8 weeks previously)

**Key Changes from Previous Plan**:
1. ✅ **Phase 2.3 (Workload Orchestration) made optional** - Deferred to Phase 7, basic suite support sufficient
2. ✅ **Phase 2.4 simplified to 1 week** - Only secrets management (.env), full hybrid config deferred to Phase 7
3. ✅ **Phase 3 moved to Weeks 18-27** - 10-week buffer before Kubernetes (vs 8 weeks), starts immediately after TPC-H
4. ✅ **Phase 4 updated to Weeks 28-38** - Depends on solid monitoring from Phase 3
5. ✅ **Phase 5 updated to Weeks 39-48** - Uses cluster infrastructure from Phase 4
6. ✅ **Clean dependency chain**: TPC-H (Week 16) → Monitoring (Weeks 18-27) → Kubernetes (Weeks 28-38) → Validation (Weeks 39-48)

**Critical Improvement**: 
- **Before**: Phase 3 started Week 21, Phase 4 started Week 29 = 8 weeks gap
- **After**: Phase 3 starts Week 18, Phase 4 starts Week 28 = **10 weeks gap**
- **Benefit**: More time to solidify monitoring infrastructure before distributed system complexity. Reduces risk of debugging Kubernetes cluster without proper instrumentation.

**Rationale for Phase Reordering**:
- **Monitoring First**: Distributed systems (Kubernetes) require robust instrumentation. Building monitoring after cluster deployment is backwards - you'd be debugging blind.
- **Clean Dependencies**: Each phase now properly depends on previous phase completion. No awkward gaps or circular dependencies.
- **Simplified Scope**: Phase 2.3 (advanced orchestration) and full Phase 2.4 (hybrid config) are nice-to-have, not blockers. Basic features sufficient for validation.
- **Risk Reduction**: 10 weeks of monitoring development ensures framework can properly observe single-node behavior before tackling distributed complexity.

---

## Risk Assessment & Mitigation Strategies

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Timeline overrun (52 weeks > 26 weeks)** | **CRITICAL** | **CRITICAL** | **SEE MITIGATION PLAN BELOW** |
| Multi-node complexity | **HIGH** | **HIGH** | Start cluster access early, test on School resources by Week 30, Docker Swarm as simpler alternative to K8s |
| TPC-DS scope (99 queries) | **HIGH** | **HIGH** | Implement subset initially (20 queries), document framework support for full suite |
| School cluster access delay | **MEDIUM** | **HIGH** | Apply for access immediately, have Docker multi-host fallback, document process for future users |
| Technical complexity (Trino/Iceberg) | **MEDIUM** | **HIGH** | Start simple (Docker only), use stable versions, extensive testing |
| Scope creep beyond spec | **MEDIUM** | **HIGH** | Defer Phase 6 completely, focus on research questions, strict phase gates |
| Research contribution unclear | **LOW** | **CRITICAL** | Framework as primary contribution (aligned with spec), regular advisor meetings |
| Distributed monitoring complexity | **MEDIUM** | **MEDIUM** | Per-node metrics first, aggregate later, use existing tools (docker stats, JMX) |
| Testing insufficient for cluster | **MEDIUM** | **HIGH** | Test-driven development, mock cluster scenarios, integration tests |

### Critical Timeline Mitigation Plan

**Option A: Scope Reduction (RECOMMENDED)**
- **TPC-DS**: Implement 20 representative queries (instead of 99), document framework's ability to support full suite
  - Time saved: ~3 weeks
  - Justification: Framework design matters more than complete query coverage
- **Multi-Node**: Deploy 2-node cluster (coordinator + 1 worker) instead of 4-8 nodes
  - Time saved: ~4 weeks
  - Justification: Demonstrates scalability concept, full scaling in Future Work
- **Phase 3 Monitoring**: Basic metrics only (CPU, memory, query time), defer advanced JMX
  - Time saved: ~2 weeks
  - Justification: Sufficient for performance comparison studies
- **Total Time Saved**: ~9 weeks → brings total to **43-47 weeks** (still over)

**Option B: Aggressive Parallelization**
- Work on TPC-DS (Phase 2.5) and Monitoring (Phase 3) concurrently
  - Risk: Context switching overhead
  - Benefit: Saves 2-3 weeks
- Start cluster access applications during Phase 2
  - Benefit: Reduces waiting time in Phase 5
  - Action: Apply for School cluster Week 1

**Option C: Hybrid Approach (RECOMMENDED + REALISTIC)**
1. **Immediate Actions**:
   - Apply for School cluster access (Week 1)
   - Scope TPC-DS to 20-30 queries with framework support for rest
   - Target 2-4 node cluster (not 8-node)
   - Basic monitoring only (defer Grafana/Prometheus)

2. **Revised Timeline**: **38-42 weeks** (achievable)
   - Phase 2.5 (TPC-DS): 3 weeks (20 queries)
   - Phase 3 (Monitoring): 6 weeks (basic metrics)
   - Phase 4 (Validation): 6 weeks (as planned)
   - Phase 5 (Cluster): 8 weeks (2-node deployment)

3. **Success Criteria**:
   - ✅ Framework functional for TPC-H (22 queries) and TPC-DS subset (20 queries)
   - ✅ Single-node and 2-node deployment working
   - ✅ Basic resource monitoring (CPU, memory, query execution)
   - ✅ Validation study: Iceberg vs Hive on single-node and 2-node
   - ✅ Reproducibility and framework overhead measured
   - ⏭️ Future Work: Full TPC-DS (99 queries), 8-node scalability, advanced monitoring

4. **Advisor Discussion Points**:
   - Confirm scope reduction acceptable for dissertation
   - Clarify minimum cluster requirements (2-node sufficient?)
   - Discuss TPC-DS query count (20 vs 99)
   - Timeline feasibility check (38-42 weeks realistic?)

---

## Revised Success Metrics

### Framework Functionality (Primary Contribution)
- **System Management**: Docker-based Trino cluster (single-node + 2-node) with lifecycle management
- **Benchmark Support**: TPC-H (22 queries) + TPC-DS subset (20-30 queries) fully operational
- **Experiment Execution**: Configuration, execution, validation, result collection working end-to-end
- **Resource Monitoring**: Per-container CPU, memory, query execution metrics collection
- **Extensibility**: Documented abstractions allowing new benchmarks/systems to be added
- **Test Coverage**: >75% coverage for core components

### Monitoring Coverage
- **System Resources**: CPU (per core), memory (RSS/VMS), disk I/O, network I/O
- **Query Metrics**: Execution time, rows processed, bytes scanned, planning time
- **Trino JMX Metrics** (basic): Query count, active queries, failed queries
- **Time-Series Data**: 1-second interval collection during experiments

### Scalability
- **Single-Node Deployment**: Local Docker Compose with all services
- **Multi-Node Deployment**: 2-node cluster (coordinator + worker) on School cluster OR Docker multi-host
- **Scalability Study**: Performance comparison (1-node vs 2-node) for representative workload

### Documentation
- **User Guide**: Setup, configuration, running benchmarks, interpreting results
- **Developer Guide**: Architecture, abstractions, adding benchmarks, extending systems
- **Deployment Guide**: Single-node and cluster deployment procedures
- **API Documentation**: Core classes and methods documented

### Validation Study (Demonstrates Framework Utility)
- **Format Comparison**: Iceberg vs Hive tables on TPC-H queries
- **Reproducibility**: <5% variance across identical runs
- **Framework Overhead**: <5% measurement overhead
- **Research Insights**: ≥3 actionable findings from performance studies

### Dissertation Quality
- **Word Count**: 10,000-15,000 words
- **Structure**: Introduction, Literature Review, Methodology (framework design), Implementation, Evaluation (validation studies), Related Work Comparison, Conclusions
- **Figures/Tables**: 20+ visualizations (architecture diagrams, performance graphs, comparison tables)
- **References**: 30+ academic sources (benchmarking, distributed systems, data lakehouses)
- **Reproducibility**: Code, data, and instructions for replicating all experiments

---

## Technology Stack & Development Details

### Technology Stack
- **Core Framework**: Python 3.11+
- **Configuration**: HOCON (pyhocon library)
- **CLI**: Click framework
- **Database**: PostgreSQL for results
- **Containerization**: Docker, Docker Compose
- **SQL Client**: trino-python-client
- **Data Processing**: pandas, PyArrow
- **Visualization**: matplotlib, plotly, seaborn
- **Testing**: pytest, pytest-cov, pytest-mock
- **Code Quality**: black, flake8, mypy

### Development Workflow
1. **Test-Driven Development**: Write tests before implementation
2. **Incremental Development**: Build and test one component at a time
3. **Continuous Integration**: Run tests on every commit
4. **Documentation**: Document as you code
5. **Version Control**: Regular commits with meaningful messages

### Project Structure
```
tribench-framework/
├── bin/
│   └── tribench.sh              # Main CLI entry point
├── lib/
│   └── tribench/
│       ├── __init__.py
│       ├── __version__.py
│       ├── cli/                 # Command-line interface
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── system_commands.py
│       │   ├── experiment_commands.py
│       │   ├── data_commands.py
│       │   └── result_commands.py
│       ├── core/                # Core abstractions
│       │   ├── __init__.py
│       │   ├── system.py
│       │   ├── experiment.py
│       │   ├── dataset.py
│       │   └── result.py
│       ├── systems/             # System implementations
│       │   ├── __init__.py
│       │   ├── trino.py
│       │   ├── postgresql.py
│       │   └── minio.py
│       ├── data/                # Data management
│       │   ├── __init__.py
│       │   ├── generator.py
│       │   └── loader.py
│       ├── monitoring/          # Resource monitoring
│       │   ├── __init__.py
│       │   └── metrics.py
│       ├── analysis/            # Analysis and reporting
│       │   ├── __init__.py
│       │   ├── analyzer.py
│       │   └── reporter.py
│       └── utils/               # Utilities
│           ├── __init__.py
│           ├── config.py
│           ├── docker.py
│           └── logging.py
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   ├── fixtures/                # Test fixtures
│   └── conftest.py              # Pytest configuration
├── config/                      # Configuration files
├── apps/                        # Benchmark applications
├── datasets/                    # Generated datasets
├── results/                     # Benchmark results
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
├── setup.py                     # Package setup
└── README.md                    # Documentation
```

### Key Design Principles
1. **Separation of Concerns**: Each module has a single responsibility
2. **Dependency Injection**: Systems and experiments are configurable
3. **Error Handling**: Comprehensive error handling and logging
4. **Extensibility**: Easy to add new systems, benchmarks, and metrics
5. **Testability**: All components are unit-testable

### Key Abstractions (Following PEEL Patterns)

1. **System**: Represents a system component (Trino, MinIO, etc.)
2. **Experiment**: Individual benchmark experiment
3. **ExperimentSuite**: Collection of related experiments
4. **DataSet**: Data source for experiments
5. **Bundle**: Complete benchmark package

### File Structure Mapping

```
Current Project              → New TriBench Structure
├── docker-compose.yml      → tribench-framework/utils/docker/
├── scripts/                → tribench-framework/lib/tribench/
├── notebooks/              → tribench-framework/utils/notebooks/
├── data/                   → tribench-framework/datasets/
├── trino/conf/             → tribench-framework/config/
└── requirements.txt        → tribench-framework/requirements.txt
```

---

## Weekly Progress Tracking

Use this template for weekly updates:

```markdown
## Week X (Date Range)

### Completed
- [ ] Task 1
- [ ] Task 2

### In Progress
- [ ] Task 3

### Blocked/Issues
- Issue 1: Description
- Mitigation: Action taken

### Next Week
- [ ] Task 4
- [ ] Task 5

### Hours Spent
- Development: X hours
- Testing: Y hours
- Documentation: Z hours
- Research: W hours
```

---

## Resources and References

### Key Papers
1. PEEL Framework: [Original Paper](https://github.com/peelframework/peel)
2. TPC-H Benchmark: [TPC-H Specification](http://www.tpc.org/tpch/)
3. Apache Iceberg: [Iceberg Paper](https://iceberg.apache.org/)
4. Trino Architecture: [Trino Documentation](https://trino.io/docs/current/)

### Tools and Libraries
- **Trino**: https://trino.io/
- **Apache Iceberg**: https://iceberg.apache.org/
- **Click**: https://click.palletsprojects.com/
- **PyHOCON**: https://github.com/chimpler/pyhocon
- **Pytest**: https://pytest.org/

### Community Resources
- Trino Community Slack
- Iceberg Mailing Lists
- Stack Overflow tags: `trino`, `apache-iceberg`

---

---

## Appendix: Scope Decisions & Future Work

### Features Scoped Down (Realistic Dissertation Timeline)

**From Original "Out of Scope" List - Now Partially/Fully Included:**
1. **TPC-DS Benchmark**: ✅ NOW INCLUDED - Subset of 20-30 queries (vs full 99) with framework support documented
2. **Multi-Node Cluster**: ✅ NOW INCLUDED - 2-node deployment required (vs full 8-node scalability study)
3. **Kubernetes**: ⏭️ DEFERRED - Docker Compose + optional Docker Swarm sufficient
4. **Prometheus/Grafana**: ⏭️ DEFERRED - Basic metrics collection via docker stats + JMX, dashboards as Future Work

**Features Remaining as Future Work:**
5. **Machine Learning Analysis**: Statistical analysis only (regression models as Future Work)
6. **Concurrent Execution**: Sequential experiments only (parallel execution as Future Work)
7. **Cloud Deployment**: Local + School cluster only (AWS/Azure/GCP as Future Work)
8. **Full TPC-DS Coverage**: 20-30 queries implemented, remaining 70+ documented as Future Work
9. **Advanced Scalability**: 2-node demonstrated, 4-8 node scaling as Future Work
10. **Advanced Monitoring**: Real-time dashboards, alerting, distributed tracing as Future Work
11. **CI/CD Pipeline**: GitHub Actions for testing as Future Work
12. **Container Orchestration**: Kubernetes, Helm charts as Future Work

### Justification for Scope Decisions

**TPC-DS Subset (20-30 queries)**:
- Framework design matters more than exhaustive query coverage
- 20-30 queries sufficient to demonstrate workload diversity
- Remaining queries follow same patterns (framework extensibility proven)
- Time saved: ~3 weeks

**2-Node Cluster (vs 8-node)**:
- Demonstrates distributed execution capability
- Validates coordinator-worker architecture
- Shows scalability concept without diminishing returns of testing 4-8 nodes
- Time saved: ~4 weeks

**Basic Monitoring (vs Prometheus/Grafana)**:
- Docker stats + JMX metrics sufficient for performance comparison
- Manual result analysis acceptable for dissertation scope
- Real-time dashboards provide polish but not research value
- Time saved: ~2 weeks

**Total Time Saved**: ~9 weeks → brings project to **38-42 weeks** (feasible for extended dissertation timeline)

### Future Work Opportunities (Dissertation Chapter 7)

These features can be discussed as logical extensions in the "Future Work" section:

1. **Full TPC-DS Implementation**: Complete all 99 queries, query complexity categorization
2. **Large-Scale Scalability Study**: 4, 8, 16 worker configurations on production cluster
3. **Advanced Monitoring Infrastructure**: Prometheus, Grafana, distributed tracing, real-time alerting
4. **Cloud Provider Support**: AWS EMR/EKS, Azure AKS, GCP Dataproc deployment guides
5. **Machine Learning Integration**: Query performance prediction, resource estimation, anomaly detection
6. **Kubernetes Orchestration**: Helm charts, auto-scaling, production-grade deployment
7. **CI/CD Pipeline**: Automated testing, Docker image publishing, benchmark regression detection
8. **Additional Benchmarks**: SSB (Star Schema Benchmark), custom industry workloads
9. **Concurrent Execution**: Parallel experiment execution, workload simulation with timing
10. **Interactive UI**: Web-based configuration, execution, monitoring dashboard

---

This plan provides a **realistic and achievable** approach to building a comprehensive benchmarking framework that follows proven patterns from PEEL while being specifically tailored for Trino and data lakehouse workloads. The scoped implementation delivers on dissertation requirements while acknowledging practical constraints of timeline and resources.

