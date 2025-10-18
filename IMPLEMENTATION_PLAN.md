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
**"How do different table format features in Apache Iceberg impact analytical query performance in Trino, and what are the trade-offs between feature capabilities and query execution efficiency?"**

### Secondary Research Questions
1. **Scalability Analysis**: How does query performance scale across different data sizes (scale factors) in Trino on Iceberg tables?
2. **Format Comparison**: What are the performance differences between Trino's native connectors (memory, Hive) and Iceberg tables for TPC-H workloads?
3. **Optimization Strategies**: Which partitioning and optimization strategies provide the best performance for different query patterns?

### Expected Contributions
1. **Reproducible Benchmarking Framework**: A systematic tool for conducting reproducible Trino performance experiments
2. **Performance Characterization**: Empirical analysis of Iceberg features (time travel, schema evolution, partition pruning) and their performance implications
3. **Best Practices**: Recommendations for optimizing Trino + Iceberg configurations based on workload characteristics
4. **Open Source Tool**: Community-reusable framework for data lakehouse benchmarking

### Success Criteria
1. **Reproducibility**: Identical experiments produce consistent results (variance < 5%)
2. **Framework Reliability**: Successfully executes TPC-H queries with <1% failure rate
3. **Usability**: Complete setup time < 30 minutes on standard hardware
4. **Research Insights**: Generate actionable performance insights for Iceberg features
5. **Documentation**: Comprehensive user and developer documentation

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
- [ ] TPC-H data generation integration (SF1, SF10)
- [ ] Iceberg table format support:
  - [ ] Hive Metastore integration (Docker-based)
  - [ ] MinIO object storage setup
  - [ ] Iceberg catalog configuration
  - [ ] Table creation and data loading scripts
- [ ] Dataset validation and checksums
- [ ] Dataset metadata tracking

### 2.2 Benchmark Implementation (Focused Scope)
- [ ] TPC-H query suite (queries 1-10 initially, expand to 22 if time permits)
- [ ] Parameterized query execution:
  - [ ] Query templating with Jinja2
  - [ ] Parameter substitution
  - [ ] Multiple runs with warm-up
- [ ] Query result validation:
  - [ ] Row count verification
  - [ ] Result checksums (for deterministic queries)
  - [ ] Comparison with expected results
- [ ] Custom benchmark support (for research experiments)

### 2.3 Workload Definition
- [ ] Workload specification format (YAML)
- [ ] Query sequencing and timing
- [ ] Support for experiment suites
- [ ] Execution orchestration

**Deliverables**:
- TPC-H SF1 and SF10 datasets generated and loaded
- Iceberg tables created and validated
- 10+ TPC-H queries executable with validation
- Experiment suites working end-to-end

**Time Estimate**: 6 weeks (with 40% buffer = 8.4 weeks)

## Phase 3: Monitoring and Analysis (Weeks 17-22)

### 3.1 Resource Monitoring
- [ ] System resource monitoring (CPU, memory, I/O)
- [ ] Trino-specific metrics collection via JMX
- [ ] Query-level performance metrics
- [ ] Real-time monitoring during experiments
- [ ] Metrics storage in structured format (JSON/CSV)

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
- Resource monitoring working during experiments
- Results stored in PostgreSQL database
- Basic statistical analysis implemented
- HTML reports with visualizations

**Time Estimate**: 6 weeks (with 40% buffer = 8.4 weeks)

## Phase 4: Research Experiments & Validation (Weeks 23-28)

### 4.1 Research Experiment Design
**Choose ONE primary research direction:**

**Option A: Iceberg Features Analysis** (RECOMMENDED)
- [ ] Implement Iceberg catalog integration
- [ ] Time travel query experiments
- [ ] Schema evolution performance tests
- [ ] Partition pruning effectiveness
- [ ] Performance comparison: Memory connector vs. Iceberg

**Option B: Scalability Study**
- [ ] TPC-H SF1, SF10, SF100 comparison
- [ ] Scale-up analysis (data size impact)
- [ ] Speed-up analysis (if multi-node available)
- [ ] Cost-performance analysis
- [ ] Scalability visualizations

**Option C: Query Optimization Study**
- [ ] Different partition strategies
- [ ] Impact on query performance
- [ ] Filter pushdown effectiveness
- [ ] Join optimization strategies
- [ ] Best practices recommendations

### 4.2 Experimental Validation
- [ ] Reproducibility testing (multiple runs)
- [ ] Variance analysis (< 5% target)
- [ ] Result validation against expected outcomes
- [ ] Statistical significance testing
- [ ] Anomaly detection and handling

### 4.3 Documentation and Examples
- [ ] Comprehensive user documentation
- [ ] Developer guides and API documentation
- [ ] Example benchmark bundles
- [ ] Tutorial: Creating custom experiments
- [ ] Troubleshooting guide

**Deliverables**:
- Complete research experiments executed
- Results analyzed and validated
- Insights and recommendations documented
- Framework fully documented

**Time Estimate**: 6 weeks (with 40% buffer = 8.4 weeks)

## Phase 5: OPTIONAL Advanced Features (Future Work)

**⚠️ NOTE**: These features are OUT OF SCOPE for initial dissertation but can be mentioned as "Future Work"

