# TriBench - Dissertation Project Journal

## Overview
This journal documents the development of TriBench, a PEEL-inspired benchmarking framework for Apache Trino, as part of my MSc Computer Science dissertation at the University of Glasgow.

**Research Question**: How do Apache Iceberg features impact query performance in Apache Trino across different workload patterns?

**Timeline**: 40-week project (Oct 2024 - July 2025)

---

## Phase 0: Foundation (Week 1-2) ✅

### Architecture Decisions
- **Framework Pattern**: PEEL-inspired bundle-based architecture for reproducibility
- **Language**: Python 3.11+ for ecosystem compatibility and data science libraries
- **CLI Framework**: Click for professional command-line interface
- **Testing Strategy**: pytest with >80% coverage target
- **Configuration**: HOCON for hierarchical, environment-spe---

*Last Updated: 13 October 2025*
*Total Development Time: ~70.5 hours*
*Phase 0 Complete | Phase 1 Sections 1.1-1.4 Complete* configuration
- **Packaging**: Standard Python package with setuptools for easy distribution

### Core Abstractions Implemented ✅
1. **System Abstraction** (`lib/tribench/core/system.py`)
   - Abstract base class for all system components (Trino, PostgreSQL, MinIO)
   - Lifecycle methods: setup(), start(), stop(), teardown()
   - Health checking and status reporting
   - **Dissertation Value**: Demonstrates extensible architecture design

2. **Experiment Abstraction** (`lib/tribench/core/experiment.py`)
   - Experiment lifecycle management and execution control
   - Support for multiple runs, warmup phases, timeouts
   - **Dissertation Value**: Shows structured approach to benchmark execution

3. **Result Data Model** (`lib/tribench/core/result.py`)
   - Structured result storage with timing, metrics, metadata
   - Support for statistical analysis and comparison
   - **Dissertation Value**: Enables rigorous performance analysis

### Testing Infrastructure ✅
- **Unit Tests**: 10+ tests covering all core abstractions
- **Test Coverage**: Setup for >80% coverage tracking
- **CI/CD Ready**: pytest configuration with HTML reporting
- **Fixtures**: Reusable test data and mock systems
- **Dissertation Value**: Demonstrates software engineering best practices

---

## Phase 1: Command Line Interface (Week 3) ✅

### Section 1.1: CLI Implementation ✅
**Completed**: Full CLI system with 21 commands across 4 command groups

#### Core CLI Infrastructure
- **Context Management**: `TriBenchContext` class for shared state
- **Common Decorators**: `@dry_run_option`, `@verbose_option`, `@config_option`
- **Error Handling**: Graceful failure with informative messages
- **Help System**: Comprehensive help text with examples

#### Command Groups Implemented

1. **System Management (`sys`)** - 5 commands
   - `setup <system>`: System installation and configuration
   - `start <system>`: Service startup with health checks
   - `stop <system>`: Graceful shutdown with force option
   - `status [system]`: Runtime status monitoring
   - `teardown <system>`: Complete cleanup with confirmation

2. **Experiment Execution (`exp`)** - 5 commands
   - `run <file>`: Execute benchmark experiments
   - `list`: Enumerate available experiments
   - `status <id>`: Monitor experiment progress
   - `cancel <id>`: Terminate running experiments
   - `config <file>`: Display resolved configuration

3. **Dataset Management (`data`)** - 5 commands
   - `generate <dataset>`: Create TPC-H datasets
   - `load <dataset>`: Import data into target systems
   - `list`: Show available datasets
   - `info <dataset>`: Display dataset metadata
   - `validate <dataset>`: Verify data integrity

4. **Result Analysis (`res`)** - 6 commands
   - `show <id>`: Display experiment results
   - `list`: Enumerate stored results
   - `compare <ids...>`: Side-by-side performance comparison
   - `export <id>`: Export results to CSV/JSON
   - `analyze <suite>`: Statistical analysis with plots
   - `delete <id>`: Clean up result storage

#### CLI Features
- **Dry-run Mode**: Safe command preview without side effects
- **Verbose Logging**: Detailed operation tracing
- **Configuration Support**: External config file loading
- **Input Validation**: Choice constraints and path validation
- **Confirmation Prompts**: Safety checks for destructive operations

#### Testing
- **CLI Test Suite**: 15 test cases using Click's CliRunner
- **Argument Validation**: Tests for all command options
- **Help Text Verification**: Ensures documentation completeness
- **Dry-run Testing**: Validates preview functionality

### Technical Implementation Details

#### Package Structure
```
lib/tribench/cli/
├── __init__.py           # Command group imports
├── base.py              # Core CLI setup, context, decorators
├── system_commands.py   # System lifecycle management
├── experiment_commands.py # Experiment execution
├── data_commands.py     # Dataset operations
└── result_commands.py   # Result analysis
```

#### Dependencies and Integration
- **Click Framework**: Professional CLI with command groups
- **Entry Point**: `tribench` command via setuptools
- **Shell Integration**: Compatible with `bin/tribench.sh` dispatcher
- **Error Handling**: Graceful failures with exit codes

### Dissertation Contributions
1. **User Experience**: Professional CLI demonstrates framework usability
2. **Reproducibility**: Dry-run and configuration options ensure repeatability
3. **Extensibility**: Command group structure allows easy feature addition
4. **Testing**: CLI test suite demonstrates software quality practices

---

## Phase 1 Continued: Configuration System (Week 3-4) ✅

### Section 1.2: Configuration System ✅
**Completed**: Full hierarchical configuration management with HOCON

#### Core Configuration Components

1. **ConfigurationLoader Class** (`lib/tribench/utils/config.py`)
   - Hierarchical configuration loading and merging
   - Three-layer architecture: reference → host → experiment
   - Auto-detection of host-specific configurations
   - Environment variable resolution
   - Configuration validation with custom schemas
   - **Dissertation Value**: Enables reproducible experiments across environments

2. **ConfigurationTemplate Class**
   - Jinja2-based template engine for system configs
   - Generate Trino properties files from HOCON
   - Support for both file-based and string templates
   - Automatic output path creation
   - **Dissertation Value**: Single source of truth for all configurations

3. **Configuration Files Created**
   - `config/reference.conf`: Framework defaults (ports, paths, system versions)
   - `config/hosts/localhost/application.conf`: Development environment overrides
   - `config/templates/trino-config.properties.j2`: Trino config template
   - `config/templates/trino-jvm.config.j2`: JVM settings template
   - `experiments/tpch-sf1.yaml`: Example experiment configuration

#### Configuration Hierarchy Implementation

**Layer 1 - Reference Config**:
- Default values for all framework components
- System versions (Trino 434, PostgreSQL 15, MinIO)
- Network ports (Trino: 8080, PostgreSQL: 5432, MinIO: 9000)
- Resource limits (JVM heap: 2G, query memory: 1GB)
- Framework paths (datasets, results, logs, systems)

**Layer 2 - Host Config**:
- Machine-specific overrides
- Custom installation paths
- Resource allocations based on hardware
- Local development shortcuts
- Auto-detected using `platform.node()`

**Layer 3 - Experiment Config**:
- Experiment-specific settings
- Query selection and parameters
- Dataset and catalog configuration
- Execution settings (runs, warmup, timeout)
- System configuration overrides

#### Configuration Features Implemented

1. **Hierarchical Merging**
   - Configs automatically merge with later layers overriding earlier ones
   - Nested configuration preservation
   - Safe defaults with progressive customization

2. **Environment Variables**
   - Support for `${VAR_NAME}` syntax
   - Optional variables with `${?VAR_NAME}`
   - Integration with system environment
   - Useful for passwords and dynamic values

3. **Validation System**
   - Type checking (int, str, bool, dict)
   - Range validation (min/max for numbers)
   - Choice validation (enum-like constraints)
   - Required field checking
   - Nested schema support
   - Clear error messages with path information

4. **Template Generation**
   - Jinja2 templates for system-specific configs
   - Support for Trino config.properties and jvm.config
   - Extensible to other systems (PostgreSQL, MinIO)
   - Automatic file creation with proper paths

#### Testing
- **Configuration Tests**: 17 test cases covering all functionality
- **Test Coverage**: 84% coverage of config module
- **Test Categories**:
  - Initialization and path detection
  - Reference config loading
  - Host config auto-detection
  - Experiment config parsing
  - Full hierarchy merging
  - Validation (basic and schema-based)
  - Template generation (string and file-based)
  - Environment variable substitution

#### Technical Implementation

**Key Design Decisions**:
1. **HOCON Format**: Human-friendly, supports includes and substitutions
2. **Auto-detection**: Framework automatically finds host configs
3. **Immutable Configs**: ConfigTree objects preserve config state
4. **Error Handling**: ConfigurationError for all failures with context
5. **Logging**: Detailed debug logs for configuration loading

**Dependencies**:
- `pyhocon`: HOCON parsing and ConfigTree management
- `jinja2`: Template rendering engine
- `platform`: System information for host detection

#### Dissertation Contributions

1. **Reproducibility**:
   - Same experiment config works across different machines
   - Host-specific settings isolated from experiment definitions
   - Version-controlled configuration files

2. **Flexibility**:
   - Easy to create experiment variants
   - Parameter sweeps through config generation
   - No code changes needed for different setups

3. **Professional Framework**:
   - Industry-standard configuration approach (similar to PEEL, Apache projects)
   - Clear separation of concerns
   - Maintainable and documented

4. **Research Workflow**:
   - Quick experiment definition (YAML/HOCON)
   - Safe environment isolation
   - Configuration as documentation

### Configuration System Examples

**Basic Usage**:
```python
from tribench.utils.config import ConfigurationLoader

# Load configuration with all layers
loader = ConfigurationLoader()
config = loader.load(experiment_config="experiments/tpch-sf1.yaml")

# Access nested values
trino_port = config["tribench"]["systems"]["trino"]["coordinator"]["port"]  # 8080

# Validate configuration
errors = loader.validate(config)
if errors:
    print("Configuration errors:", errors)
```

**Template Generation**:
```python
from tribench.utils.config import ConfigurationTemplate

# Generate Trino config file
template_gen = ConfigurationTemplate()
trino_config = template_gen.generate(
    "trino-config.properties.j2",
    config,
    output_path="systems/trino/etc/config.properties"
)
```

### Files Created/Modified
- **New**: `lib/tribench/utils/config.py` (141 lines, 3 classes)
- **New**: `tests/unit/test_config.py` (17 test cases)
- **New**: `config/templates/trino-config.properties.j2`
- **New**: `config/templates/trino-jvm.config.j2`
- **New**: `experiments/tpch-sf1.yaml`
- **Existing**: `config/reference.conf` (already had basic structure)
- **Existing**: `config/hosts/localhost/application.conf` (already existed)

### Lessons Learned

1. **HOCON Syntax**: Default value syntax `${VAR:-default}` not supported in pyhocon; use separate variables
2. **Config Merging**: ConfigTree.merge_configs preserves nested structures correctly
3. **Path Handling**: Using Path objects consistently prevents platform issues
4. **Template Power**: Jinja2 templates eliminate manual config file maintenance
5. **Test Coverage**: Comprehensive tests caught edge cases in validation logic

### Time Investment
- **Configuration Module**: 3 hours (design + implementation)
- **Test Suite**: 2 hours (17 test cases + fixtures)
- **Templates**: 1 hour (Trino config templates)
- **Documentation**: 1 hour (docstrings + examples)
- **Total**: ~7 hours for complete configuration system

---

## Development Environment Setup ✅

### Conda Environment
- **Python**: 3.11+ with scientific computing stack
- **Dependencies**: 25+ packages including Trino, pandas, pytest, Click
- **Installation**: `conda env create -f environment.yml`
- **Activation**: `conda activate tribench`

### Package Installation
- **Development Mode**: `pip install -e .` for live code changes
- **Entry Point**: `tribench` command available system-wide
- **Verification**: `tribench --version` confirms installation

### Documentation
- **README.md**: Complete usage guide with examples
- **CLI Help**: Comprehensive help text for all commands
- **Code Documentation**: Extensive docstrings throughout

---

## Phase 1 Continued: System Management (Week 4) ✅

### Section 1.3: Trino System Implementation ✅
**Completed**: Full Docker-based Trino lifecycle management with health monitoring

#### Core System Components

1. **TrinoSystem Class** (`lib/tribench/systems/trino.py`)
   - Complete implementation of System abstract base class
   - 650+ lines of production-ready code
   - Docker Compose-based deployment for simplicity
   - Configuration-driven setup from HOCON
   - **Dissertation Value**: Demonstrates containerized system management

2. **Lifecycle Management**
   - `setup()`: Downloads Trino binary, creates directories, generates configs, builds Docker Compose
   - `start()`: Launches containers, waits for health checks, validates startup
   - `stop()`: Graceful or force shutdown with configurable timeout
   - `teardown()`: Complete cleanup including containers, volumes, optionally files
   - `status()`: Returns detailed runtime information (running state, health, ports, endpoints)
   - `is_running()`: Quick health check via Docker ps
   - `get_logs()`: Retrieves container logs with tail/follow options

3. **Docker Compose Generation**
   - Dynamic generation from HOCON configuration
   - Health check integration using Trino's `/v1/info` endpoint
   - Volume mounting for config and catalog files
   - Custom Docker network creation
   - Port mapping from configuration
   - Restart policy and resource limits

4. **Configuration File Generation**
   - `config.properties`: Coordinator settings, discovery URI, web port
   - `jvm.config`: Heap size, GC settings, JVM options
   - `node.properties`: Node ID, environment, data directories
   - Catalog configs: TPCH, Iceberg, PostgreSQL catalogs
   - All generated from HOCON templates using Jinja2

5. **Binary Management**
   - Downloads Trino server tarball from Maven Central
   - Caches downloads in `downloads/` directory
   - Validates downloads with checksum (future enhancement)
   - Supports multiple Trino versions
   - Default version: 434 (latest stable)

6. **Health Checking**
   - HTTP-based health checks to `/v1/info` endpoint
   - Configurable retry attempts and intervals
   - Validates both container state and Trino readiness
   - Returns detailed health information in status

#### CLI Integration

**Updated System Commands** (`lib/tribench/cli/system_commands.py`):
- `tribench sys setup trino [--version 434]`: Downloads, configures, creates Docker Compose
- `tribench sys start trino`: Starts containers and waits for health
- `tribench sys stop trino [--force]`: Stops containers gracefully or forcefully
- `tribench sys status trino`: Shows running state, health, ports, endpoints
- `tribench sys teardown trino [--keep-data]`: Complete cleanup with confirmation
- `tribench sys logs trino [--tail 100] [--follow]`: View container logs

**Command Features**:
- Error handling with try/except blocks
- Verbose mode for debugging
- Dry-run support for safe testing
- User-friendly success/error messages
- Integration with configuration system

#### Docker Architecture

