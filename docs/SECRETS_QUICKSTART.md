# Quick Start: Secrets Management

This guide helps you quickly set up secrets management for TriBench.

## 🚀 30-Second Setup

```bash
# 1. Copy the template
cp .env.example .env

# 2. Edit passwords (use your favorite editor)
nano .env   # or vim, vscode, etc.

# 3. That's it! TriBench automatically loads .env on startup
./bin/tribench.sh sys status
```

## 📋 What You Need to Change

At minimum, update these passwords in `.env`:

```bash
# PostgreSQL (for Hive Metastore)
POSTGRES_PASSWORD=your_secure_password_here

# MinIO (for object storage)
MINIO_ROOT_PASSWORD=your_admin_password
MINIO_SECRET_KEY=your_secret_key_here
```

## 🔐 Security Checklist

- ✅ `.env` is already in `.gitignore` (won't be committed)
- ✅ Use strong, random passwords (32+ characters recommended)
- ✅ Set file permissions: `chmod 600 .env`
- ✅ Never share your `.env` file
- ✅ Use `.env.example` as template only (no real secrets)

## 📚 Need More Help?

- **Full Documentation**: [docs/SECRETS_MANAGEMENT.md](docs/SECRETS_MANAGEMENT.md)
- **All Variables**: See `.env.example` with descriptions
- **Troubleshooting**: Check the docs for common issues

## 🎯 Quick Examples

### Development (Local Docker)
```bash
# Keep defaults from .env.example
cp .env.example .env
# Just change passwords for security
```

### Production (Remote Services)
```bash
# Point to remote hosts
POSTGRES_HOST=db.prod.example.com
POSTGRES_PASSWORD=<from_vault>

MINIO_HOST=s3.prod.example.com
MINIO_ACCESS_KEY=<from_vault>

TRINO_HOST=trino.prod.example.com
```

### Testing Different Credentials
```bash
# Temporarily override without editing .env
POSTGRES_PASSWORD=test123 ./bin/tribench.sh sys start postgresql
```

## 🔄 How It Works

**Configuration Precedence** (highest to lowest):
1. **System Environment Variables** (shell export)
2. **`.env` File** (this file)
3. **HOCON Config Files** (reference.conf)

Example:
- If you set `export POSTGRES_PASSWORD=from_shell`
- And `.env` has `POSTGRES_PASSWORD=from_file`
- **Shell wins**: Uses `from_shell`

## 🆘 Common Issues

### "Connection refused" errors?
Check services are running:
```bash
./bin/tribench.sh sys status
```

### Environment not loading?
Restart the framework:
```bash
./bin/tribench.sh sys stop trino
./bin/tribench.sh sys start trino
```

### Want to reset everything?
```bash
rm .env
cp .env.example .env
# Edit passwords again
```

---

**First time using TriBench?** Start with the main [README.md](README.md) for a complete introduction.
