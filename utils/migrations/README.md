# Database Migrations

This directory contains database migration scripts for the TriBench framework.

## Available Migrations

### 001_add_advanced_query_metrics.py

Adds high and medium priority metrics to the `query_executions` table:

**New Columns:**
- `spilled_bytes` (BIGINT) - Memory spill metrics
- `total_splits` (INTEGER) - Total query splits
- `completed_splits` (INTEGER) - Completed splits
- `total_tasks` (INTEGER) - Total tasks from stage aggregation
- `query_plan_hash` (VARCHAR(64)) - SHA256 hash of query plan

**Usage:**
```bash
# Run with default database (SQLite)
python utils/migrations/001_add_advanced_query_metrics.py

# Run with custom database URL
TRIBENCH_DATABASE_URL=postgresql://user:pass@host/db python utils/migrations/001_add_advanced_query_metrics.py
```

**Features:**
- Idempotent: Safe to run multiple times
- Supports SQLite and PostgreSQL
- Checks for existing columns before adding
- Detailed logging

## Running Migrations

1. **Backup your database** (recommended)
2. Run the migration script
3. Verify new columns exist
4. Test with a sample experiment

## Creating New Migrations

Follow this naming convention:
```
<number>_<descriptive_name>.py
```

Example: `002_add_environment_metadata.py`

## Migration Best Practices

1. **Make migrations reversible** when possible
2. **Test on a copy** of production database first
3. **Document the changes** in the script docstring
4. **Handle both SQLite and PostgreSQL** syntax differences
5. **Check for existing schema** before making changes
6. **Use transactions** for multiple operations

## Troubleshooting

### Column already exists
The migration will skip existing columns and log a message.

### Database not found
Ensure `init_database()` has been run at least once to create the base schema.

### Permission errors
Check database file/directory permissions (SQLite) or user permissions (PostgreSQL).