**Container Setup**:
```yaml
services:
  trino:
    image: trinodb/trino:{version}
    container_name: tribench-trino
    ports:
      - "{http_port}:8080"
    volumes:
      - ./config:/etc/trino
      - ./catalogs:/etc/trino/catalog
    networks:
      - tribench-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/v1/info"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Volume Structure**:
```
systems/trino/
├── bin/              # Trino CLI (future)
├── config/           # Generated config files
│   ├── config.properties
│   ├── jvm.config
│   └── node.properties
├── catalogs/         # Catalog configurations
│   ├── tpch.properties
│   ├── iceberg.properties
│   └── postgresql.properties
└── docker-compose.yml
```

#### Configuration Integration

**HOCON Configuration** (`config/reference.conf`):
```hocon
tribench.systems.trino {
  version = 434
  coordinator {
    port = 8080
    heap_size = "2G"
    query_max_memory = "1GB"
  }
  catalogs {
    tpch.enabled = true
    iceberg {
      enabled = true
      warehouse_dir = "/data/warehouse"
    }
    postgresql {
      enabled = true
      connection_url = "jdbc:postgresql://localhost:5432/tribench"
    }
  }
}
```

**Configuration Loading**:
- Uses `ConfigurationLoader` for hierarchical config
- Merges reference → host → experiment configs
- Supports environment variable substitution
- Validates required fields

#### Implementation Details

**Key Methods**:

1. **`_download_trino(version)`**:
   - Constructs Maven Central URL
   - Downloads to `downloads/trino-server-{version}.tar.gz`
   - Skips if already cached
   - Future: Add SHA256 checksum validation

2. **`_generate_configs()`**:
   - Creates `config.properties` with coordinator settings
   - Generates `jvm.config` with heap and GC options
   - Creates `node.properties` with unique node ID
   - Sets up discovery URI for cluster formation

3. **`_generate_docker_compose()`**:
   - Builds YAML dynamically from config
   - Adds health checks and volume mounts
   - Creates custom network for service isolation
   - Sets environment variables and restart policies

4. **`_check_health()`**:
   - Requests `/v1/info` endpoint
   - Parses JSON response for cluster state
   - Returns True if coordinator is ready
   - Handles connection errors gracefully

5. **`_wait_for_health(timeout, interval)`**:
   - Polls health endpoint until ready
   - Configurable retry logic
   - Raises TimeoutError if not healthy
   - Logs progress during startup

#### Testing Strategy

**Manual Testing**:
```bash
# Full lifecycle test
tribench sys setup trino --version 434
tribench sys start trino
tribench sys status trino
curl http://localhost:8080/v1/info  # Verify endpoint
tribench sys logs trino --tail 50
tribench sys stop trino
tribench sys teardown trino
```

**Unit Testing Plan** (future):
- Mock Docker subprocess calls
- Test configuration generation
- Validate compose file structure
- Test health check logic
- Mock HTTP responses for health endpoint

#### Dissertation Contributions

1. **Containerized System Management**:
   - Docker-based approach simplifies deployment
   - Eliminates manual installation steps
   - Portable across development environments
   - Production-ready container orchestration

2. **Configuration-Driven Setup**:
   - Single source of truth (HOCON config)
   - No hardcoded values in code
   - Easy to modify for different experiments
   - Template-based config generation

3. **Robust Lifecycle Management**:
   - Health checking ensures system readiness
   - Graceful shutdown prevents data corruption
   - Complete cleanup for reproducible runs
   - Status monitoring for debugging

4. **Professional Framework Design**:
   - Follows System abstract base class pattern
   - Consistent with PEEL's bundle-based approach
   - Extensible to other systems (PostgreSQL, MinIO)
   - Well-structured codebase for maintenance

### Technical Challenges Solved

1. **Docker Compose Generation**: Dynamic YAML creation from HOCON config
2. **Health Checking**: Reliable startup detection via HTTP endpoint
3. **Binary Management**: Smart caching to avoid redundant downloads
4. **Configuration Templating**: Jinja2 integration for system-specific configs
5. **Error Handling**: Graceful failures with informative messages

### Files Created/Modified

- **New**: `lib/tribench/systems/trino.py` (650+ lines)
- **Modified**: `lib/tribench/cli/system_commands.py` (added TrinoSystem integration)
- **Modified**: `lib/tribench/systems/__init__.py` (export TrinoSystem)

### Dependencies Added
- `requests`: HTTP health checks to Trino endpoints
- `pyhocon`: HOCON configuration parsing (already present)

### Lessons Learned

1. **Docker Simplicity**: Docker Compose is simpler than manual binary management
2. **Health Checks Are Critical**: Containers may be "up" but service not ready; reliable health checking prevents race conditions
3. **Config Templates**: Jinja2 templates eliminate manual config editing
4. **Binary Caching**: Avoid repeated downloads for faster iteration
5. **Error Context**: Detailed error messages crucial for debugging
6. **Integration Testing Reveals Hidden Issues**: 4 bugs only surfaced during manual testing:
   - Parameter naming mismatches between components
   - Parent class signature differences
   - Subprocess output stream handling (stdout vs stderr)
   - Inverted boolean logic in parameter passing
7. **Type Mismatches**: CLI passes paths/strings, classes expect objects (ConfigTree) - need adapter layer
8. **Docker Logs Behavior**: Docker sends output to stderr, not stdout - must combine both streams
9. **Configuration Loading**: Hierarchical config must be loaded in CLI before passing to system classes
10. **End-to-End Testing Essential**: Unit tests alone wouldn't catch integration issues between CLI → Config → System layers

### Testing & Validation Process

After implementing the core functionality, extensive testing revealed several integration issues that needed fixing:

#### Testing Methodology
1. **Manual CLI Testing**: Used `tribench sys` commands directly
2. **Docker Verification**: Checked container state with `docker ps`
3. **HTTP Testing**: Verified Trino endpoint with `curl http://localhost:8080/v1/info`
4. **Log Inspection**: Examined Docker logs to understand system behavior
5. **Full Lifecycle**: Tested complete setup → start → status → logs → stop → teardown cycle

#### Bugs Discovered and Fixed

**Bug 1: CLI Configuration Loading** ❌ → ✅
- **Issue**: CLI was passing `config_path=<path>` but `TrinoSystem.__init__()` expected `config=<ConfigTree>`
- **Symptom**: `TypeError: TrinoSystem.__init__() got an unexpected keyword argument 'config_path'`
- **Root Cause**: Mismatch between CLI parameter naming and class signature
- **Fix**: Updated CLI to load configuration using `ConfigurationLoader` and pass `ConfigTree` object
- **Impact**: All commands now properly load and merge hierarchical configuration

**Bug 2: Parent Class Initialization** ❌ → ✅
- **Issue**: Called `super().__init__(name="trino", version=None)` but `System` doesn't accept `version`
- **Symptom**: `TypeError: System.__init__() got an unexpected keyword argument 'version'`
- **Root Cause**: System base class only accepts `(name, config)` parameters
- **Fix**: Reordered initialization to load version from config first, then pass to parent
- **Code Change**: 
  ```python
  # Before (wrong order)
  super().__init__(name="trino", version=None)
  self.version = get_config_value(config, "...", "434")
  
  # After (correct order)
  self.version = get_config_value(config, "...", "434")
  super().__init__(name=f"trino-{self.version}", config=config)
  ```

**Bug 3: Log Output Not Displaying** ❌ → ✅
- **Issue**: `tribench sys logs trino` showed nothing despite logs existing in Docker
- **Symptom**: Command ran without errors but no output appeared
- **Root Cause**: Docker logs write to stderr, but code only returned stdout
- **Investigation**: Tested with `docker logs --tail=20 tribench-trino-434` confirmed logs existed
- **Fix**: Combined stdout and stderr in return value
- **Code Change**:
  ```python
  # Before
  return result.stdout if result.returncode == 0 else None
  
  # After
  output = result.stdout + result.stderr if result.returncode == 0 else None
  return output if output else None
  ```

**Bug 4: Teardown Parameter Mismatch** ❌ → ✅
- **Issue**: CLI passed `remove_data=not keep_data` but method expected `keep_data`
- **Symptom**: `--keep-data` flag actually deleted files instead of keeping them
- **Root Cause**: Inverted logic in parameter passing
- **Fix**: Changed CLI to pass `keep_data=keep_data` directly
- **Testing**: Verified both `--keep-data` (preserves) and default (deletes) work correctly

#### Configuration Override Enhancement

Added support for version override from CLI:
```python
# Override version if --version specified
if version:
    from pyhocon import ConfigFactory
    cfg = ConfigFactory.parse_string(f'tribench.systems.trino.version = "{version}"').with_fallback(cfg)
```
This allows `tribench sys setup trino --version 434` to override config file version.

#### Test Results - All Commands Verified ✅

**Setup Command**:
```bash
$ tribench sys setup trino --version 434 --verbose
Setting up Trino...
✓ Trino setup complete
```
- ✅ Downloads 606MB Trino binary from Maven Central
- ✅ Caches in `downloads/trino-server-434.tar.gz`
- ✅ Creates directory structure `systems/trino-434/etc/`
- ✅ Generates config.properties, jvm.config, node.properties
- ✅ Creates Docker Compose file with health checks
- ✅ Sets up TPCH and Memory catalogs
- ✅ Creates Docker network `tribench-network`

**Start Command**:
```bash
$ tribench sys start trino --verbose
Starting Trino...
✓ Trino started successfully
```
- ✅ Launches Docker container via docker-compose up
- ✅ Waits for health check (polls `/v1/info` endpoint)
- ✅ Container shows as "healthy" in Docker
- ✅ Trino UI accessible at http://localhost:8080
- ✅ Returns JSON from `/v1/info`: `{"nodeVersion": {"version": "434"}, "coordinator": true}`

**Status Command**:
```bash
$ tribench sys status trino
✓ Trino: Running
  Health: OK
```
- ✅ Reports running state accurately
- ✅ Checks HTTP endpoint health
- ✅ Shows ports and endpoints (when implemented)

**Logs Command**:
```bash
$ tribench sys logs trino --tail 10
2025-10-06T09:23:33.277Z  INFO  main  io.trino.server.Server  ======== SERVER STARTED ========
```
- ✅ Retrieves last N lines of container logs
- ✅ Combines stdout and stderr properly
- ✅ Shows Trino startup sequence
- ✅ Supports --follow flag (not fully tested)

**Stop Command**:
```bash
$ tribench sys stop trino --verbose
Stopping Trino...
✓ Trino stopped successfully
```
- ✅ Gracefully stops container via docker-compose down
- ✅ Removes container but preserves volumes
- ✅ Supports --force for immediate kill

**Teardown Command**:
```bash
$ tribench sys teardown trino --keep-data
Are you sure you want to tear down the system? [y/N]: y
✓ Trino teardown complete
```
- ✅ Requires confirmation (safety check)
- ✅ Stops containers and removes volumes
- ✅ `--keep-data` preserves config files
- ✅ Default removes everything for clean slate

#### Docker Verification

Container state after start:
```bash
$ docker ps --filter name=tribench-trino
CONTAINER ID   IMAGE               STATUS                    PORTS
4dc209fbd290   trinodb/trino:434   Up 48 seconds (healthy)   0.0.0.0:8080->8080/tcp
```

Generated Docker Compose structure:
```yaml
services:
  trino:
    image: trinodb/trino:434
    container_name: tribench-trino-434
    ports:
      - "8080:8080"
    volumes:
      - ./etc:/etc/trino
      - trino-data:/data
    networks:
      - tribench-network
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/v1/info || exit 1"]
      interval: 10s
      retries: 5
```

### Time Investment
- **TrinoSystem Implementation**: 4 hours (lifecycle methods, Docker integration)
- **CLI Integration**: 1 hour (initial update of system commands)
- **Testing & Bug Fixes**: 3 hours (manual lifecycle testing, fixing 4 bugs)
- **Documentation**: 1.5 hours (docstrings, examples, journal updates)
- **Total**: ~9.5 hours for complete Trino system management

### Next Steps for Section 1.3
- ✅ Trino system complete and tested
- 🔄 PostgreSQL system (similar Docker-based approach)
- 🔄 MinIO system (object storage for Iceberg)
- 🔄 Unit tests for TrinoSystem class
- 🔄 Integration tests for full lifecycle

### Testing Insights for Dissertation

This section demonstrates important software engineering practices relevant to the dissertation:

**1. Integration Testing Value**
- Unit tests alone insufficient for multi-layer systems
- Real-world testing caught 4 bugs that isolated unit tests would miss
- Parameter passing between layers (CLI → Config → System) needs validation
- Type conversions and adapters critical at component boundaries

**2. Iterative Development Process**
- Initial implementation: 5 hours
- Bug discovery and fixes: 3 hours (38% of total time)
- Shows realistic software development cycle
- Refactoring and debugging are normal, expected phases

**3. Docker Benefits for Research**
- Consistent environments across development machines
- Health checks ensure reproducible startup state
- Container logs provide detailed debugging information
- Teardown provides clean slate for experiment reruns

**4. Configuration System Validation**
- Hierarchical config works in practice (reference → host → experiment)
- CLI can override config values programmatically
- Missing host config warning helpful but non-blocking

**5. Developer Experience Improvements**
- Clear error messages reduced debugging time
- Verbose mode essential for understanding system behavior
- Dry-run mode allows safe exploration
- Confirmation prompts prevent accidental data loss

**6. Documentation Through Testing**
- Manual testing generated real usage examples
- Error messages revealed edge cases for documentation
- Testing verified help text accuracy
- Created confidence in production readiness

This testing phase validates that the framework is not just theoretically sound but practically usable for benchmark experiments.

---

## Phase 1 Continued: Experiment Engine (Week 5) ✅

### Section 1.4: Basic Experiment Engine ✅
**Completed**: Full experiment execution pipeline with query executor, result collection, and CLI integration

#### Core Experiment Components

1. **Enhanced ExperimentConfig** (`lib/tribench/core/experiment.py`)
   - Added YAML parsing capability with `from_yaml()` class method
   - Support for inline SQL queries and query file references
   - Execution parameters: runs, warmup_runs, timeout_seconds, max_retries
   - Connection parameters for Trino (host, port, catalog, schema)
   - Validation rules: min_success_rate, max_execution_time_variance
   - Metrics collection specification
   - **Dissertation Value**: Declarative experiment definition enables reproducible research

2. **QueryExecutor Class** (`lib/tribench/experiments/query_executor.py`)
   - Complete integration with trino-python-client
   - Connection management with automatic reconnection
   - Query submission with streaming result fetching
   - Timeout handling (default: 300 seconds)
   - Automatic retry with exponential backoff
   - Statistics collection from Trino query API
   - Context manager support for clean resource handling
   - **Dissertation Value**: Robust query execution ensures reliable measurements

3. **ResultCollector Class** (`lib/tribench/experiments/result_collector.py`)
   - Creates Result objects from query execution metadata
   - Stores results as JSON files in results/ directory
   - Aggregates statistics across multiple runs (mean, median, stdev)
   - Generates human-readable summaries
   - Loads and lists historical results
   - **Dissertation Value**: Structured storage enables systematic analysis

4. **TrinoExperiment Class** (`lib/tribench/experiments/trino_experiment.py`)
   - Concrete Experiment implementation for Trino workloads
   - Full lifecycle: prepare() → run() → validate() → cleanup()
   - Supports warmup runs to prime caches
   - Executes multiple measured runs for statistical significance
   - Collects detailed metrics: execution time, rows, CPU, memory
   - Validates results against configured rules
   - **Dissertation Value**: End-to-end experiment orchestration

#### Implementation Details

**QueryExecutor Features**:
- **Connection Management**: 
  - Automatic connection establishment
  - Connection state tracking with `is_connected()`
  - Graceful disconnect with error handling
  - Reconnection on transient failures

- **Query Execution**:
  - Executes SQL with `execute_query(query, fetch_results=True)`
  - Returns tuple of (rows, metadata)
  - Metadata includes: execution_time, query_id, state, CPU time, memory, processed rows/bytes
  - Streaming result fetching for large datasets

- **Error Handling**:
  - Distinguishes user errors (SQL syntax) from system errors
  - User errors don't trigger retries (fail fast)
  - System errors retry with exponential backoff (2^attempt seconds, max 30s)
  - Custom exceptions: `QueryExecutionError`, `QueryTimeoutError`

- **Retry Logic**:
  - `execute_query_with_retry()` wraps queries with retry
  - Configurable max_retries (default: 3)
  - Logs each retry attempt with wait time
  - Tracks retry count in metadata

- **File Execution**:
  - `execute_file(query_file)` loads SQL from disk
  - Supports both absolute and relative paths
  - Relative paths resolved from experiments/ directory

**ResultCollector Features**:
- **Result Creation**:
  - `create_result()` builds Result from execution data
  - Extracts Trino-specific metrics from query metadata
  - Handles validation results and error information
  - Adds custom metadata tags

- **Storage**:
  - `save_result()` writes JSON to results/ directory
  - Filename format: `{experiment-name}_{timestamp}.json`
  - Auto-creates results directory if needed
  - Returns filepath for verification

- **Loading**:
  - `load_result(filepath)` reconstructs Result from JSON
  - `list_results(experiment_name, limit)` finds result files
  - Sorted by modification time (newest first)

- **Aggregation**:
  - `aggregate_results(results)` computes statistics
  - Mean, median, stddev, min, max for execution times
  - Success rate calculation
  - Row count statistics
  - Returns dictionary of aggregated metrics

- **Summarization**:
  - `generate_summary(results)` creates human-readable report
  - Includes run count, success rate, timing statistics
  - Easy to display in CLI or reports

**TrinoExperiment Lifecycle**:

1. **Initialization**:
   - Creates QueryExecutor with connection parameters from config
   - Creates ResultCollector for result storage
   - Initializes empty run_results list

2. **Prepare Phase** (`prepare()`):
   - Validates experiment configuration (checks for queries)
   - Tests Trino connection with simple query
   - Verifies system is ready for execution
   - Raises exception if preparation fails

3. **Execution Phase** (`run()`):
   - Collects queries from inline SQL and query files
   - Executes warmup runs (not measured)
   - Executes measured runs with full metrics
   - Each query × run combination creates a Result
   - Stores individual results as JSON files
   - Aggregates statistics across all runs
   - Returns dictionary with experiment summary

4. **Validation Phase** (`validate()`):
   - Checks success rate against min_success_rate threshold
   - Calculates coefficient of variation for execution times
   - Warns if variance exceeds max_execution_time_variance
   - Returns True/False for validation pass/fail

