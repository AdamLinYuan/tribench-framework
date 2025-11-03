# Secrets Management Guide

## Overview

TriBench uses environment variables and `.env` files for secure management of sensitive configuration data such as database passwords, API tokens, and cloud credentials. This approach follows security best practices and ensures secrets are never committed to version control.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Configuration Precedence](#configuration-precedence)
3. [Environment Variables Reference](#environment-variables-reference)
4. [Setup Instructions](#setup-instructions)
5. [Best Practices](#best-practices)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Usage](#advanced-usage)

---

## Quick Start

### 1. Create Your `.env` File

Copy the example template and customize it for your environment:

```bash
cp .env.example .env
```

### 2. Edit Sensitive Values

Open `.env` and update the passwords and credentials:

```bash
# Example: Change default PostgreSQL password
POSTGRES_PASSWORD=your_secure_password_here

# Example: Set MinIO credentials
MINIO_ROOT_USER=your_admin_user
MINIO_ROOT_PASSWORD=your_secure_password
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
```

### 3. Verify Configuration

Run a system status check to ensure environment variables are loaded:

```bash
./bin/tribench.sh sys status
```

The framework automatically loads `.env` on startup.

---

## Configuration Precedence

TriBench uses a **hierarchical configuration system** with the following precedence (highest to lowest):

1. **System Environment Variables** (highest priority)
   - Set via `export VAR=value` in shell
   - Persists for current shell session
   - Overrides all other sources

2. **`.env` File in Project Root**
   - Loaded automatically on framework startup
   - Does NOT override existing environment variables
   - Safe default for development

3. **HOCON Configuration Files** (lowest priority)
   - `config/reference.conf` - framework defaults
   - `config/hosts/{hostname}/application.conf` - host-specific overrides
   - `experiments/*.yaml` - experiment-specific settings

### Example Precedence

Given:
- `.env` file: `POSTGRES_PASSWORD=from_dotenv`
- Shell: `export POSTGRES_PASSWORD=from_shell`
- HOCON: `password = "from_config"`

**Result**: `from_shell` is used (system environment wins)

If only `.env` and HOCON exist:
**Result**: `from_dotenv` is used (environment wins over config)

---

## Environment Variables Reference

### PostgreSQL (Hive Metastore Backend)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `hive` | Database username |
| `POSTGRES_PASSWORD` | `hive_password` | Database password |
| `POSTGRES_DB` | `metastore` | Database name |
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |

### MinIO (Object Storage)

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ROOT_USER` | `admin` | Admin username |
| `MINIO_ROOT_PASSWORD` | `password` | Admin password |
| `MINIO_ACCESS_KEY` | `minioadmin` | S3 access key |
| `MINIO_SECRET_KEY` | `minioadmin` | S3 secret key |
| `MINIO_HOST` | `localhost` | MinIO host |
| `MINIO_PORT` | `9000` | MinIO API port |
| `MINIO_CONSOLE_PORT` | `9001` | MinIO console port |
| `MINIO_BUCKET` | `warehouse` | Default bucket |
| `MINIO_REGION` | `us-east-1` | AWS region |

### Trino

| Variable | Default | Description |
|----------|---------|-------------|
| `TRINO_USER` | `admin` | Trino username |
| `TRINO_PASSWORD` | *(empty)* | Trino password (if auth enabled) |
| `TRINO_HOST` | `localhost` | Trino coordinator host |
| `TRINO_PORT` | `8080` | Trino coordinator port |
| `TRINO_CATALOG` | `iceberg` | Default catalog |
| `TRINO_SCHEMA` | `default` | Default schema |

### Hive Metastore

| Variable | Default | Description |
|----------|---------|-------------|
| `HIVE_METASTORE_HOST` | `localhost` | Metastore host |
| `HIVE_METASTORE_PORT` | `9083` | Metastore port |
| `HIVE_METASTORE_WAREHOUSE` | `s3a://warehouse/` | Warehouse location |

### Results Database

| Variable | Default | Description |
|----------|---------|-------------|
| `RESULTS_DB_USER` | `tribench` | Results DB username |
| `RESULTS_DB_PASSWORD` | *(empty)* | Results DB password |
| `RESULTS_DB_HOST` | `localhost` | Results DB host |
| `RESULTS_DB_PORT` | `5432` | Results DB port |
| `RESULTS_DB_NAME` | `tribench_results` | Results DB name |
| `RESULTS_DB_ENABLED` | `false` | Enable results storage |

### Framework Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_DIR` | `log` | Log directory |
| `RESULTS_DIR` | `results` | Results directory |
| `DEBUG` | `false` | Enable debug mode |
| `DRY_RUN` | `false` | Simulate operations |

---

## Setup Instructions

### Local Development Setup

1. **Copy the template**:
   ```bash
   cp .env.example .env
   ```

2. **Edit for local development**:
   ```bash
   # Keep defaults for local Docker deployment
   POSTGRES_USER=hive
   POSTGRES_PASSWORD=dev_password_123
   
   MINIO_ROOT_USER=admin
   MINIO_ROOT_PASSWORD=admin_password_123
   MINIO_ACCESS_KEY=minioadmin
   MINIO_SECRET_KEY=minioadmin_secret_123
   ```

3. **Start services**:
   ```bash
   ./bin/tribench.sh sys setup trino
   ./bin/tribench.sh sys setup postgresql
   ./bin/tribench.sh sys setup minio
   ./bin/tribench.sh sys start postgresql
   ./bin/tribench.sh sys start minio
   ./bin/tribench.sh sys start trino
   ```

### Production/School Cluster Setup

For remote or production deployments:

1. **Create environment-specific `.env`**:
   ```bash
   # Point to remote services
   POSTGRES_HOST=db.example.com
   POSTGRES_PORT=5432
   POSTGRES_USER=tribench_prod
   POSTGRES_PASSWORD=<strong_password_from_vault>
   
   MINIO_HOST=s3.example.com
   MINIO_ACCESS_KEY=<access_key_from_vault>
   MINIO_SECRET_KEY=<secret_key_from_vault>
   
   TRINO_HOST=trino-coordinator.example.com
   TRINO_PORT=8080
   TRINO_USER=tribench_prod
   TRINO_PASSWORD=<strong_password_from_vault>
   ```

2. **Secure the `.env` file**:
   ```bash
   chmod 600 .env
   ```

3. **Verify connectivity**:
   ```bash
   ./bin/tribench.sh sys status
   ```

### CI/CD Setup

For GitHub Actions or other CI/CD:

1. **Store secrets in CI/CD platform**:
   - GitHub: Repository Settings → Secrets and variables → Actions
   - GitLab: Settings → CI/CD → Variables
   - Jenkins: Credentials management

2. **Set environment variables in CI job**:
   ```yaml
   # GitHub Actions example
   jobs:
     test:
       steps:
         - name: Set environment variables
           env:
             POSTGRES_USER: ${{ secrets.POSTGRES_USER }}
             POSTGRES_PASSWORD: ${{ secrets.POSTGRES_PASSWORD }}
             MINIO_ACCESS_KEY: ${{ secrets.MINIO_ACCESS_KEY }}
             MINIO_SECRET_KEY: ${{ secrets.MINIO_SECRET_KEY }}
   ```

3. **DO NOT create `.env` in CI**:
   - Use native CI/CD secrets management
   - Never commit `.env` files to repository

---

## Best Practices

### Security

1. **Never Commit Secrets**
   - ✅ `.env` is in `.gitignore` by default
   - ✅ Always use `.env.example` as template (no real secrets)
   - ❌ Never commit actual passwords or keys to Git

2. **Use Strong Passwords**
   - Generate random passwords: `openssl rand -base64 32`
   - Use password managers (1Password, LastPass, Bitwarden)
   - Rotate passwords regularly (quarterly for production)

3. **Restrict File Permissions**
   ```bash
   chmod 600 .env          # Owner read/write only
   chmod 644 .env.example  # Everyone can read template
   ```

4. **Separate Environments**
   - Use different `.env` files for dev, staging, prod
   - Example: `.env.dev`, `.env.staging`, `.env.prod`
   - Load appropriate file: `cp .env.prod .env`

5. **Use Secrets Management Tools** (for production)
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Kubernetes Secrets

### Development Workflow

1. **Onboarding New Developers**
   ```bash
   # Developer clones repo
   git clone <repo-url>
   cd tribench-framework
   
   # Copy and customize environment
   cp .env.example .env
   # Edit .env with local passwords
   
   # Verify setup
   ./bin/tribench.sh sys status
   ```

2. **Sharing Configuration** (without secrets)
   - Share `config/reference.conf` (safe, no secrets)
   - Share `experiments/*.yaml` (safe, no secrets)
   - Share `.env.example` (safe, template only)
   - DO NOT share `.env` (contains real secrets)

3. **Testing with Different Credentials**
   ```bash
   # Temporarily override for testing
   POSTGRES_PASSWORD=test123 ./bin/tribench.sh sys start postgresql
   ```

### Configuration Management

1. **Document Required Variables**
   - Keep `.env.example` up-to-date
   - Add comments for each variable
   - Specify valid value ranges

2. **Validate Configuration**
   ```python
   # Framework automatically validates on startup
   from tribench.utils.config import ConfigurationLoader
   
   loader = ConfigurationLoader()
   config = loader.load()
   errors = loader.validate(config)
   if errors:
       print("Configuration errors:", errors)
   ```

3. **Use Defaults Wisely**
   - Development: Convenient defaults in `.env.example`
   - Production: Force explicit configuration (no defaults for passwords)

---

## Troubleshooting

### Problem: Environment variables not loading

**Symptoms**:
- Framework uses default passwords instead of `.env` values
- Connection errors to databases

**Solution**:
1. Verify `.env` file exists in project root:
   ```bash
   ls -la .env
   ```

2. Check file contents:
   ```bash
   cat .env | grep POSTGRES_PASSWORD
   ```

3. Ensure no syntax errors (no spaces around `=`):
   ```bash
   # ✅ Correct
   POSTGRES_PASSWORD=mypassword
   
   # ❌ Wrong (spaces)
   POSTGRES_PASSWORD = mypassword
   ```

4. Restart framework (reload environment):
   ```bash
   ./bin/tribench.sh sys stop trino
   ./bin/tribench.sh sys start trino
   ```

### Problem: System environment overrides `.env`

**Symptoms**:
- `.env` file has correct values
- Framework uses different values

**Solution**:
System environment variables have higher priority. Check:
```bash
echo $POSTGRES_PASSWORD
```

If set, either:
- Unset system variable: `unset POSTGRES_PASSWORD`
- Or update system variable: `export POSTGRES_PASSWORD=new_value`

### Problem: Permission denied errors

**Symptoms**:
```
PermissionError: [Errno 13] Permission denied: '.env'
```

**Solution**:
```bash
# Fix file permissions
chmod 600 .env

# Ensure owner can read
ls -la .env
# Should show: -rw------- 1 user group ... .env
```

### Problem: Connection refused errors

**Symptoms**:
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**Solution**:
1. Verify services are running:
   ```bash
   ./bin/tribench.sh sys status
   ```

2. Check correct host/port in `.env`:
   ```bash
   grep POSTGRES_HOST .env
   grep POSTGRES_PORT .env
   ```

3. Test connection manually:
   ```bash
   psql -h localhost -p 5432 -U hive -d metastore
   ```

### Problem: Variables not resolving in HOCON

**Symptoms**:
- Configuration shows `${?VAR_NAME}` instead of value

**Solution**:
1. Verify environment variable is set:
   ```bash
   echo $VAR_NAME
   ```

2. Check HOCON syntax (should have default):
   ```hocon
   # ✅ Correct (with default)
   password = ${?POSTGRES_PASSWORD}"default_password"
   
   # ❌ Wrong (no default, will fail if not set)
   password = ${?POSTGRES_PASSWORD}
   ```

3. Reload configuration:
   ```python
   from tribench.utils.config import ConfigurationLoader
   loader = ConfigurationLoader()
   config = loader.load()
   print(config.get("tribench.systems.postgresql.password"))
   ```

---

## Advanced Usage

### Multiple Environments

Manage multiple `.env` files for different environments:

```bash
# Create environment-specific files
.env.dev           # Development settings
.env.staging       # Staging settings
.env.prod          # Production settings

# Activate specific environment
ln -sf .env.dev .env       # Use development
ln -sf .env.staging .env   # Use staging
ln -sf .env.prod .env      # Use production
```

### Docker Compose Integration

TriBench automatically passes environment variables to Docker Compose:

```yaml
# systems/postgresql/docker-compose.yml (auto-generated)
services:
  postgresql:
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
```

### Programmatic Access

Access environment variables in custom code:

```python
from tribench.utils.config import ConfigurationLoader, get_config_or_env

# Load configuration with .env support
loader = ConfigurationLoader()
config = loader.load()

# Get value with fallback precedence: config → env → default
password = get_config_or_env(
    config,
    "tribench.systems.postgresql.password",
    "POSTGRES_PASSWORD",
    default="fallback_password"
)

# Direct environment access
db_host = loader.get_env("POSTGRES_HOST", default="localhost")
```

### Custom Validation

Validate environment variables on startup:

```python
import os
from tribench.utils.config import ConfigurationLoader

loader = ConfigurationLoader()

# Check required secrets are set
required_secrets = [
    "POSTGRES_PASSWORD",
    "MINIO_SECRET_KEY",
]

missing = [var for var in required_secrets if not os.getenv(var)]
if missing:
    raise ValueError(f"Missing required environment variables: {missing}")
```

### Integration with External Secrets Managers

#### AWS Secrets Manager

```python
import boto3
from tribench.utils.config import ConfigurationLoader

def load_aws_secrets():
    """Load secrets from AWS Secrets Manager."""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='tribench/prod')
    secrets = json.loads(response['SecretString'])
    
    # Set as environment variables
    for key, value in secrets.items():
        os.environ[key] = value

# Load secrets before initializing framework
load_aws_secrets()
loader = ConfigurationLoader()
config = loader.load()
```

#### HashiCorp Vault

```python
import hvac
from tribench.utils.config import ConfigurationLoader

def load_vault_secrets():
    """Load secrets from HashiCorp Vault."""
    client = hvac.Client(url='https://vault.example.com:8200')
    client.auth.approle.login(
        role_id=os.getenv('VAULT_ROLE_ID'),
        secret_id=os.getenv('VAULT_SECRET_ID')
    )
    
    secrets = client.secrets.kv.v2.read_secret_version(
        path='tribench/prod'
    )['data']['data']
    
    for key, value in secrets.items():
        os.environ[key] = value

load_vault_secrets()
loader = ConfigurationLoader()
config = loader.load()
```

---

## Summary

TriBench's secrets management provides:

✅ **Security**: Secrets never committed to Git  
✅ **Flexibility**: Environment-specific configuration  
✅ **Simplicity**: Single `.env` file for development  
✅ **Compatibility**: Works with CI/CD and secrets managers  
✅ **Precedence**: Clear hierarchy (system env → .env → config)  

For questions or issues, consult the [troubleshooting section](#troubleshooting) or file an issue on GitHub.
