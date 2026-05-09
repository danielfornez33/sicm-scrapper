# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-05-09

### 🚀 Added
- **Core**: Complete rewrite using Scrapling framework (4.2x faster than v1)
- **Spider**: Pause/resume automatic with checkpoints
- **Database**: Asyncpg connection pool optimized (min=5, max=20)
- **Validation**: Pydantic models with automatic outlier filtering
- **CLI**: Full command-line interface with arguments (`--start-id`, `--end-id`, `--dry-run`, etc.)
- **Docker**: Multi-stage Dockerfile optimized (~170MB)
- **CI/CD**: GitHub Actions workflows (CI + CD)
- **Tests**: Basic unit tests for parser and models
- **Documentation**: Complete documentation (8 files)

### ✅ Fixed
- Batch not saving (now uses atomic transactions)
- Memory leak from accumulated tasks (now uses generator pattern)
- Duplicate records (now uses ON CONFLICT DO NOTHING)
- Progress negative ETA calculation (now correct)
- No validation of data (now Pydantic validates all)
- Outliers not filtered (>1M units now rejected)

### ⚡ Performance
- 125 req/s (vs 30 in v1) - 4.2x faster
- ~150MB RAM (vs ~800MB) - 5.3x less
- Bulk insert 0.8s (vs 8s) - 10x faster

### 📚 Documentation
- START_HERE.md - Quick start guide
- SETUP_RÁPIDO.md - 5-minute setup
- README.md - Complete documentation
- DEPLOYMENT.md - VPS deployment guide
- OPTIMIZATION_GUIDE.md - Performance tuning
- SUMMARY.md - Changes vs v1
- ESTRUCTURA_PROYECTO.md - Project structure
- CONTRIBUTING.md - Contribution guide

## [1.0.0] - 2025-01-01 (Original version)

### ⚠️ Deprecated
- **This version is no longer supported.**
- Please upgrade to v2.0.0 for better performance and reliability.

---

## Migration Guide (v1 to v2)

### Configuration
```env
# v1: Hardcoded
DB_HOST=localhost
START_ID=42022341

# v2: Environment variables
# Create .env from .env.example
```

### Running
```bash
# v1: python src/scraper.py

# v2: 
python src/main.py           # Basic
python -m src.cli --help    # With CLI
docker-compose up -d         # Docker
```

### Features
- v1: No pause/resume
- v2: Automatic checkpoint saving

- v1: Manual duplicate handling
- v2: Automatic ON CONFLICT

- v1: No data validation
- v2: Pydantic validation + outlier filtering