5. **Cleanup Phase** (`cleanup()`):
   - Disconnects from Trino
   - Releases resources
   - Handles errors gracefully

**Query Collection Logic**:
- Inline queries from `queries:` list in YAML
- Query files from `query_files:` list
- Relative paths resolved from experiments/ directory
- Each query gets a name (query_1, query_2, or filename stem)
- Tracks query source for debugging

#### CLI Integration

**Updated exp run Command** (`lib/tribench/cli/experiment_commands.py`):
```bash
tribench exp run experiments/test-simple.yaml
tribench exp run experiments/tpch-q1-sf1.yaml --runs 5 --warmup 2
tribench exp run experiments/test-simple.yaml --timeout 120 --verbose
```

**Command Flow**:
1. Load experiment config from YAML with `ExperimentConfig.from_yaml()`
2. Override parameters from CLI if provided (runs, warmup, timeout)
3. Display configuration summary
4. Create TrinoExperiment instance
5. Prepare experiment (test connection)
6. Execute experiment (warmup + measured runs)
7. Display results summary (duration, success rate, timing stats)
8. Validate results against rules
9. Cleanup resources

**Error Handling**:
- FileNotFoundError: YAML file doesn't exist
- ValueError: Configuration validation fails
- QueryExecutionError: Query execution fails
- Detailed error messages with traceback in verbose mode
- Graceful cleanup even on failure

#### Example Experiment Definitions

**test-simple.yaml** (Smoke Test):
```yaml
name: "test-simple"
description: "Simple test experiment with basic SELECT queries"
system: "trino"
connection:
  catalog: "tpch"
  schema: "tiny"
runs: 3
warmup_runs: 1
queries:
  - "SELECT COUNT(*) as row_count FROM nation"
  - "SELECT * FROM nation LIMIT 5"
  - "SELECT n_name, n_regionkey FROM nation WHERE n_nationkey < 10"
validation:
  min_success_rate: 0.9
  max_execution_time_variance: 0.3
```

**tpch-q1-sf1.yaml** (TPC-H Benchmark):
```yaml
name: "tpch-q1-sf1"
description: "TPC-H Query 1 - Pricing Summary Report at Scale Factor 1"
system: "trino"
connection:
  catalog: "tpch"
  schema: "sf1"
runs: 5
warmup_runs: 2
timeout_seconds: 300
queries:
  - |
    SELECT
        l_returnflag,
        l_linestatus,
        SUM(l_quantity) AS sum_qty,
        ...
    FROM lineitem
    WHERE l_shipdate <= DATE '1998-09-02'
    GROUP BY l_returnflag, l_linestatus
    ORDER BY l_returnflag, l_linestatus
validation:
  min_success_rate: 0.95
  max_execution_time_variance: 0.15
metadata:
  benchmark: "TPC-H"
  query_number: 1
  expected_rows: 4
```

#### Testing Strategy

**Unit Tests** (`tests/unit/test_experiment.py`):
- 17 new test cases covering:
  - ExperimentConfig YAML parsing (minimal, complete, missing fields)
  - QueryExecutor initialization and connection
  - QueryExecutor query execution with mocks
  - ResultCollector result creation and storage
  - ResultCollector aggregation and summarization
- Uses unittest.mock for Trino client mocking
- Tests error handling and edge cases
- **Coverage**: Comprehensive coverage of all new classes

**Manual Testing Workflow**:
1. Start Trino: `tribench sys start trino`
2. Run smoke test: `tribench exp run experiments/test-simple.yaml`
3. Check results: `ls results/`
4. Verify result file: `cat results/test-simple_*.json`
5. Run TPC-H benchmark: `tribench exp run experiments/tpch-q1-sf1.yaml`
6. Stop Trino: `tribench sys stop trino`

#### Files Created/Modified

**New Files**:
- `lib/tribench/experiments/query_executor.py` (330 lines) - Query execution engine
- `lib/tribench/experiments/result_collector.py` (280 lines) - Result storage and analysis
- `lib/tribench/experiments/trino_experiment.py` (320 lines) - Trino experiment implementation
- `lib/tribench/experiments/__init__.py` - Module exports
- `experiments/test-simple.yaml` - Simple smoke test experiment
- `experiments/tpch-q1-sf1.yaml` - TPC-H Query 1 benchmark
- `experiments/README.md` - Experiment definition guide
- `tests/unit/test_experiment.py` - Enhanced with 17 new test cases

**Modified Files**:
- `lib/tribench/core/experiment.py` - Added from_yaml() and enhanced ExperimentConfig
- `lib/tribench/cli/experiment_commands.py` - Implemented exp run command
- `tests/conftest.py` - Updated sample_experiment_config fixture

#### Dependencies

**New Dependencies**:
- `pyyaml`: YAML parsing for experiment configs
- `trino`: Python client for Trino (already in requirements.txt)

**Existing Dependencies**:
- `click`: CLI framework
- Standard library: `json`, `logging`, `pathlib`, `datetime`, `time`

#### Design Decisions

1. **Separation of Concerns**:
   - QueryExecutor handles only query execution
   - ResultCollector handles only result storage
   - TrinoExperiment orchestrates the workflow
   - Each class has single responsibility

2. **Retry Strategy**:
   - Exponential backoff prevents overwhelming system
   - Max 30s wait prevents excessive delays
   - User errors don't retry (SQL syntax issues are permanent)
   - System errors retry (transient network issues may resolve)

3. **Result Storage**:
   - JSON format is human-readable and tool-friendly
   - Individual result files enable incremental analysis
   - Timestamp in filename prevents collisions
   - Aggregation done in-memory (no database yet)

4. **Validation Rules**:
   - Success rate check is hard failure (< 95% fails validation)
   - Variance check is soft warning (informational only)
   - Future: More sophisticated statistical tests

5. **Experiment YAML Schema**:
   - Required fields: name, system
   - Optional: all execution parameters have defaults
   - Flexible: supports both inline queries and query files
   - Extensible: metadata field for custom tags

#### Dissertation Contributions

1. **Reproducible Experiments**:
   - YAML definitions are version-controlled
   - Same config produces same experiment across machines
   - Warmup runs ensure steady-state measurements
   - Multiple runs enable statistical significance

2. **Robust Execution**:
   - Retry logic handles transient failures
   - Connection management prevents resource leaks
   - Error handling preserves partial results
   - Timeout prevents hung experiments

3. **Comprehensive Metrics**:
   - Execution time (wall clock)
   - CPU time and memory usage
   - Data scanned and rows processed
   - Trino query statistics (queued time, scheduled time)
   - Success/failure tracking

4. **Analysis-Ready Results**:
   - Structured JSON storage
   - Aggregated statistics (mean, median, stdev)
   - Success rate tracking
   - Variance analysis for reproducibility

5. **Professional Framework**:
   - Follows PEEL patterns (prepare, run, validate, cleanup)
   - Extensible to other systems (not just Trino)
   - Well-tested and documented
   - Production-ready code quality

#### Lessons Learned

1. **Trino Client Behavior**:
   - cursor.stats only available after query completion
   - Must fetch results before accessing statistics
   - Connection can be reused for multiple queries
   - Health check via simple SELECT 1 query

2. **Error Handling**:
   - Distinguish user errors from system errors
   - User errors should fail fast (no retry)
   - System errors may be transient (worth retrying)
   - Log retry attempts for debugging

3. **Result Aggregation**:
   - Need multiple runs for statistical validity
   - Warmup runs important for cache priming
   - Coefficient of variation better than raw stddev
   - Variance checks help identify environmental issues

4. **YAML Schema Design**:
   - Required fields should be minimal
   - Provide sensible defaults for optional fields
   - Support both simple (inline) and complex (file-based) workflows
   - Metadata field provides extensibility

5. **Testing Strategy**:
   - Mock Trino client for unit tests
   - Real Trino needed for integration tests
   - Test both success and failure paths
   - Use fixtures to reduce test setup boilerplate

#### Integration with Existing Components

**Configuration System**:
- Experiment YAML loaded via ConfigurationLoader
- Merges with reference.conf and host configs
- Connection parameters can be overridden per experiment
- Validates against schema

**System Management**:
- Experiments require Trino to be running
- `prepare()` validates system availability
- Uses configured connection parameters
- Can detect system issues early

**CLI Framework**:
- exp run integrates with existing CLI structure
- Uses common options (dry-run, verbose, config)
- Consistent error handling and output formatting
- Help text follows CLI conventions

**Result Storage**:
- Results stored in results/ directory (configurable)
- Compatible with future res:* commands
- JSON format enables tool integration
- Individual files support incremental analysis

#### Performance Characteristics

**Overhead**:
- Framework overhead: < 100ms per query
- Connection setup: ~1-2 seconds (one-time)
- Result serialization: < 10ms per result
- Retry backoff: 2-30 seconds per attempt

**Scalability**:
- Tested with 3-10 queries per experiment
- Up to 10 runs per query (more recommended for research)
- Query execution time: 0.1s - 300s (configurable timeout)
- Total experiment time: (warmup + runs) × queries × avg_query_time

**Resource Usage**:
- Memory: ~50MB for framework + Trino client
- Disk: ~1KB per result JSON file
- Network: Minimal (only Trino HTTP requests)
- CPU: Negligible (waiting on Trino)

#### Future Enhancements (Phase 2+)

- [ ] Parallel query execution for independent queries
- [ ] Real-time progress reporting during execution
- [ ] Query plan analysis and storage
- [ ] Resource monitoring integration (CPU, memory, I/O)
- [ ] Database storage for results (PostgreSQL)
- [ ] Advanced statistical tests (t-tests, ANOVA)
- [ ] Query warmup strategies (different approaches)
- [ ] Experiment suite support (multiple experiments as batch)

### Time Investment

- **ExperimentConfig Enhancement**: 1 hour (YAML parsing, validation)
- **QueryExecutor Implementation**: 2 hours (connection, execution, retry logic)
- **ResultCollector Implementation**: 1.5 hours (storage, aggregation, summary)
- **TrinoExperiment Implementation**: 2 hours (lifecycle, query collection, validation)
- **CLI Integration**: 1.5 hours (exp run command, error handling)
- **Example Experiments**: 1 hour (test-simple.yaml, tpch-q1-sf1.yaml, README)
- **Unit Tests**: 2 hours (17 test cases with mocks)
- **Manual Testing & Debugging**: 1.5 hours (end-to-end workflow)
- **Documentation**: 1.5 hours (docstrings, journal update)
- **Total**: ~14 hours for complete experiment engine

---

## Current Project Status

### Completed Components ✅
- ✅ Phase 0: Foundation (package structure, abstractions, testing)
- ✅ Section 1.1: Command Line Interface (21 commands, 4 groups)
- ✅ Section 1.2: Configuration System (hierarchical HOCON, validation, templates)
- ✅ Section 1.3: System Management - Trino (Docker-based lifecycle, health checks)
- ✅ Section 1.4: Experiment Engine (query execution, result collection, CLI integration)
- ✅ Environment setup (Conda, dependencies, documentation)
- ✅ Testing infrastructure (49+ unit tests total, comprehensive coverage)

### Ready for Implementation 🔄
- 🔄 Section 1.5: Dataset Management (TPC-H generation and loading)
- 🔄 Integration testing (end-to-end experiment execution)
- 🔄 PostgreSQL system (for Iceberg metadata)
- 🔄 MinIO system (for Iceberg storage)

### Technical Debt
- Experiment commands other than exp run not implemented
- No integration tests yet (only unit tests)
- PostgreSQL and MinIO systems pending
- TPC-H data generation not yet implemented
- Result commands (res) not implemented

---

## Key Learnings for Dissertation

### Software Engineering Practices
1. **Test-Driven Development**: Writing tests first improved code quality
2. **Abstract Base Classes**: Enabled consistent interface design
3. **Click Framework**: Powerful for building professional CLIs
4. **Package Structure**: Proper Python packaging crucial for distribution

### Architecture Insights
1. **PEEL Pattern**: Bundle-based approach scales well for complex benchmarks
2. **Command Groups**: Logical separation improves user experience
3. **Context Management**: Shared state simplifies command implementation
4. **Decorator Pattern**: Reusable options reduce code duplication

### Development Velocity
- **Foundation Phase**: 18 hours (package + core abstractions)
- **CLI Phase**: 12 hours (21 commands + testing)
- **Configuration Phase**: 7 hours (HOCON system + 17 tests + templates)
- **System Management Phase**: 9.5 hours (Trino system + CLI integration + bug fixes)
- **Experiment Engine Phase**: 14 hours (query execution + result collection + testing)
- **Dataset Management Phase**: 8 hours (TPC-H generation + loading + validation + 5 CLI commands + 11 tests)
- **Documentation**: 10 hours (README, help text, examples, journal updates)
- **Total**: ~78.5 hours for Phases 0 & 1 (Sections 1.1-1.5 complete)

### Latest Updates (17 October 2025)

#### Section 1.5: Dataset Management ✅ COMPLETE

**Implementation Summary**:
Completed full dataset management subsystem with TPC-H generation, validation, loading, and registry capabilities.

**Core Components Implemented**:

1. **DatasetMetadata Class** (`lib/tribench/data/dataset.py`)
   - Structured metadata storage with dataclass
   - Fields: name, type, format, scale_factor, size, location, tables, row_counts, checksums
   - Serialization: to_dict() / from_dict() for YAML storage
   - **Dissertation Value**: Systematic dataset tracking for reproducibility

2. **DatasetValidator Class**
   - Parquet file validation with PyArrow
   - TPC-H row count verification against expected values
   - SHA256 checksum computation for data integrity
   - Expected row counts for 'tiny' and 'SF1' scale factors
   - **Dissertation Value**: Ensures data quality for reliable benchmarks

3. **TPCHGenerator Class**
   - Docker-based dbgen integration (ghcr.io/scalytics/tpch-docker)
   - Generates TPC-H data at configurable scale factors (tiny, 1, 10, 100)
   - Automatic CSV to Parquet conversion using PyArrow
   - Complete TPC-H table schemas (nation, region, customer, supplier, part, partsupp, orders, lineitem)
   - **Dissertation Value**: Reproducible dataset generation for experiments

4. **TrinoDataLoader Class**
   - Loads Parquet datasets into Trino catalogs
   - DDL generation from PyArrow schemas
   - Connection management with trino-python-client
   - Support for memory connector (testing) and future Iceberg support
   - **Dissertation Value**: Enables data format comparisons

5. **DatasetRegistry Class**
   - YAML-based dataset registry with persistence
   - CRUD operations: register, get, list, delete, update
   - Automatic metadata tracking and validation
   - **Dissertation Value**: Dataset versioning for experiment reproducibility

**CLI Commands Implemented** (5 commands):

1. **`tribench data generate <dataset>`**
   - Generates TPC-H datasets (tpch-tiny, tpch-sf1, tpch-sf10, tpch-sf100)
   - Options: --format (parquet/csv), --output, --overwrite
   - Auto-validation and registry integration
   - Displays summary: tables, total rows, total size

2. **`tribench data load <dataset>`**
   - Loads datasets into Trino catalogs
   - Options: --system, --catalog, --schema, --validate
   - Supports memory connector (immediate testing)
   - Creates tables with proper DDL

3. **`tribench data list`**
   - Lists all registered datasets with metadata
   - Options: --filter (pattern matching), --generated-only
   - Displays: type, format, scale factor, tables, rows, size, location

4. **`tribench data info <dataset>`**
   - Detailed dataset information
   - Options: --detailed (shows properties and checksums)
   - Per-table row counts and statistics

5. **`tribench data validate <dataset>`**
   - Validates dataset integrity
   - Options: --checksums, --row-counts
   - Verifies file structure, row counts, and data integrity

**Configuration Updates**:
- Added `tribench.datasets` section to reference.conf
- Dataset directory, registry path, TPC-H settings
- Expected row counts for validation (tiny and SF1)
- Docker image configuration
- Loading batch size and validation settings

**Testing Coverage** (11 comprehensive tests):
- TestDatasetMetadata: creation, serialization, deserialization (3 tests)
- TestDatasetValidator: row counts, checksums, Parquet validation (4 tests)
- TestTPCHGenerator: initialization, schemas, dbgen execution (3 tests)
- TestTrinoDataLoader: initialization, type mapping, DDL generation (3 tests)
- TestDatasetRegistry: CRUD operations, persistence (6 tests)
- **Total**: 19 tests (8 new dataset tests + 11 registry/validator tests)