### 5.1 Experiment Orchestration (Optional)
- [ ] Experiment dependencies
- [ ] Automated experiment sequences
- [ ] Failure recovery and retry logic
- [ ] Parallel experiment execution

### 5.2 Distributed Execution (Optional - Complex!)
- [ ] Multi-node Trino cluster support
- [ ] Remote experiment execution
- [ ] Cluster resource management
- [ ] Load balancing strategies

### 5.3 Advanced Analytics (Optional)
- [ ] Performance regression testing
- [ ] A/B testing framework
- [ ] Statistical significance testing
- [ ] Machine learning-based analysis

### 5.4 Cloud Integration (Optional)
- [ ] Cloud deployment support (AWS, Azure, GCP)
- [ ] Container orchestration (Kubernetes)
- [ ] CI/CD pipeline integration
- [ ] Automated scaling

**Note**: Pick MAX ONE item from Phase 5 if time permits after Phase 4 completion.

## Phase 6: Dissertation Writing & Final Polish (Weeks 23-26, Concurrent)

### 6.1 Documentation Completion
- [ ] Comprehensive user documentation
- [ ] API reference documentation
- [ ] Architecture documentation
- [ ] Deployment guides
- [ ] Example benchmark bundles

### 6.2 Dissertation Writing
- [ ] Literature review refinement
- [ ] Methodology chapter (framework design)
- [ ] Implementation chapter
- [ ] Evaluation and results chapter
- [ ] Conclusions and future work

### 6.3 Final Polish
- [ ] Code refactoring and cleanup
- [ ] Performance optimization
- [ ] Bug fixes and edge cases
- [ ] Final benchmark runs for dissertation
- [ ] Prepare demo/presentation materials

**Deliverables**:
- Complete dissertation draft
- Fully documented framework
- Reproducible benchmark results
- Demo materials

**Time Estimate**: 4 weeks dedicated + concurrent work throughout phases

---

## Timeline Summary with Realistic Estimates

| Phase | Original | With Buffer | Weeks | Milestone |
|-------|----------|-------------|-------|-----------|
| **Phase 0** | 2 weeks | 3 weeks | 1-3 | Foundation & Testing Setup |
| **Phase 1** | 8 weeks | 11 weeks | 4-14 | Minimal Viable Framework |
| **Phase 2** | 6 weeks | 8 weeks | 15-22 | Core Benchmarking |
| **Phase 3** | 6 weeks | 8 weeks | 23-30 | Monitoring & Analysis |
| **Phase 4** | 6 weeks | 8 weeks | 31-38 | Research Experiments |
| **Phase 5** | - | OPTIONAL | - | Future Work Only |
| **Phase 6** | 4 weeks | Concurrent | 23-42 | Writing & Polish |

**Total Estimated Time**: 38-42 weeks (realistic) vs. 26 weeks (original)

**Recommendation**: Focus on Phases 0-4 for core dissertation. Phase 5 as "Future Work" chapter.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Timeline overrun | **HIGH** | **HIGH** | Reduce scope, focus on MVP, strict phase gates |
| Technical complexity (Trino/Iceberg) | **MEDIUM** | **HIGH** | Start simple (Docker only), use stable versions |
| Scope creep | **HIGH** | **HIGH** | Defer Phase 5, focus on research questions |
| Research contribution unclear | **LOW** | **CRITICAL** | Research questions defined, regular advisor meetings |
| Trino integration issues | **MEDIUM** | **MEDIUM** | Use stable Trino 434, extensive testing |
| Data generation bottleneck | **LOW** | **MEDIUM** | Pre-generate datasets, cache in repo |
| Testing insufficient | **MEDIUM** | **HIGH** | Test-driven development, continuous testing |

---

## Implementation Details

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

## Success Metrics

### Technical Metrics
- **Code Coverage**: >80% test coverage
- **Build Success Rate**: 100% of commits pass CI
- **Documentation Coverage**: All public APIs documented
- **Performance**: Framework overhead <5% of query time

### Research Metrics
- **Reproducibility**: Variance <5% across identical runs
- **Experiment Success Rate**: >99% of queries execute successfully
- **Insights Generated**: ≥3 actionable performance insights
- **Dataset Coverage**: TPC-H SF1, SF10 fully loaded

### Dissertation Metrics
- **Word Count**: 10,000-15,000 words
- **Figures/Tables**: 20+ visualizations
- **References**: 30+ academic sources
- **Code Quality**: Clean, documented, tested

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

## Appendix: Removed Features (Future Work)

The following features were removed from the core plan to reduce scope:

1. **TPC-DS Benchmark**: Focus on TPC-H only (99 queries vs. 22)
2. **Multi-Node Cluster**: Single-node Docker deployment only
3. **Kubernetes**: Docker Compose sufficient for dissertation
4. **Prometheus/Grafana**: Basic metrics collection only
5. **Machine Learning Analysis**: Statistical analysis only
6. **Concurrent Execution**: Sequential experiments only
7. **Cloud Deployment**: Local deployment only
8. **All 22 TPC-H Queries**: Start with 10, expand if time permits

These features can be mentioned in the "Future Work" section of your dissertation.

This plan provides a structured approach to building a comprehensive benchmarking framework that follows proven patterns from PEEL while being specifically tailored for Trino and data lakehouse workloads.