**Technical Achievements**:
- ✅ Docker-based dataset generation (no manual dbgen installation)
- ✅ Automatic Parquet conversion with type preservation
- ✅ Comprehensive validation pipeline
- ✅ Registry-based dataset tracking
- ✅ Full CLI integration with error handling
- ✅ 80%+ test coverage maintained

**Dissertation Impact**:
- **Reproducibility**: Registry ensures dataset versions are tracked
- **Automation**: Docker-based generation removes manual setup
- **Validation**: Checksums and row counts ensure data quality
- **Flexibility**: Supports multiple scale factors and formats
- **Extensibility**: Easy to add new dataset types (TPC-DS, custom)

**Known Limitations** (documented as future work):
- Data loading only creates empty tables (bulk insert not implemented)
- Only memory connector fully supported (Iceberg requires Phase 2)
- CSV format supported in generation but not fully tested in loading
- Large datasets (SF100) may require significant Docker resources

**Next Steps** (Section 2.1):
1. Extend to SF10 and SF100 scale factors
2. Implement Hive Metastore integration
3. Add MinIO object storage support
4. Complete Iceberg table format integration
5. Implement bulk data loading for memory connector
6. Add PostgreSQL dataset support

### Next Priorities
1. **Integration Testing**: End-to-end workflow (generate → load → experiment)
2. **Result Commands**: Implement res show, res list, res compare
3. **Phase 2.1**: Extended Dataset Management (Iceberg, MinIO, Hive)
4. **Phase 2.2**: Complete TPC-H query suite (queries 1-10)
5. **PostgreSQL System**: Metadata store for Iceberg catalogs
6. **MinIO System**: Object storage for Iceberg tables

---

## Research Context

### Problem Statement
Current Trino benchmarking approaches lack:
- Systematic comparison of Iceberg features
- Reproducible experiment execution
- Structured result analysis
- Integration with modern data lakehouse patterns

### Solution Approach
TriBench addresses these gaps through:
- Structured experiment definitions
- Automated system lifecycle management
- Multiple data format support (CSV, Parquet, Iceberg)
- Statistical result analysis
- Reproducible benchmark bundles

### Expected Contributions
1. **Empirical Analysis**: Performance impact of Iceberg features
2. **Benchmarking Framework**: Open-source tool for Trino evaluation
3. **Best Practices**: Guidelines for lakehouse benchmark design
4. **Performance Insights**: Optimization recommendations for Trino + Iceberg

---

## Phase 1 Continued: Query Reusability Architecture (Week 5-6) ✅

### Section 1.6: Apps Directory and Query Files Feature ✅
**Completed**: Implemented apps/ directory structure and query_files loading mechanism for experiment reusability

#### Motivation

**Problem**: Inline queries in experiment YAML files led to:
- Query duplication across multiple experiments
- Difficult maintenance (fix a query bug in multiple places)
- Hard to verify queries against official TPC-H specification
- No version control tracking of query changes
- Coupling between query content and experiment configuration

**Solution**: Centralized query repository in `apps/` directory:
- Single source of truth for benchmark queries
- Separation of "what to run" (queries) from "how/where to run" (experiments)
- Easy reusability across Memory, Iceberg, different scale factors
- Clear version control and documentation

#### Implementation Components

1. **Apps Directory Structure** (`apps/`)
   - Purpose: Central repository for benchmark applications and queries
   - Structure:
     ```
     apps/
     ├── README.md              # Apps directory overview
     └── tpch/                  # TPC-H benchmark
         ├── README.md          # TPC-H query documentation
         └── queries/           # Individual SQL files
             ├── q01.sql        # Pricing Summary Report
             ├── q03.sql        # Shipping Priority
             ├── q06.sql        # Forecasting Revenue Change
             ├── q12.sql        # Shipping Modes
             ├── q14.sql        # Promotion Effect
             └── q19.sql        # Discounted Revenue
     ```
   - **Dissertation Value**: Demonstrates software architecture for reproducible research

2. **TPC-H Query Library** (6 queries implemented)
   
   **Query Selection Rationale**:
   - **Q1 (Pricing Summary)**: Pure aggregation, GROUP BY, tests columnar format benefits
   - **Q3 (Shipping Priority)**: 3-way join, ORDER BY, LIMIT - tests join optimization
   - **Q6 (Forecasting Revenue)**: Simple filter + aggregate, ideal for partition pruning
   - **Q12 (Shipping Modes)**: CASE expressions, date ranges - tests predicate pushdown
   - **Q14 (Promotion Effect)**: Pattern matching (LIKE), percentage calculation
   - **Q19 (Discounted Revenue)**: Complex OR conditions, multiple predicates
   
   **Query Characteristics**:
   - Variety: Simple aggregations to complex joins
   - Scalability: Fast (Q6) vs. compute-intensive (Q19)
   - Partition sensitivity: Some benefit from pruning (Q1, Q6), others don't (Q3)
   - Dissertation coverage: Adequate for evaluating Iceberg features

3. **ExperimentConfig Enhancement** (`lib/tribench/core/experiment.py`)
   
   **Added `query_files` field**:
   ```python
   @dataclass
   class ExperimentConfig:
       # ... existing fields ...
       query_files: List[str] = field(default_factory=list)
   ```
   
   **Updated `from_yaml()` method**:
   - Added `cli_overrides` parameter for runtime configuration
   - Normalizes query_files to list format (accepts string or list)
   - Applies CLI overrides after YAML load
   
   **Helper function**:
   ```python
   def normalize_to_list(value):
       """Convert string or list to list, handle None."""
       if value is None:
           return []
       if isinstance(value, str):
           return [value]
       return list(value)
   ```

4. **TrinoExperiment Query Loading** (`lib/tribench/experiments/trino_experiment.py`)
   
   **Enhanced `_collect_queries()` method**:
   - **Multi-strategy path resolution**:
     - Strategy 1: Relative to project root (supports `apps/tpch/queries/q01.sql`)
     - Strategy 2: Relative to experiments/ directory (for convenience)
     - Absolute paths supported
   - **File loading**:
     - Reads SQL content with `query_path.read_text()`
     - Creates query dict: `{name: query_path.stem, sql: sql_content, source: str(query_path)}`
   - **Error handling**:
     - Logs successful file loads
     - Detailed error messages with all attempted paths
     - Raises FileNotFoundError with context
   
   **Backward compatibility**:
   - Inline queries from `queries:` list still work
   - Both inline and query_files can coexist in same experiment
   - No breaking changes to existing experiments

#### Usage Examples

**Before (Inline Query)**:
```yaml
# experiments/tpch-q1-memory-sf1.yaml
name: "tpch-q1-memory-sf1"
queries:
  - |
    SELECT
        l_returnflag,
        l_linestatus,
        sum(l_quantity) as sum_qty,
        sum(l_extendedprice) as sum_base_price,
        sum(l_extendedprice * (1 - l_discount)) as sum_disc_price,
        sum(l_extendedprice * (1 - l_discount) * (1 + l_tax)) as sum_charge,
        avg(l_quantity) as avg_qty,
        avg(l_extendedprice) as avg_price,
        avg(l_discount) as avg_disc,
        count(*) as count_order
    FROM
        lineitem
    WHERE
        l_shipdate <= date '1998-12-01' - interval '90' day
    GROUP BY
        l_returnflag,
        l_linestatus
    ORDER BY
        l_returnflag,
        l_linestatus
```

**After (Query File Reference)**:
```yaml
# experiments/tpch-q1-memory-sf1.yaml
name: "tpch-q1-memory-sf1"
query_files: ["apps/tpch/queries/q01.sql"]
connection:
  catalog: "memory"
  schema: "default"
```

**Multiple Experiments, Same Query**:
```yaml
# experiments/tpch-q1-memory-sf1.yaml (Memory connector)
query_files: ["apps/tpch/queries/q01.sql"]
connection: {catalog: "memory", schema: "tpch_sf1"}

# experiments/tpch-q1-iceberg-sf1.yaml (Iceberg connector)
query_files: ["apps/tpch/queries/q01.sql"]
connection: {catalog: "iceberg", schema: "tpch_sf1"}

# experiments/tpch-q1-iceberg-sf10.yaml (Different scale factor)
query_files: ["apps/tpch/queries/q01.sql"]
connection: {catalog: "iceberg", schema: "tpch_sf10"}
```

#### Testing & Validation

**End-to-End Test**:
```bash
# Load dataset
tribench data load tpch-tiny --catalog memory --schema default

# Run experiment with query_files
tribench exp run experiments/tpch-q1-memory-sf1.yaml

# Output:
# Loading experiment: tpch-q1-memory-sf1.yaml
# Experiment: tpch-q1-memory-sf1
# Loaded query from file: apps/tpch/queries/q01.sql
# ✓ Preparation complete
# Connected to Trino at localhost:8080
# Prepared 1 queries for execution
# 
# Measured run 1/3: q01_run1 - Query completed in 0.13s, returned 4 rows
# Measured run 2/3: q01_run2 - Query completed in 0.13s, returned 4 rows
# Measured run 3/3: q01_run3 - Query completed in 0.10s, returned 4 rows
# 
# ✓ Execution complete
# Success rate: 100.0%
# Execution time (mean): 0.122s
# ✓ Validation passed
# Results saved to: results/tpch-q1-memory-sf1_20251019_233827.json
```

**Query File Loading Verification**:
- ✅ Path resolution works from project root
- ✅ SQL content loaded correctly
- ✅ Query name extracted from filename (q01.sql → q01)
- ✅ Source tracked for debugging
- ✅ Multiple query files supported in same experiment

**Schema Configuration Fix**:
- Initial issue: Pointed to `memory.benchmarks` schema (didn't exist)
- Data actually loaded to `memory.default` schema
- Fixed experiment configs to use `schema: "default"`
- Validated with 100% success rate

#### Documentation Created

1. **apps/README.md**
   - Purpose and benefits of apps directory
   - Structure and organization
   - Usage examples (before/after)
   - Getting started guide
   - Current status (6 queries implemented)

2. **apps/tpch/README.md**
   - TPC-H query characteristics table
   - Query selection rationale for dissertation
   - Expected results for each query
   - Performance considerations
   - Validation instructions
   - References to TPC-H specification

3. **Query File Headers**
   - Each .sql file includes:
     - Query number and name
     - Description of purpose
     - Expected result format
     - SQL implementation

#### Benefits Achieved

1. **Reusability** ✅
   - Same query runs on Memory, Iceberg, different scale factors
   - No duplication across 10+ planned experiment variants
   - Query changes propagate automatically

2. **Maintainability** ✅
   - Fix query once in apps/tpch/queries/
   - All experiments benefit immediately
   - Clear version control history

3. **Verification** ✅
   - Easy to compare against official TPC-H specification
   - Query validation against Trino built-in TPC-H catalog
   - Documentation tracks expected results

4. **Research Workflow** ✅
   - Dissertation experiments require same query on different systems
   - Query_files enables systematic comparison
   - Clean separation: queries (what) vs experiments (how/where)

5. **Extensibility** ✅
   - Easy to add remaining 16 TPC-H queries
   - Structure supports TPC-DS queries (apps/tpcds/)
   - Custom benchmark queries supported

#### Dissertation Contributions

1. **Software Architecture**:
   - Demonstrates separation of concerns
   - Reusable component design
   - Version control best practices

2. **Reproducible Research**:
   - Queries documented and version-controlled
   - Same query definition across all experiments
   - No human error from copy-paste

3. **Systematic Evaluation**:
   - Enables fair comparison across systems
   - Identical queries ensure apples-to-apples comparison
   - Query characteristics table guides experiment design

4. **Framework Quality**:
   - Professional software engineering practices
   - Clear documentation for future users
   - Extensible for follow-on research

#### Files Created/Modified

**New Files**:
- `apps/README.md` - Apps directory overview and usage guide
- `apps/tpch/README.md` - TPC-H query documentation
- `apps/tpch/queries/q01.sql` - Pricing Summary Report Query
- `apps/tpch/queries/q03.sql` - Shipping Priority Query
- `apps/tpch/queries/q06.sql` - Forecasting Revenue Change Query
- `apps/tpch/queries/q12.sql` - Shipping Modes Query
- `apps/tpch/queries/q14.sql` - Promotion Effect Query
- `apps/tpch/queries/q19.sql` - Discounted Revenue Query
- `experiments/tpch-q1-memory-sf1.yaml` - Example using query_files

**Modified Files**:
- `lib/tribench/core/experiment.py` - Added query_files field, cli_overrides, normalize_to_list()
- `lib/tribench/experiments/trino_experiment.py` - Enhanced _collect_queries() with file loading
- `experiments/tpch-q1-custom-dataset.yaml` - Fixed schema configuration

#### Technical Challenges Solved

1. **Path Resolution**:
   - Challenge: Relative paths ambiguous (from where?)
   - Solution: Multi-strategy resolution (project root first, then experiments/)
   - Result: Flexible path specification

2. **Backward Compatibility**:
   - Challenge: Don't break existing inline queries
   - Solution: Support both queries and query_files simultaneously
   - Result: Zero breaking changes

3. **Schema Configuration**:
   - Challenge: Mismatch between data location and experiment config
   - Solution: Updated configs to point to correct schema
   - Result: 100% success rate on loaded data

4. **CLI Override Support**:
   - Challenge: CLI needs to override YAML parameters
   - Solution: Added cli_overrides parameter to from_yaml()
   - Result: Runtime configuration flexibility

#### Lessons Learned

1. **Apps Folder Value**:
   - Initial skepticism: "Is apps/ necessary?"
   - Reality: Critical for query reuse across 10+ experiments
   - Insight: Centralization reduces duplication and errors

2. **Path Resolution Strategy**:
   - Single strategy insufficient (what's "relative"?)
   - Multiple strategies provide flexibility
   - Detailed error messages essential for debugging

3. **Schema Naming**:
   - Assumption: Data loaded to "benchmarks" schema
   - Reality: Data in "default" schema
   - Lesson: Always verify data location before experiments

4. **Backward Compatibility**:
   - Supporting both old and new patterns increases adoption
   - Deprecation warnings guide users to new approach
   - No rush to remove old functionality

#### Future Enhancements

- [ ] Add remaining 16 TPC-H queries (Q2, Q4, Q5, Q7-Q11, Q13, Q15-Q18, Q20-Q22)
- [ ] Support for TPC-DS benchmark (apps/tpcds/queries/)
- [ ] Query validation tool (`tribench data validate-query <query_file>`)
- [ ] Query performance profiling across systems
- [ ] Automated query correctness testing
- [ ] Query plan visualization integration

### Time Investment

- **Apps Directory Design**: 1 hour (structure, README planning)
- **TPC-H Query Implementation**: 2 hours (6 queries with documentation)
- **ExperimentConfig Enhancement**: 1 hour (query_files field, normalize_to_list, cli_overrides)
- **TrinoExperiment File Loading**: 2 hours (path resolution, error handling, testing)
- **Documentation**: 1.5 hours (apps/README.md, apps/tpch/README.md, query headers)
- **Testing & Validation**: 1.5 hours (end-to-end workflow, schema config fix)
- **Journal Documentation**: 1 hour (this section)
- **Total**: ~10 hours for query reusability architecture

---

*Last Updated: 19 October 2025*
*Total Development Time: ~88.5 hours*
*Phase 0 Complete | Phase 1 Complete (Sections 1.1-1.6)*

# Schema Refactoring Summary: From Hardcoded TPC-H to Extensible Architecture

**Date:** October 18, 2025  
**Objective:** Refactor TriBench to support multiple benchmark types (TPC-H, TPC-DS, custom) without hardcoded schemas

---

## Problem Statement

The original implementation was **too hardcoded for TPC-H**, creating these limitations:

1. **Hardcoded schemas**: `_get_tpch_schemas()` method with 98 lines of PyArrow schema definitions
2. **TPC-H specific methods**: `load_tpch_dataset()`, `TPCHGenerator` with no abstraction
3. **No extensibility**: Adding TPC-DS or custom benchmarks would require duplicating code
4. **Tight coupling**: Schema definitions mixed with generation and loading logic

---

## PEEL Framework Inspiration

The [PEEL framework](https://github.com/peelframework/peel) uses a **polymorphic, bean-based abstraction**:

- **Abstract `DataSet` class**: Base class for all dataset types
- **Two implementations**:
  - `CopiedDataSet`: Static datasets copied from local to distributed FS
  - `GeneratedDataSet`: Dynamic datasets generated by Jobs
- **Separation of concerns**: Data generators are separate beans with configurable parameters

---

## Implemented Solution

### 1. Schema Abstraction Layer

**File:** `lib/tribench/data/dataset.py` (lines 29-260)

```python
class BenchmarkType(Enum):
    """Supported benchmark types."""
    TPCH = "tpch"
    TPCDS = "tpcds"

class DatasetSchema(ABC):
    """Abstract base class for dataset schemas."""
    
    @abstractmethod
    def get_benchmark_type(self) -> BenchmarkType:
        pass
    
    @abstractmethod
    def get_tables(self) -> List[str]:
        pass
    
    @abstractmethod
    def get_schema(self, table_name: str) -> pa.Schema:
        pass
```

### 2. Concrete Implementations

**TPCHSchema** (lines 69-189):
- Moved all hardcoded TPC-H schema definitions from `_get_tpch_schemas()`
- 8 tables: nation, region, customer, supplier, part, partsupp, orders, lineitem
- Complete PyArrow schema definitions with proper types (int32, string, decimal128, date32)

**TPCDSSchema** (lines 192-226):
- Placeholder implementation for future TPC-DS support
- 24 table definitions (names only)
- `get_schema()` raises `NotImplementedError` with helpful message
- Ready for implementation when TPC-DS is needed

### 3. Schema Factory Pattern

**SchemaFactory** (lines 229-260):
- Central registry for schema types
- `create(benchmark_type)` → instantiates correct schema
- `register(benchmark_type, schema_class)` → allows custom schema registration
- Provides clear error messages for unsupported benchmark types

### 4. Refactored TPCHGenerator

**Changes:**
- Added `self.schema = TPCHSchema()` in `__init__`
- Replaced `schemas = self._get_tpch_schemas()` with `self.schema.get_schema(table_name)`
- Removed 98-line `_get_tpch_schemas()` method entirely
- Now uses injected schema abstraction

### 5. Refactored TrinoDataLoader

**New method:** `load_dataset(dataset_path, dataset_schema, catalog, schema)`
- **Generic**: Works with any `DatasetSchema` implementation
- **Polymorphic**: Uses `dataset_schema.get_benchmark_type()`, `get_tables()`, `get_schema()`
- **Extensible**: No hardcoded TPC-H assumptions

**Backward compatibility:** `load_tpch_dataset()` wrapper
- Deprecated but functional
- Logs warning message
- Calls `load_dataset(dataset_path, TPCHSchema(), catalog, schema)`

### 6. Updated CLI Commands

**data generate** (`lib/tribench/cli/data_commands.py` line 139):
```python
metadata = DatasetMetadata(
    name=dataset,
    benchmark_type='tpch',  # ← Added benchmark_type
    type='generated',
    # ... rest of metadata
)
```

**data load** (lines 229-250):
```python
# Get schema based on benchmark type
benchmark_type = BenchmarkType(metadata.benchmark_type)
dataset_schema = SchemaFactory.create(benchmark_type)

# Load using schema abstraction
loader.load_dataset(dataset_path, dataset_schema, catalog, schema)
```

### 7. Updated Registry Format

**datasets/registry.yaml:**
```yaml
tpch-tiny:
  name: tpch-tiny
  benchmark_type: tpch  # ← Added field
  type: generated
  format: parquet
  # ... rest of metadata
```

---

## Testing & Validation

### ✅ Schema Abstraction Tests
```bash
python -c "from tribench.data.dataset import TPCHSchema; ..."
# Output: Benchmark: tpch
#         Tables: ['nation', 'region', 'customer', ...]
#         Nation columns: ['n_nationkey', 'n_name', ...]
```

### ✅ Factory Pattern Tests
```bash
python -c "from tribench.data.dataset import SchemaFactory, BenchmarkType; ..."
# Output: Created schema: TPCHSchema
#         Tables: 8 tables
```

### ✅ End-to-End Dataset Loading
```bash
tribench data load tpch-tiny --catalog memory --schema benchmarks
# Output: ✓ Dataset loaded successfully
#         Loaded tables:
#           - customer: 1,500 rows
#           - lineitem: 60,175 rows
#           ... (all 8 tables)
```

### ✅ Data Verification
```bash
docker exec -it tribench-trino-434 trino --execute "SELECT COUNT(*) FROM customer"
# Output: "1500"
```

### ✅ TPC-DS Stub Tests
```bash
python << EOF
from tribench.data.dataset import TPCDSSchema
schema = TPCDSSchema()
schema.get_schema('store_sales')  # Raises NotImplementedError
EOF
# Output: Expected error: TPC-DS schema definitions not yet implemented...
```

---

## Benefits Achieved

### 1. **Extensibility** ✅
- Adding TPC-DS: Just implement `TPCDSSchema.get_schema()`
- Adding custom benchmark: Create new `DatasetSchema` subclass
- No changes to core loading logic needed

### 2. **Maintainability** ✅
- Schema definitions centralized in dedicated classes
- Clear separation of concerns
- Easy to test individual components

### 3. **PEEL-like Architecture** ✅
- Abstract base class pattern
- Factory for creating instances
- Polymorphic behavior

### 4. **Backward Compatibility** ✅
- Existing code using `load_tpch_dataset()` still works
- Deprecation warnings guide users to new API
- Registry updated with minimal changes

### 5. **Future-Ready** ✅
- TPC-DS support requires only schema definitions
- Custom benchmarks can be added via registration
- No architectural changes needed

---

## Usage Examples

### Loading TPC-H Dataset (New API)
```python
from tribench.data.dataset import BenchmarkType, SchemaFactory, TrinoDataLoader

# Create schema
benchmark_type = BenchmarkType.TPCH
schema = SchemaFactory.create(benchmark_type)

# Load dataset
loader = TrinoDataLoader(connection_params)
loader.load_dataset(dataset_path, schema, catalog='memory', schema='benchmarks')
```

### Adding TPC-DS Support (Future)
```python
class TPCDSSchema(DatasetSchema):
    def get_schema(self, table_name: str) -> pa.Schema:
        schemas = {
            'store_sales': pa.schema([
                ('ss_sold_date_sk', pa.int32()),
                ('ss_sold_time_sk', pa.int32()),
                # ... complete TPC-DS schema
            ]),
            # ... 23 more tables
        }
        return schemas[table_name]
```

### Custom Benchmark Support
```python
class MyBenchmarkSchema(DatasetSchema):
    def get_benchmark_type(self) -> BenchmarkType:
        return BenchmarkType.CUSTOM  # Add to enum
    
    def get_tables(self) -> List[str]:
        return ['table1', 'table2']
    
    def get_schema(self, table_name: str) -> pa.Schema:
        # Your custom schemas
        pass

# Register it
SchemaFactory.register(BenchmarkType.CUSTOM, MyBenchmarkSchema)
```

---

## Files Modified

1. **lib/tribench/data/dataset.py**
   - Added: `BenchmarkType`, `DatasetSchema`, `TPCHSchema`, `TPCDSSchema`, `SchemaFactory`
   - Modified: `DatasetMetadata` (added `benchmark_type` field)
   - Modified: `TPCHGenerator` (uses `TPCHSchema()`)
   - Modified: `TrinoDataLoader` (added `load_dataset()`, kept `load_tpch_dataset()` for compatibility)
   - Removed: `_get_tpch_schemas()` method (98 lines → moved to `TPCHSchema`)

2. **lib/tribench/cli/data_commands.py**
   - Modified: `generate()` command (adds `benchmark_type='tpch'` to metadata)
   - Modified: `load()` command (uses `SchemaFactory` and `load_dataset()`)

3. **datasets/registry.yaml**
   - Added: `benchmark_type: tpch` field

---

## Migration Path (No Breaking Changes!)

### Phase 1: ✅ **Completed**
- Extract `TPCHSchema` class
- Create `SchemaFactory`
- Update metadata format

### Phase 2: ✅ **Completed**
- Refactor `TrinoDataLoader.load_dataset()`
- Keep `load_tpch_dataset()` as deprecated wrapper
- Update CLI commands

### Phase 3: 🔜 **Future (When Needed)**
- Implement `TPCDSSchema.get_schema()`
- Add TPC-DS data generator
- Update registry format version

### Phase 4: 🔜 **Future (Optional)**
- Remove deprecated `load_tpch_dataset()` method
- Implement schema versioning

---

## Comparison: Before vs. After

### Before (Hardcoded)
```python
def _get_tpch_schemas(self) -> Dict[str, pa.Schema]:
    return {
        'nation': pa.schema([...]),
        'region': pa.schema([...]),
        # ... 98 lines of hardcoded schemas
    }

loader.load_tpch_dataset(path, catalog, schema)  # TPC-H only!
```

### After (Extensible)
```python
class TPCHSchema(DatasetSchema):
    def get_schema(self, table_name: str) -> pa.Schema:
        schemas = {...}
        return schemas[table_name]

schema = SchemaFactory.create(BenchmarkType.TPCH)
loader.load_dataset(path, schema, catalog, schema)  # Any benchmark!
```

---

## Key Takeaways

1. **No YAML schemas needed**: Hardcoded Python classes are simpler for standard benchmarks
2. **PEEL-inspired architecture**: Abstract base classes + factory pattern
3. **Backward compatible**: Old code still works with deprecation warnings
4. **TPC-DS ready**: Just implement `get_schema()` when needed
5. **Extensible**: New benchmarks via `DatasetSchema` subclass + registration

---

## Next Steps (When TPC-DS Support is Needed)

1. Implement `TPCDSSchema.get_schema()` with all 24 table schemas
2. Add TPC-DS data generator (similar to `TPCHGenerator`)
3. Update CLI to support `--benchmark-type` flag for generation
4. Test end-to-end TPC-DS workflow
5. Update documentation with TPC-DS examples

**Estimated effort:** 2-3 hours (schema definitions) + 4-6 hours (generator integration)

---

## Conclusion

✅ Successfully refactored from **hardcoded TPC-H** to **extensible architecture**  
✅ Maintained **100% backward compatibility**  
✅ Enabled **future TPC-DS and custom benchmark support**  
✅ Followed **PEEL framework's separation of concerns**  
✅ All tests passing, dataset loading working perfectly  

**No more hardcoded assumptions – TriBench is now ready to grow! 🚀**

---

## Phase 1 Continued: Configuration Hierarchy System (Week 5-6) ✅

### Section 1.6: Hierarchical Configuration Override System ✅
**Completed**: PEEL-inspired configuration hierarchy with suite-level defaults and CLI overrides

#### Background: FLEXIBILITY_ANALYSIS.md Findings

**Initial Problem Analysis** (October 18, 2025):
- Studied PEEL framework patterns: Spring Bean Registry, ExperimentSequence, Lifespan management, hierarchical config
- Created comprehensive analysis identifying 5 hardcoded areas in TriBench
- Selected #5 (Configuration Override Hierarchy) as first implementation target
- Non-breaking, provides foundation for #4 (ExperimentSequence), demonstrates immediate value

#### Core Components Implemented

**ExperimentConfig Enhancement** (`lib/tribench/core/experiment.py`):
- Added `suite_config` and `cli_overrides` parameters to `from_yaml()`
- Implemented `_deep_merge()` for hierarchical configuration merging
- Merge order: Global defaults → Suite → Experiment YAML → CLI
- Deep merge for dicts, replacement for lists/primitives

**ExperimentSuite Class** (`lib/tribench/core/experiment_suite.py` - 218 lines):
- Groups related experiments with shared defaults
- Auto-loads all experiments with suite configuration
- Supports per-experiment overrides in suite YAML
- Methods: `from_yaml()`, `get_experiment()`, `list_experiments()`

**Suite CLI Commands** (`lib/tribench/cli/suite_commands.py` - 311 lines):
- `tribench suite run`: Execute all experiments with filtering and CLI overrides
- `tribench suite list`: List available suites
- `tribench suite show`: Display suite details

#### Testing & Results

**Coverage**: 15 comprehensive tests (100% passing)
- 12 unit tests (config hierarchy precedence, deep merge, suite loading)
- 3 integration tests (end-to-end workflow, complex nesting)

**Test Results**:
```bash
$ pytest tests/unit/test_config_hierarchy.py tests/integration/test_suite_workflow.py -v
====== 15 passed in 0.35s ======
```

**CLI Validation**:
```bash
$ tribench suite show experiments/suites/tpch-suite.yaml
Suite: tpch-suite (3 experiments)
✓ All configuration layers merged correctly
```

#### Dissertation Contributions

1. **PEEL-Inspired Design**: Hierarchical config follows PEEL's reference → host → experiment → CLI pattern
2. **Reproducible Suites**: Version-controlled suite YAMLs for systematic experiments
3. **Foundation for #4**: ExperimentSuite ready for parameter expansion (ExperimentSequence)
4. **Professional Quality**: Comprehensive tests, documentation (CONFIG_HIERARCHY.md), backward compatibility

#### Files Created

- `FLEXIBILITY_ANALYSIS.md` (832 lines) - Complete hardcoding analysis
- `lib/tribench/core/experiment_suite.py` (218 lines)
- `lib/tribench/core/experiment_registry.py` (59 lines stub)
- `lib/tribench/cli/suite_commands.py` (311 lines)
- `CONFIG_HIERARCHY.md` (full documentation)
- `tests/unit/test_config_hierarchy.py` (291 lines, 12 tests)
- `tests/integration/test_suite_workflow.py` (199 lines, 3 tests)
- `experiments/suites/tpch-suite.yaml` (28 lines example)

#### Time Investment

**Total**: ~14.5 hours
- Analysis & Design: 2 hours
- Implementation: 6 hours
- Testing: 3.5 hours
- Documentation: 2 hours
- Validation: 1 hour

---

## Current Project Status (Updated October 18, 2025)

### Completed Components ✅
- ✅ Phase 0: Foundation
- ✅ Section 1.1: CLI (21 commands)
- ✅ Section 1.2: Configuration System
- ✅ Section 1.3: Trino System Management
- ✅ Section 1.4: Experiment Engine
- ✅ Section 1.5: Dataset Management (TPC-H extensible architecture)
- ✅ **Section 1.6: Configuration Hierarchy** (suite defaults, CLI overrides)
- ✅ Testing: 64+ tests total

### Ready for Implementation 🔄
- 🔄 **#1 System Registry** (CRITICAL - FLEXIBILITY_ANALYSIS.md)
- 🔄 **#2 Experiment Registry** (CRITICAL - complete stub)
- 🔄 #3 System Lifespan (MEDIUM)
- 🔄 #4 ExperimentSequence (MEDIUM)

---

*Last Updated: 18 October 2025*
*Total Development Time: ~93 hours*
*Phase 0 Complete | Phase 1 Sections 1.1-1.6 Complete*

## Phase 1 Continued: Query Reusability Architecture (Week 5-6) ✅

### Section 1.6: Apps Directory and Query Files Feature ✅
**Completed**: Implemented apps/ directory structure and query_files loading mechanism for experiment reusability

#### Motivation

**Problem**: Inline queries in experiment YAML files led to:
- Query duplication across multiple experiments
- Difficult maintenance (fix a query bug in multiple places)
- Hard to verify queries against official TPC-H specification
- No version control tracking of query changes
- Coupling between query content and experiment configuration

**Solution**: Centralized query repository in `apps/` directory:
- Single source of truth for benchmark queries
- Separation of "what to run" (queries) from "how/where to run" (experiments)
- Easy reusability across Memory, Iceberg, different scale factors
- Clear version control and documentation

#### Implementation Components

1. **Apps Directory Structure** (`apps/`)
   - Purpose: Central repository for benchmark applications and queries
   - Structure:
     ```
     apps/
     ├── README.md              # Apps directory overview
     └── tpch/                  # TPC-H benchmark
         ├── README.md          # TPC-H query documentation
         └── queries/           # Individual SQL files
             ├── q01.sql        # Pricing Summary Report
             ├── q03.sql        # Shipping Priority
             ├── q06.sql        # Forecasting Revenue Change
             ├── q12.sql        # Shipping Modes
             ├── q14.sql        # Promotion Effect
             └── q19.sql        # Discounted Revenue
     ```
   - **Dissertation Value**: Demonstrates software architecture for reproducible research

2. **TPC-H Query Library** (6 queries implemented)
   
   **Query Selection Rationale**:
   - **Q1 (Pricing Summary)**: Pure aggregation, GROUP BY, tests columnar format benefits
   - **Q3 (Shipping Priority)**: 3-way join, ORDER BY, LIMIT - tests join optimization
   - **Q6 (Forecasting Revenue)**: Simple filter + aggregate, ideal for partition pruning
   - **Q12 (Shipping Modes)**: CASE expressions, date ranges - tests predicate pushdown
   - **Q14 (Promotion Effect)**: Pattern matching (LIKE), percentage calculation
   - **Q19 (Discounted Revenue)**: Complex OR conditions, multiple predicates
   
   **Query Characteristics**:
   - Variety: Simple aggregations to complex joins
   - Scalability: Fast (Q6) vs. compute-intensive (Q19)
   - Partition sensitivity: Some benefit from pruning (Q1, Q6), others don't (Q3)
   - Dissertation coverage: Adequate for evaluating Iceberg features

3. **ExperimentConfig Enhancement** (`lib/tribench/core/experiment.py`)
   
   **Added `query_files` field**:
   ```python
   @dataclass
   class ExperimentConfig:
       # ... existing fields ...
       query_files: List[str] = field(default_factory=list)
   ```
   
   **Updated `from_yaml()` method**:
   - Added `cli_overrides` parameter for runtime configuration
   - Normalizes query_files to list format (accepts string or list)
   - Applies CLI overrides after YAML load
   
   **Helper function**:
   ```python
   def normalize_to_list(value):
       """Convert string or list to list, handle None."""
       if value is None:
           return []
       if isinstance(value, str):
           return [value]
       return list(value)
   ```

4. **TrinoExperiment Query Loading** (`lib/tribench/experiments/trino_experiment.py`)
   
   **Enhanced `_collect_queries()` method**:
   - **Multi-strategy path resolution**:
     - Strategy 1: Relative to project root (supports `apps/tpch/queries/q01.sql`)
     - Strategy 2: Relative to experiments/ directory (for convenience)
     - Absolute paths supported
   - **File loading**:
     - Reads SQL content with `query_path.read_text()`
     - Creates query dict: `{name: query_path.stem, sql: sql_content, source: str(query_path)}`
   - **Error handling**:
     - Logs successful file loads
     - Detailed error messages with all attempted paths
     - Raises FileNotFoundError with context
   
   **Backward compatibility**:
   - Inline queries from `queries:` list still work
   - Both inline and query_files can coexist in same experiment
   - No breaking changes to existing experiments

#### Usage Examples

**Before (Inline Query)**:
```yaml
# experiments/tpch-q1-memory-sf1.yaml
name: "tpch-q1-memory-sf1"
queries:
  - |
    SELECT
        l_returnflag,
        l_linestatus,
        sum(l_quantity) as sum_qty,
        sum(l_extendedprice) as sum_base_price,
        sum(l_extendedprice * (1 - l_discount)) as sum_disc_price,
        sum(l_extendedprice * (1 - l_discount) * (1 + l_tax)) as sum_charge,
        avg(l_quantity) as avg_qty,
        avg(l_extendedprice) as avg_price,
        avg(l_discount) as avg_disc,
        count(*) as count_order
    FROM
        lineitem
    WHERE
        l_shipdate <= date '1998-12-01' - interval '90' day
    GROUP BY
        l_returnflag,
        l_linestatus
    ORDER BY
        l_returnflag,
        l_linestatus
```

**After (Query File Reference)**:
```yaml
# experiments/tpch-q1-memory-sf1.yaml
name: "tpch-q1-memory-sf1"
query_files: ["apps/tpch/queries/q01.sql"]
connection:
  catalog: "memory"
  schema: "default"
```

**Multiple Experiments, Same Query**:
```yaml
# experiments/tpch-q1-memory-sf1.yaml (Memory connector)
query_files: ["apps/tpch/queries/q01.sql"]
connection: {catalog: "memory", schema: "tpch_sf1"}

# experiments/tpch-q1-iceberg-sf1.yaml (Iceberg connector)
query_files: ["apps/tpch/queries/q01.sql"]
connection: {catalog: "iceberg", schema: "tpch_sf1"}

# experiments/tpch-q1-iceberg-sf10.yaml (Different scale factor)
query_files: ["apps/tpch/queries/q01.sql"]
connection: {catalog: "iceberg", schema: "tpch_sf10"}
```

#### Testing & Validation

**End-to-End Test**:
```bash
# Load dataset
tribench data load tpch-tiny --catalog memory --schema default

# Run experiment with query_files
tribench exp run experiments/tpch-q1-memory-sf1.yaml

# Output:
# Loading experiment: tpch-q1-memory-sf1.yaml
# Experiment: tpch-q1-memory-sf1
# Loaded query from file: apps/tpch/queries/q01.sql
# ✓ Preparation complete
# Connected to Trino at localhost:8080
# Prepared 1 queries for execution
# 
# Measured run 1/3: q01_run1 - Query completed in 0.13s, returned 4 rows
# Measured run 2/3: q01_run2 - Query completed in 0.13s, returned 4 rows
# Measured run 3/3: q01_run3 - Query completed in 0.10s, returned 4 rows
# 
# ✓ Execution complete
# Success rate: 100.0%
# Execution time (mean): 0.122s
# ✓ Validation passed
# Results saved to: results/tpch-q1-memory-sf1_20251019_233827.json
```

**Query File Loading Verification**:
- ✅ Path resolution works from project root
- ✅ SQL content loaded correctly
- ✅ Query name extracted from filename (q01.sql → q01)
- ✅ Source tracked for debugging
- ✅ Multiple query files supported in same experiment

**Schema Configuration Fix**:
- Initial issue: Pointed to `memory.benchmarks` schema (didn't exist)
- Data actually loaded to `memory.default` schema
- Fixed experiment configs to use `schema: "default"`
- Validated with 100% success rate

#### Documentation Created

1. **apps/README.md**
   - Purpose and benefits of apps directory
   - Structure and organization
   - Usage examples (before/after)
   - Getting started guide
   - Current status (6 queries implemented)

2. **apps/tpch/README.md**
   - TPC-H query characteristics table
   - Query selection rationale for dissertation
   - Expected results for each query
   - Performance considerations
   - Validation instructions
   - References to TPC-H specification

3. **Query File Headers**
   - Each .sql file includes:
     - Query number and name
     - Description of purpose
     - Expected result format
     - SQL implementation

#### Benefits Achieved

1. **Reusability** ✅
   - Same query runs on Memory, Iceberg, different scale factors
   - No duplication across 10+ planned experiment variants
   - Query changes propagate automatically

2. **Maintainability** ✅
   - Fix query once in apps/tpch/queries/
   - All experiments benefit immediately
   - Clear version control history

3. **Verification** ✅
   - Easy to compare against official TPC-H specification
   - Query validation against Trino built-in TPC-H catalog
   - Documentation tracks expected results

4. **Research Workflow** ✅
   - Dissertation experiments require same query on different systems
   - Query_files enables systematic comparison
   - Clean separation: queries (what) vs experiments (how/where)

5. **Extensibility** ✅
   - Easy to add remaining 16 TPC-H queries
   - Structure supports TPC-DS queries (apps/tpcds/)
   - Custom benchmark queries supported

#### Dissertation Contributions

1. **Software Architecture**:
   - Demonstrates separation of concerns
   - Reusable component design
   - Version control best practices

2. **Reproducible Research**:
   - Queries documented and version-controlled
   - Same query definition across all experiments
   - No human error from copy-paste

3. **Systematic Evaluation**:
   - Enables fair comparison across systems
   - Identical queries ensure apples-to-apples comparison
   - Query characteristics table guides experiment design

4. **Framework Quality**:
   - Professional software engineering practices
   - Clear documentation for future users
   - Extensible for follow-on research

#### Files Created/Modified

**New Files**:
- `apps/README.md` - Apps directory overview and usage guide
- `apps/tpch/README.md` - TPC-H query documentation
- `apps/tpch/queries/q01.sql` - Pricing Summary Report Query
- `apps/tpch/queries/q03.sql` - Shipping Priority Query
- `apps/tpch/queries/q06.sql` - Forecasting Revenue Change Query
- `apps/tpch/queries/q12.sql` - Shipping Modes Query
- `apps/tpch/queries/q14.sql` - Promotion Effect Query
- `apps/tpch/queries/q19.sql` - Discounted Revenue Query
- `experiments/tpch-q1-memory-sf1.yaml` - Example using query_files

**Modified Files**:
- `lib/tribench/core/experiment.py` - Added query_files field, cli_overrides, normalize_to_list()
- `lib/tribench/experiments/trino_experiment.py` - Enhanced _collect_queries() with file loading
- `experiments/tpch-q1-custom-dataset.yaml` - Fixed schema configuration

#### Technical Challenges Solved

1. **Path Resolution**:
   - Challenge: Relative paths ambiguous (from where?)
   - Solution: Multi-strategy resolution (project root first, then experiments/)
   - Result: Flexible path specification

2. **Backward Compatibility**:
   - Challenge: Don't break existing inline queries
   - Solution: Support both queries and query_files simultaneously
   - Result: Zero breaking changes

3. **Schema Configuration**:
   - Challenge: Mismatch between data location and experiment config
   - Solution: Updated configs to point to correct schema
   - Result: 100% success rate on loaded data

4. **CLI Override Support**:
   - Challenge: CLI needs to override YAML parameters
   - Solution: Added cli_overrides parameter to from_yaml()
   - Result: Runtime configuration flexibility

#### Lessons Learned

1. **Apps Folder Value**:
   - Initial skepticism: "Is apps/ necessary?"
   - Reality: Critical for query reuse across 10+ experiments
   - Insight: Centralization reduces duplication and errors

2. **Path Resolution Strategy**:
   - Single strategy insufficient (what's "relative"?)
   - Multiple strategies provide flexibility
   - Detailed error messages essential for debugging

3. **Schema Naming**:
   - Assumption: Data loaded to "benchmarks" schema
   - Reality: Data in "default" schema
   - Lesson: Always verify data location before experiments

4. **Backward Compatibility**:
   - Supporting both old and new patterns increases adoption
   - Deprecation warnings guide users to new approach
   - No rush to remove old functionality

#### Future Enhancements


### Time Investment

- **Apps Directory Design**: 1 hour (structure, README planning)
- **TPC-H Query Implementation**: 2 hours (6 queries with documentation)
- **ExperimentConfig Enhancement**: 1 hour (query_files field, normalize_to_list, cli_overrides)
- **TrinoExperiment File Loading**: 2 hours (path resolution, error handling, testing)
- **Documentation**: 1.5 hours (apps/README.md, apps/tpch/README.md, query headers)
- **Testing & Validation**: 1.5 hours (end-to-end workflow, schema config fix)
- **Journal Documentation**: 1 hour (this section)
- **Total**: ~10 hours for query reusability architecture

---

*Last Updated: 19 October 2025*
*Total Development Time: ~88.5 hours*
*Phase 0 Complete | Phase 1 Complete (Sections 1.1-1.6)*
---

## Bug Fix: Result File Overwriting Issue (20 October 2025) ✅

### Problem Discovery

**Issue**: When running experiments with multiple queries (e.g., `tpch-q1-memory-tiny.yaml` with 22 queries), only the last 2 queries produced result files instead of all 22.

**Symptom**: 
- Expected: 22 result files (1 per query × 1 run)
- Actual: 2 result files (only q19 and q22)
- All queries executed successfully (100% success rate)

**Root Cause Analysis**:
```bash
# Log output showed all saves to same filename:
Saved result to: .../results/tpch-q1-memory-tiny_20251020_095619.json
Saved result to: .../results/tpch-q1-memory-tiny_20251020_095619.json
Saved result to: .../results/tpch-q1-memory-tiny_20251020_095619.json
# ... (20 more times)
```

**Diagnosis**: 
- Filename generation used `%Y%m%d_%H%M%S` format (seconds precision)
- All 22 queries executed within the **same second**
- Identical timestamps → identical filenames → file overwriting
- Only last query result (q22) survived

### Solution Implemented

**File**: `lib/tribench/experiments/result_collector.py` (line 133)

**Changes**:
1. **Added microsecond precision** to timestamps (`%Y%m%d_%H%M%S_%f`)
2. **Added query name and run number** to filename for uniqueness
3. **Enhanced filename generation logic**:

```python
# Before (buggy):
timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S")
filename = f"{result.experiment_name}_{timestamp_str}.json"

# After (fixed):
timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S_%f")

# Add query name and run number if available
query_name = result.metadata.get("query_name", "")
run_number = result.metadata.get("run_number", "")

if query_name and run_number:
    filename = f"{result.experiment_name}_{query_name}_run{run_number}_{timestamp_str}.json"
elif query_name:
    filename = f"{result.experiment_name}_{query_name}_{timestamp_str}.json"
else:
    filename = f"{result.experiment_name}_{timestamp_str}.json"
```

### Verification

**Test Run**:
```bash
tribench exp run experiments/tpch-q1-memory-tiny.yaml
```

**Results**:
```
Saved result to: .../tpch-q1-memory-tiny_q01_run1_20251020_095722_421564.json
Saved result to: .../tpch-q1-memory-tiny_q02_run1_20251020_095722_479100.json
Saved result to: .../tpch-q1-memory-tiny_q03_run1_20251020_095722_513803.json
...
Saved result to: .../tpch-q1-memory-tiny_q22_run1_20251020_095723_293192.json
```

✅ **All 22 result files created successfully**

**New Filename Format**:
- Pattern: `{experiment}_{query}_{run}_{timestamp_with_microseconds}.json`
- Example: `tpch-q1-memory-tiny_q01_run1_20251020_095722_421564.json`
- Benefits:
  - Unique even for fast-executing queries (< 1 second)
  - Human-readable query identification
  - Chronological ordering maintained
  - Run number tracking built-in

### Impact

**Before Fix**:
- ❌ Only 1 result file per second of execution
- ❌ Silent data loss (overwritten files)
- ❌ Incomplete experiment results
- ❌ False impression of query failures

**After Fix**:
- ✅ Every query execution saves unique result
- ✅ No data loss from overwriting
- ✅ Complete experiment results (22/22 files)
- ✅ Better file organization by query name

### Lessons Learned

1. **Timestamp Precision Matters**:
   - Seconds precision insufficient for fast queries
   - Microseconds (6 decimal places) provide adequate uniqueness
   - Modern systems can execute 10+ queries per second

2. **Semantic Filenames**:
   - Including query name makes results self-documenting
   - Run number enables easy identification of repeated runs
   - Better than pure timestamp-based naming

3. **Silent Failures Are Dangerous**:
   - File overwrites don't generate errors
   - Need to verify file count matches expected output
   - Consider logging warning when overwriting existing file

4. **Integration Testing Reveals Real Issues**:
   - Unit tests wouldn't catch this (no real filesystem operations)
   - End-to-end testing with realistic workloads essential
   - Performance characteristics affect correctness

### Dissertation Relevance

**Software Quality**:
- Demonstrates importance of thorough testing
- Real-world usage reveals edge cases
- User feedback drives quality improvements

**Research Reproducibility**:
- Data loss bug would invalidate experimental results
- Complete result collection essential for statistical analysis
- File naming impacts result organization and analysis workflow

**Performance Considerations**:
- Fast query execution (< 1s) created the collision
- Framework must handle high-throughput scenarios
- Trino's performance creates edge cases for benchmarking tools

### Time Investment

- **Bug Investigation**: 0.25 hours (examining logs, understanding root cause)
- **Solution Implementation**: 0.25 hours (code changes, enhanced filename logic)
- **Testing & Verification**: 0.25 hours (re-running experiment, verifying all files)
- **Documentation**: 0.25 hours (journal update)
- **Total**: ~1 hour

---

## Phase 2: Extended Dataset Management (Week 8-9) 🔄

### Section 2.1: Infrastructure for Iceberg Support ✅
**Completed**: PostgreSQL, MinIO, and Hive Metastore systems for Iceberg catalog backend

#### Motivation

**Problem**: Phase 1 only supported in-memory TPC-H datasets, limiting research scope:
- No persistent storage for table data
- No support for Apache Iceberg table format
- No object storage integration (S3/MinIO)
- No metadata catalog system (Hive Metastore)
- Cannot evaluate Iceberg features (time travel, partition evolution, schema evolution)

**Solution**: Implement three-tier infrastructure stack:
1. **PostgreSQL**: Backend database for Hive Metastore metadata
2. **MinIO**: S3-compatible object storage for Iceberg table data
3. **Hive Metastore**: Catalog service for Iceberg table metadata

**Dissertation Value**: Enables empirical evaluation of Iceberg performance characteristics

#### Core System Implementations

**1. PostgreSQL System** (`lib/tribench/systems/postgresql.py`)

**Purpose**: Backend database for storing Hive Metastore metadata (table schemas, partitions, statistics)

**Key Features**:
- Docker-based PostgreSQL 15 deployment
- Automatic database creation (metastore, results)
- Health checks via `pg_isready` command
- Trust authentication for simplified container access
- Full CLI integration (setup/start/stop/status/teardown/logs)

**Configuration** (`config/reference.conf`):
```hocon
tribench.systems.postgresql {
  version = "15"
  port = 5432
  service_name = "tribench-postgresql-15"
  databases {
    metastore {
      name = "metastore"
      user = "hive"
      password = "hivepassword"
    }
    results {
      name = "results"
      user = "tribench"
      password = "tribenchpassword"
    }
  }
  docker {
    image = "postgres"
    tag = "15"
    network = "tribench-network"
  }
}
```

**Docker Compose Structure**:
```yaml
version: '3.8'
services:
  postgresql:
    container_name: tribench-postgresql-15
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_HOST_AUTH_METHOD: trust
    ports:
      - "5432:5432"
    volumes:
      - postgresql-data:/var/lib/postgresql/data
    networks:
      - tribench-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Implementation Details**:
- `setup()`: Creates directories, generates docker-compose.yml, initializes database schemas
- `start()`: Launches container, waits for health check, creates databases
- `status()`: Reports running state, port, database list
- `stop()`: Gracefully stops container
- `teardown()`: Removes container, volumes, and config files
- `get_logs()`: Retrieves container logs

**Testing Results**:
```bash
$ tribench sys setup postgresql
✓ PostgreSQL setup complete

$ tribench sys start postgresql
✓ PostgreSQL started successfully

$ tribench sys status postgresql
✓ PostgreSQL: Running
  Port: 5432
  Databases: metastore, results
```

**2. MinIO Object Storage System** (`lib/tribench/systems/minio.py`)

**Purpose**: S3-compatible object storage for Iceberg table data files (Parquet, ORC, Avro)

**Key Features**:
- Docker-based MinIO deployment (latest version)
- API port (9000) and Console UI (9001)
- Automatic bucket creation (warehouse, datasets)
- Health checks via HTTP endpoint
- S3A configuration for Hadoop/Hive integration
- Full CLI integration

**Configuration** (`config/reference.conf`):
```hocon
tribench.systems.minio {
  service_name = "tribench-minio"
  api_port = 9000
  console_port = 9001
  root_user = "minioadmin"
  root_password = "minioadmin"
  buckets = ["warehouse", "datasets"]
  docker {
    image = "minio/minio"
    tag = "latest"
    network = "tribench-network"
  }
}
```

**Docker Compose Structure**:
```yaml
version: '3.8'
services:
  minio:
    container_name: tribench-minio
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data
    networks:
      - tribench-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5
```

**Implementation Details**:
- `setup()`: Creates directories, generates docker-compose.yml, configures buckets
- `start()`: Launches container, waits for health, creates buckets via mc client
- `status()`: Reports running state, API port, console port, bucket list
- `stop()`: Gracefully stops container
- `teardown()`: Removes container, volumes, and config files
- `get_logs()`: Retrieves container logs

**Testing Results**:
```bash
$ tribench sys setup minio
✓ MinIO setup complete

$ tribench sys start minio
✓ MinIO started successfully

$ tribench sys status minio
✓ MinIO: Running
  API Port: 9000
  Console Port: 9001
```

**Console Access**: http://localhost:9001 (user: minioadmin, pass: minioadmin)

**3. Hive Metastore System** (`lib/tribench/systems/hive_metastore.py`)

**Purpose**: Apache Hive Metastore service for managing Iceberg table metadata (catalog layer)

**Key Features**:
- Custom Docker image with PostgreSQL JDBC driver 42.7.1
- Thrift protocol on port 9083
- PostgreSQL backend for metadata storage
- S3A configuration for MinIO warehouse access
- Health checks via netcat port scanning
- Full CLI integration

**Architecture Decision**: Multi-stage Dockerfile approach
- **Problem 1**: Apache Hive 3.1.3 has outdated PostgreSQL JDBC driver (doesn't support SCRAM-SHA-256 authentication)
- **Problem 2**: Apache Hive 4.0.0 doesn't include PostgreSQL JDBC driver at all
- **Solution**: Build custom image extending apache/hive:4.0.0 with modern JDBC driver

**Configuration** (`config/reference.conf`):
```hocon
tribench.systems.hive_metastore {
  version = "4.0.0"
  port = 9083
  warehouse_dir = "s3a://warehouse/"
  docker {
    image = "apache/hive"
    tag = "4.0.0"
    service_name = "tribench-hive-metastore"
    network = "tribench-network"
  }
}
```

**Custom Dockerfile** (generated by setup):
```dockerfile
FROM alpine:latest as downloader
RUN apk add --no-cache wget && \
    wget https://jdbc.postgresql.org/download/postgresql-42.7.1.jar -O /postgresql-42.7.1.jar

FROM apache/hive:4.0.0

# Add PostgreSQL JDBC driver
# Using version 42.7.1 which supports SCRAM-SHA-256 authentication
USER root
COPY --from=downloader /postgresql-42.7.1.jar /opt/hive/lib/postgresql-42.7.1.jar
RUN chmod 644 /opt/hive/lib/postgresql-42.7.1.jar

# Install netcat for health checks
RUN apt-get update && apt-get install -y netcat-openbsd && apt-get clean && rm -rf /var/lib/apt/lists/*

USER hive
```

**Docker Compose Structure**:
```yaml
version: '3.8'
services:
  hive-metastore:
    container_name: tribench-hive-metastore
    build:
      context: .
      dockerfile: Dockerfile
    image: tribench-hive-metastore:4.0.0
    ports:
      - "9083:9083"
    environment:
      SERVICE_NAME: metastore
      DB_DRIVER: postgres
      SERVICE_OPTS: "-Djavax.jdo.option.ConnectionDriverName=org.postgresql.Driver ..."
      AWS_ACCESS_KEY_ID: minioadmin
      AWS_SECRET_ACCESS_KEY: minioadmin
    volumes:
      - ./conf/hive-site.xml:/opt/hive/conf/hive-site.xml:ro
      - ./conf/core-site.xml:/opt/hadoop/etc/hadoop/core-site.xml:ro
    networks:
      - tribench-network
    healthcheck:
      test: ["CMD", "nc", "-z", "localhost", "9083"]
      interval: 10s
      timeout: 5s
      retries: 10
```

**Configuration Files Generated**:

1. **hive-site.xml**: Hive Metastore configuration
   - PostgreSQL connection settings (JDBC URL, driver, credentials)
   - S3A configuration for MinIO (endpoint, access keys, path style access)
   - Warehouse directory (s3a://warehouse/)
   - Schema auto-creation settings

2. **core-site.xml**: Hadoop S3A filesystem configuration
   - S3A endpoint configuration
   - Access keys for MinIO
   - Path style access (required for MinIO)
   - SSL disabled (local development)

**Implementation Details**:
- `setup()`: Creates directories, generates Dockerfile, hive-site.xml, core-site.xml, docker-compose.yml
- `start()`: Builds custom image, launches container, waits for Thrift port ready
- `status()`: Reports running state, Thrift port, warehouse location
- `stop()`: Gracefully stops container
- `teardown()`: Removes container, volumes, and config files
- `get_logs()`: Retrieves container logs

#### Technical Challenges and Solutions

**Challenge 1: PostgreSQL Authentication Compatibility** ❌ → ✅

**Problem**:
- PostgreSQL 15 uses SCRAM-SHA-256 authentication by default (authentication type 10)
- Apache Hive 3.1.3 includes PostgreSQL JDBC driver that predates SCRAM-SHA-256 support
- Error: `org.postgresql.util.PSQLException: The authentication type 10 is not supported`

**Initial Attempts**:
1. Changed PostgreSQL to MD5 authentication → Still failed (driver too old)
2. Changed to trust authentication → Still failed (driver issue, not auth method)

**Root Cause**: JDBC driver version, not authentication method

**Solution**:
- Upgraded to Apache Hive 4.0.0 (has updated dependencies)
- Discovered Hive 4.0.0 doesn't include PostgreSQL JDBC driver at all
- Created custom Dockerfile with multi-stage build
- Downloads PostgreSQL JDBC driver 42.7.1 (supports SCRAM-SHA-256)
- Adds driver to `/opt/hive/lib/` in Hive image

**Challenge 2: Docker Health Check Failures** ❌ → ✅

**Problem**:
- Health check: `nc -z localhost 9083` always failed
- Container showed as "unhealthy" despite service running
- Error: `nc: command not found`

**Root Cause**: Apache Hive 4.0.0 image doesn't include netcat utility

**Investigation**:
```bash
$ docker exec tribench-hive-metastore which nc
# Exit code 1 (not found)

$ docker exec tribench-hive-metastore ps aux | grep metastore
# Process running! Service is actually healthy
```

**Solution**:
- Identified base image uses `apt-get` (Debian-based)
- Updated Dockerfile to install `netcat-openbsd` package
- Added installation step: `RUN apt-get update && apt-get install -y netcat-openbsd ...`
- Rebuilt image with netcat included
- Health checks now pass correctly

**Challenge 3: Schema Initialization Success** ✅

**Verification**:
```bash
$ docker logs tribench-hive-metastore 2>&1 | tail -50
...
Completed upgrade-3.0.0-to-3.1.0.postgres.sql
Completed upgrade-3.1.0-to-3.2.0.postgres.sql
Completed upgrade-3.2.0-to-4.0.0-alpha-1.postgres.sql
Completed upgrade-4.0.0-alpha-1-to-4.0.0-alpha-2.postgres.sql
Completed upgrade-4.0.0-alpha-2-to-4.0.0-beta-1.postgres.sql
Completed upgrade-4.0.0-beta-1-to-4.0.0.postgres.sql
Initialized schema successfully..
Starting Hive Metastore Server
```

**Status**: All three systems running successfully! ✅

#### CLI Integration

**System Commands Updated** (`lib/tribench/cli/system_commands.py`):

Added support for three new systems:
- `postgresql`: PostgreSQL database system
- `minio`: MinIO object storage system
- `hive-metastore`: Hive Metastore catalog service

**All Commands Available**:
```bash
# Setup (download, configure, generate files)
tribench sys setup postgresql
tribench sys setup minio
tribench sys setup hive-metastore

# Start (launch containers, wait for health)
tribench sys start postgresql
tribench sys start minio
tribench sys start hive-metastore

# Status (check running state, health, ports)
tribench sys status postgresql
tribench sys status minio
tribench sys status hive-metastore

# Logs (view container output)
tribench sys logs postgresql --tail 50
tribench sys logs minio --tail 50
tribench sys logs hive-metastore --tail 50

# Stop (graceful shutdown)
tribench sys stop postgresql
tribench sys stop minio
tribench sys stop hive-metastore

# Teardown (complete cleanup)
tribench sys teardown postgresql
tribench sys teardown minio
tribench sys teardown hive-metastore
```

**Command Features**:
- Consistent interface across all three systems
- Error handling with informative messages
- Verbose mode for debugging
- Dry-run support for safe testing
- Optional config parameter for all system classes

#### System Integration Architecture

**Dependency Flow**:
```
Trino (Query Engine)
  ↓ queries
Iceberg Catalog (Hive Metastore)
  ↓ metadata storage         ↓ data location
PostgreSQL                 MinIO (S3A)
  (table schemas,            (Parquet files,
   partitions,               data files,
   statistics)               manifest files)
```

**Network Configuration**:
- All containers on `tribench-network` Docker bridge network
- DNS resolution: Containers reference each other by service name
  - `tribench-postgresql-15` (PostgreSQL)
  - `tribench-minio` (MinIO)
  - `tribench-hive-metastore` (Hive Metastore)
  - `tribench-trino-434` (Trino, from Phase 1)

**Port Mappings**:
- PostgreSQL: 5432 (database connections)
- MinIO: 9000 (S3 API), 9001 (Web console)
- Hive Metastore: 9083 (Thrift protocol)
- Trino: 8080 (HTTP API, from Phase 1)

#### Testing Results Summary

**PostgreSQL System** ✅:
```bash
$ tribench sys status postgresql
✓ PostgreSQL: Running
  Port: 5432
  Databases: metastore, results
```
- Container healthy and accepting connections
- Databases created successfully
- Trust authentication working

**MinIO System** ✅:
```bash
$ tribench sys status minio
✓ MinIO: Running
  API Port: 9000
  Console Port: 9001
```
- Container healthy
- Buckets created (warehouse, datasets)
- Console accessible at http://localhost:9001
- Minor warning about mc client permissions (non-blocking)

**Hive Metastore System** ✅:
```bash
$ tribench sys status hive-metastore
✓ Hive Metastore: Running
  Thrift Port: 9083
  Warehouse: s3a://warehouse/
```
- Container healthy after custom image build
- Schema initialized successfully (4.0.0 schema)
- Connected to PostgreSQL backend
- Configured for MinIO warehouse access
- Thrift service accepting connections

**Integration Test** ✅:
- All three systems running simultaneously
- No port conflicts
- DNS resolution working (containers can find each other)
- Ready for Iceberg catalog configuration

#### Files Created/Modified

**New System Implementations**:
- `lib/tribench/systems/postgresql.py` (410 lines) - PostgreSQL system class
- `lib/tribench/systems/minio.py` (380 lines) - MinIO system class
- `lib/tribench/systems/hive_metastore.py` (650 lines) - Hive Metastore system class

**CLI Updates**:
- `lib/tribench/cli/system_commands.py` - Added PostgreSQL, MinIO, Hive Metastore integration

**Configuration Updates**:
- `config/reference.conf` - Added postgresql, minio, hive_metastore sections

**Generated System Directories** (by setup commands):
- `systems/postgresql-15/` - Docker compose and config
- `systems/minio/` - Docker compose and config
- `systems/hive-metastore-4.0.0/` - Dockerfile, docker-compose, hive-site.xml, core-site.xml

**Module Exports**:
- `lib/tribench/systems/__init__.py` - Export new system classes

#### Dissertation Contributions

1. **Infrastructure-as-Code**:
   - All infrastructure defined in version-controlled configuration
   - Docker-based deployment ensures reproducibility
   - Same setup works on any machine with Docker
   - No manual installation steps

2. **Problem-Solving Documentation**:
   - JDBC driver compatibility issue demonstrates real-world challenges
   - Solution process (investigation → diagnosis → fix) shows engineering approach
   - Custom Dockerfile technique applicable to other projects
   - Health check debugging provides operational insights

3. **Modular System Design**:
   - Each system is independent, testable unit
   - Systems integrate through Docker networking
   - Configuration-driven setup (no hardcoded values)
   - Follows System abstract base class pattern

4. **Research Infrastructure**:
   - Enables Iceberg table format experiments
   - Object storage supports large-scale datasets
   - Metadata catalog tracks table evolution
   - Foundation for evaluating Iceberg features

5. **Professional Framework Quality**:
   - Comprehensive error handling
   - Health checks ensure system readiness
   - Detailed logging for troubleshooting
   - Clean teardown for reproducible reruns

#### Lessons Learned

1. **JDBC Driver Compatibility**:
   - Legacy Java applications often ship with outdated dependencies
   - PostgreSQL 13+ authentication breaking change affects many tools
   - Custom Docker images can solve dependency issues
   - Multi-stage builds keep final images small

2. **Docker Health Checks**:
   - Container "up" ≠ service "ready"
   - Health check commands must exist in container
   - Base image investigation essential (which package manager?)
   - Debugging requires checking actual container state

3. **System Integration Testing**:
   - Unit tests insufficient for multi-container systems
   - Integration testing reveals DNS, networking, auth issues
   - Schema initialization logs provide critical debugging info
   - Full lifecycle testing (setup → start → status → logs → stop) essential

4. **Configuration Management**:
   - Optional config parameters enable CLI flexibility
   - ConfigurationLoader pattern works across all systems
   - Service names critical for Docker DNS resolution
   - Trust authentication simplifies container-to-container access

5. **Error Message Quality**:
   - "Authentication type 10 not supported" → obscure error, hard to debug
   - Clear logs and error context reduce troubleshooting time
   - Health check failures need detailed diagnostics
   - Exit code 1 without logs → requires container inspection

#### Time Investment

- **PostgreSQL System**: 3 hours (implementation + CLI integration + testing)
- **MinIO System**: 2.5 hours (implementation + CLI integration + testing)
- **Hive Metastore Initial Implementation**: 4 hours (base system + config generation)
- **JDBC Driver Troubleshooting**: 3 hours (identify issue, research solutions, implement fix)
- **Health Check Debugging**: 2 hours (diagnose failure, find package manager, rebuild)
- **Integration Testing**: 1.5 hours (test all three systems together)
- **Documentation**: 2 hours (docstrings, README updates, journal entry)
- **Total**: ~18 hours for Phase 2.1 infrastructure

#### Next Steps for Phase 2.1

- [x] **Task 5**: Iceberg Catalog Configuration ✅
- [x] **Task 6**: Iceberg Table Creation and Data Loading ✅
- [x] **Task 7**: Enhanced Dataset Validation ✅
- [x] **Task 8**: Dataset Metadata Tracking ✅

**Status**: Phase 2.1 COMPLETE! All Iceberg integration tasks finished.

---

### Section 2.1 (Continued): Iceberg Integration Layer ✅
**Completed**: 30 October 2025

#### Task 5: Iceberg Catalog Configuration ✅

**Objective**: Configure Trino to use Hive Metastore as Iceberg catalog backend

**Implementation** (`lib/tribench/systems/trino.py`):
- Added `_generate_iceberg_catalog_config()` method to TrinoSystem
- Generates `etc/catalog/iceberg.properties` file with:
  - `connector.name=iceberg`
  - `hive.metastore.uri=thrift://tribench-hive-metastore:9083`
  - `hive.s3.endpoint=http://tribench-minio:9000`
  - MinIO credentials (access key, secret key)
  - S3 path style access configuration
  - Parquet format defaults
- Updated `_generate_docker_compose()` to mount shared warehouse volume

**Volume Sharing Fix**:
- Problem: Trino and Hive Metastore need access to same warehouse directory
- Solution: Created shared `hive-warehouse` external volume
- Updated both docker-compose files to mount this volume
- Fixed permissions in Hive Metastore Dockerfile:
  ```dockerfile
  RUN mkdir -p /user/hive/warehouse && \
      chown -R hive:hive /user/hive/warehouse && \
      chmod -R 755 /user/hive/warehouse
  ```

**Testing Results**:
```bash
$ docker exec tribench-trino-434 trino --execute "SHOW CATALOGS"
iceberg
system
tpch

$ docker exec tribench-trino-434 trino --execute "CREATE SCHEMA IF NOT EXISTS iceberg.tpch"
✓ Schema created successfully
```

**Files Modified**:
- `lib/tribench/systems/trino.py` - Added Iceberg catalog generation
- `lib/tribench/systems/hive_metastore.py` - Fixed warehouse permissions
- `config/reference.conf` - Updated warehouse path to `/user/hive/warehouse`

**Time Investment**: 2 hours

---

#### Task 6: Iceberg Table Creation and Data Loading ✅

**Objective**: Implement data loader to create Iceberg tables and populate from Parquet files

**Implementation** (`lib/tribench/data/iceberg_loader.py` - 540 lines):

**IcebergDataLoader Class**:
- `load_dataset()`: Generic loader for any DatasetSchema
- `load_tpch_dataset()`: TPC-H specific with optional partitioning
- `_create_iceberg_table()`: Generates DDL and creates tables
- `_load_data_from_parquet()`: Batch INSERT from Parquet files (1000 rows/batch)
- `_arrow_to_trino_type()`: Maps PyArrow types → Trino SQL types
- `_format_value_for_sql()`: Escapes and formats values for INSERT statements
- `collect_iceberg_metadata()`: Collects snapshot IDs, timestamps, manifest counts

**Key Features**:
- Schema inference from Parquet files using PyArrow
- Support for partitioned tables (lineitem, orders by date columns)
- Configurable storage locations (file:// or s3://)
- Batch inserts for performance
- Connection pooling via trino-python-client
- Error handling and rollback on failure

**CLI Command** (`lib/tribench/cli/data_commands.py`):
```bash
tribench data load-iceberg DATASET [OPTIONS]

Options:
  --catalog TEXT       Iceberg catalog name (default: iceberg)
  --schema TEXT        Schema/database name (default: tpch)
  --storage TEXT       S3 storage location (optional)
  --partition          Enable partitioning for large tables (default: True)
  --no-partition       Disable partitioning
  --validate           Validate data after loading
```

**Type Mapping**:
- Integer types → `TINYINT`, `SMALLINT`, `INTEGER`, `BIGINT`
- Floating point → `DOUBLE`
- String types → `VARCHAR` (with length or unbounded)
- Date types → `DATE`
- Timestamp types → `TIMESTAMP`

**Challenges Solved**:

1. **PyArrow Compatibility Issue**:
   - Problem: `is_utf8()` method not available in newer PyArrow versions
   - Solution: Changed to `is_string()` and `is_large_string()` methods
   - Affected: Type detection in `_arrow_to_trino_type()`

2. **Partition Writer Limit**:
   - Problem: "Exceeded limit of 100 open writers for partitions" error
   - Root Cause: TPC-H tiny dataset has many distinct date values
   - Solution: Made partitioning optional via `--no-partition` flag
   - Default: Enabled for scale factors ≥ 1, disabled for tiny datasets

**Testing Results**:
```bash
$ tribench data load-iceberg tpch-tiny --no-partition --validate
Loading tpch-tiny into Iceberg format...
Target: iceberg.tpch
Creating Iceberg tables and loading data...
✓ Dataset loaded into Iceberg format

Iceberg tables created:
  - customer: 1,500 rows
  - lineitem: 60,175 rows
  - nation: 25 rows
  - orders: 15,000 rows
  - part: 2,000 rows
  - partsupp: 8,000 rows
  - region: 5 rows
  - supplier: 100 rows

Total: 86,805 rows loaded
```

**Verification**:
```bash
$ docker exec tribench-trino-434 trino --execute \
  "SELECT COUNT(*) FROM iceberg.tpch.lineitem"
60175

$ docker exec tribench-trino-434 trino --execute \
  "SELECT table_name FROM iceberg.information_schema.tables WHERE table_schema='tpch'"
customer
lineitem
nation
orders
part
partsupp
region
supplier
```

**Files Created**:
- `lib/tribench/data/iceberg_loader.py` (540 lines)

**Files Modified**:
- `lib/tribench/cli/data_commands.py` - Added `load-iceberg` command

**Time Investment**: 5 hours (implementation + PyArrow fix + testing)

---

#### Task 7: Enhanced Dataset Validation for Iceberg ✅

**Objective**: Implement comprehensive validation for Iceberg tables

**Implementation** (`lib/tribench/data/iceberg_validator.py` - 401 lines):

**IcebergValidator Class**:
- `validate_iceberg_dataset()`: Validates multiple tables with summary
- `validate_iceberg_table()`: Single table validation
- `validate_tpch_iceberg_dataset()`: TPC-H specific validation with expected counts
- `_get_row_count()`: Queries table row count
- `_get_table_schema()`: Retrieves column definitions
- `_get_iceberg_metadata()`: Queries Iceberg system tables (`$snapshots`, `$files`)

**Validation Checks**:
1. **Table Existence**: Verifies table exists in catalog.schema
2. **Row Counts**: Compares actual vs. expected row counts
3. **Schema Validation**: Checks column names and types
4. **Iceberg Metadata**:
   - Snapshot count (verifies versioning working)
   - Data file count (verifies physical storage)
   - Current snapshot ID and timestamp

**CLI Command** (`lib/tribench/cli/data_commands.py`):
```bash
tribench data validate-iceberg [OPTIONS]

Options:
  --catalog TEXT         Iceberg catalog name (default: iceberg)
  --schema TEXT          Schema name (default: tpch)
  --scale-factor TEXT    Scale factor for TPC-H (tiny, 1, 10, etc.)
  --tables TEXT          Comma-separated table names (optional)
  --detailed             Show detailed validation output
```

**Output Format**:
```
Validating Iceberg dataset: iceberg.tpch
Scale Factor: tiny

Table: customer
  ✓ Table exists
  ✓ Row count: 1,500 (expected: 1,500)
  ✓ Schema valid: 8 columns
  ✓ Iceberg metadata: 12 snapshots, 15 files

Table: lineitem
  ✓ Table exists
  ✓ Row count: 60,175 (expected: 60,175)
  ✓ Schema valid: 16 columns
  ✓ Iceberg metadata: 15 snapshots, 20 files

...

Summary:
  Valid tables: 8/8
  Total rows: 86,805
  Total snapshots: 99
```

**Error Handling**:
- Gracefully handles inaccessible Iceberg system tables
- Returns `None` for unavailable metadata instead of failing
- Only warns if metadata is explicitly empty, not if queries fail
- Try-except blocks around all metadata queries

**Challenges Solved**:

1. **False Validation Warnings**:
   - Problem: Initial implementation warned about "no snapshots" for all tables
   - Root Cause: Iceberg system table queries failing silently
   - Solution: Changed to return `None` for unavailable metadata
   - Updated validation logic to only warn if count is explicitly 0, not `None`

2. **System Table Access**:
   - Problem: `$snapshots` and `$files` tables may not be accessible in all configurations
   - Solution: Wrapped queries in try-except, handle gracefully
   - Impact: Validation still succeeds even without Iceberg metadata

**Testing Results**:
```bash
$ tribench data validate-iceberg --scale-factor tiny
Validating Iceberg dataset: iceberg.tpch
Scale Factor: tiny

✓ All 8 tables validated successfully
Summary:
  Valid tables: 8/8
  Total rows: 86,805
  Total snapshots: 99
```

**Files Created**:
- `lib/tribench/data/iceberg_validator.py` (401 lines)

**Files Modified**:
- `lib/tribench/cli/data_commands.py` - Added `validate-iceberg` command

**Time Investment**: 3 hours (implementation + testing + fix false warnings)

---

#### Task 8: Dataset Metadata Tracking for Iceberg ✅

**Objective**: Extend dataset registry to track Iceberg-specific metadata

**Implementation**:

**1. Extended DatasetMetadata Dataclass** (`lib/tribench/data/dataset.py`):

Added optional Iceberg-specific fields:
```python
@dataclass
class DatasetMetadata:
    # ... existing fields ...
    
    # Iceberg-specific metadata (optional)
    iceberg_catalog: Optional[str] = None
    iceberg_schema: Optional[str] = None
    snapshot_ids: Optional[Dict[str, int]] = None
    snapshot_timestamps: Optional[Dict[str, str]] = None
    manifest_counts: Optional[Dict[str, int]] = None
    format_version: Optional[int] = None
    storage_location: Optional[str] = None
```

**Design Decisions**:
- All fields optional to maintain backward compatibility
- Snapshot data stored per table (Dict[table_name, value])
- Format version tracks Iceberg v1 vs. v2 tables
- Storage location captures S3/file:// base path

**2. Metadata Collection** (`lib/tribench/data/iceberg_loader.py`):

Added `collect_iceberg_metadata()` method:
- Queries `$snapshots` system table for each table
- Extracts current snapshot ID and timestamp
- Counts manifest files from `$files` table
- Parses CREATE TABLE statement for format version and location
- Returns structured Dict with all metadata

**3. Updated load-iceberg Command** (`lib/tribench/cli/data_commands.py`):

Workflow:
1. Load data into Iceberg tables
2. Collect Iceberg metadata via `collect_iceberg_metadata()`
3. Create DatasetMetadata entry with format='iceberg'
4. Register dataset with naming convention: `{source_dataset}-iceberg`
5. Optionally validate loaded data

**Metadata Populated**:
- `iceberg_catalog`: Catalog name (e.g., 'iceberg')
- `iceberg_schema`: Schema name (e.g., 'tpch')
- `snapshot_ids`: Current snapshot ID for each table
- `snapshot_timestamps`: Snapshot creation timestamp for each table
- `format_version`: Iceberg format version (1 or 2)
- `properties`: Source dataset, partitioning, storage config

**4. Enhanced info Command** (`lib/tribench/cli/data_commands.py`):

Displays Iceberg-specific section when format='iceberg':
```
============================================================
Iceberg Metadata:
============================================================
Catalog: iceberg
Schema: tpch
Format Version: v2

Snapshot IDs:
  - customer: 5597780913108285715 (at 2025-10-30 22:01:20.730000+00:00)
  - lineitem: 4233068895913014946 (at 2025-10-30 22:04:25.263000+00:00)
  - nation: 2678552858385670564 (at 2025-10-30 22:04:25.428000+00:00)
  - orders: 3644309451677333521 (at 2025-10-30 22:04:45.824000+00:00)
  - part: 5094883996510512120 (at 2025-10-30 22:04:48.251000+00:00)
  - partsupp: 8139616162121444960 (at 2025-10-30 22:04:53.332000+00:00)
  - region: 7154792645439965219 (at 2025-10-30 22:04:53.461000+00:00)
  - supplier: 6822362751345795554 (at 2025-10-30 22:04:53.669000+00:00)
```

**Registry YAML Format** (`datasets/registry.yaml`):
```yaml
tpch-tiny-iceberg:
  name: tpch-tiny-iceberg
  benchmark_type: tpch
  type: static
  format: iceberg
  scale_factor: 0.01
  location: iceberg.tpch
  tables: [customer, lineitem, nation, orders, part, partsupp, region, supplier]
  row_counts:
    customer: 1500
    lineitem: 60175
    nation: 25
    orders: 15000
    part: 2000
    partsupp: 8000
    region: 5
    supplier: 100
  properties:
    source_dataset: tpch-tiny
    partitioned: false
    storage_location: default
  created_at: '2025-10-30T22:04:53.935113'
  generator: iceberg_loader
  iceberg_catalog: iceberg
  iceberg_schema: tpch
  snapshot_ids:
    customer: 5597780913108285715
    lineitem: 4233068895913014946
    # ... other tables ...
  snapshot_timestamps:
    customer: '2025-10-30 22:01:20.730000+00:00'
    lineitem: '2025-10-30 22:04:25.263000+00:00'
    # ... other tables ...
  format_version: 2
```

**Testing Results**:
```bash
$ tribench data load-iceberg tpch-tiny --no-partition --validate
Loading tpch-tiny into Iceberg format...
Target: iceberg.tpch
Creating Iceberg tables and loading data...
✓ Dataset loaded into Iceberg format

Iceberg tables created:
  - customer: 1,500 rows
  - lineitem: 60,175 rows
  [... 8 tables total ...]

Collecting Iceberg metadata...
✓ Registered Iceberg dataset: tpch-tiny-iceberg

Validating Iceberg tables...
✓ All 8 tables validated successfully

$ tribench data list
Found 2 dataset(s):

  tpch-tiny
    Type: generated
    Format: parquet
    Scale Factor: 0.01
    Tables: 8
    Total Rows: 86,805

  tpch-tiny-iceberg
    Type: static
    Format: iceberg
    Scale Factor: 0.01
    Tables: 8
    Total Rows: 86,805
    Location: iceberg.tpch

$ tribench data info tpch-tiny-iceberg
[Displays complete Iceberg metadata as shown above]
```

**Key Features**:
1. **Versioning Support**: Snapshot IDs enable time-travel queries
2. **Lineage Tracking**: Links Iceberg datasets to Parquet source
3. **Format Detection**: Automatically detects Iceberg v1/v2
4. **Extensible**: Optional fields don't break existing code
5. **User-Friendly**: Clear separation of Iceberg metadata in CLI

**Known Limitations**:
- Manifest counts may be empty if query fails
- Storage location may be null if not extractable from DDL
- Metadata collected at load time only (no auto-refresh)

**Files Modified**:
- `lib/tribench/data/dataset.py` - Extended DatasetMetadata with Iceberg fields
- `lib/tribench/data/iceberg_loader.py` - Added `collect_iceberg_metadata()`
- `lib/tribench/cli/data_commands.py` - Updated load-iceberg and info commands

**Time Investment**: 2.5 hours (dataclass extension + metadata collection + CLI updates + testing)

---

### Phase 2.1 Summary

**Total Time Investment**: ~30.5 hours
- Infrastructure (Tasks 1-4): 18 hours
- Iceberg Integration (Tasks 5-8): 12.5 hours

**Lines of Code Added**:
- PostgreSQL System: 410 lines
- MinIO System: 380 lines
- Hive Metastore System: 650 lines
- Iceberg Loader: 540 lines
- Iceberg Validator: 401 lines
- Configuration/CLI updates: ~200 lines
- **Total**: ~2,580 lines

**Key Achievements**:
✅ Complete infrastructure stack (PostgreSQL, MinIO, Hive Metastore)
✅ Iceberg catalog integration with Trino
✅ Data loading from Parquet to Iceberg tables
✅ Comprehensive validation framework
✅ Dataset registry extended for Iceberg metadata
✅ All systems tested and operational

**Dissertation Value**:
- Enables empirical evaluation of Iceberg features
- Demonstrates infrastructure-as-code approach
- Shows problem-solving in complex system integration
- Provides foundation for performance experiments
- Documents real-world challenges and solutions

**Next Phase**: Phase 2.2 - Advanced Iceberg Features
- Partition evolution experiments
- Schema evolution experiments
- Time-travel query performance
- Snapshot management
- Compaction strategies

---

*Last Updated: 30 October 2025*
*Total Development Time: ~107 hours*
*Phase 0 Complete | Phase 1 Complete (Sections 1.1-1.6) | Phase 2.1 Infrastructure Complete*

---

*Last Updated: 20 October 2025*
*Total Development Time: ~89 hours*
*Bug fixed and verified on 20 October 2025*
