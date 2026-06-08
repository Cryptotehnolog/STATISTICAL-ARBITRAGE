# Storage Layer - Structured Registry

This module provides the storage layer for the Structured Registry, which stores all experiment data, metrics, and results.

## Overview

The Structured Registry is a SQLite database that serves as the source of truth for numeric metrics and experiment tracking. It stores:

- **Hypotheses**: Trading pair candidates with rationale and novelty scores
- **Datasets**: OHLCV data with quality metrics and provenance
- **Statistical Test Results**: Cointegration and ADF test results
- **Backtest Results**: Performance metrics and cost attribution
- **Critic Reviews**: Validation results and objections
- **Experiments**: Full lifecycle tracking from hypothesis to decision
- **Report Artifacts**: Links to generated reports

## Quick Start

### Initialize the Database

```python
from stat_arb.storage import init_database

# Initialize with default path (data/registry.db)
engine = init_database()

# Or specify a custom path
from pathlib import Path
engine = init_database(db_path=Path("custom/path/registry.db"))
```

Or use the CLI script:

```bash
# Initialize with default path
uv run python -m stat_arb.scripts.init_database

# Initialize with custom path
uv run python -m stat_arb.scripts.init_database --db-path custom/path/registry.db

# Drop existing tables and recreate (WARNING: deletes all data!)
uv run python -m stat_arb.scripts.init_database --drop-existing
```

### Using the Database Manager

```python
from stat_arb.storage import DatabaseManager, Hypothesis

# Create database manager
db = DatabaseManager()

# Initialize database (creates tables)
db.init_database()

# Use context manager for sessions
with db.session() as session:
    # Create a hypothesis
    hypothesis = Hypothesis(
        asset_a="AAPL",
        asset_b="MSFT",
        rationale="Both are large-cap tech companies",
        source="rule_based",
        novelty_score=0.85,
        created_by="hypothesis_agent",
    )
    session.add(hypothesis)
    session.commit()
    
    # Query hypotheses
    hypotheses = session.query(Hypothesis).filter_by(status="new").all()
    for h in hypotheses:
        print(f"{h.asset_a}/{h.asset_b}: {h.rationale}")

# Close connections when done
db.close()
```

### Using Session Context Manager

```python
from stat_arb.storage import get_session, Hypothesis

# Use context manager for one-off operations
with get_session() as session:
    hypothesis = session.query(Hypothesis).first()
    print(hypothesis.asset_a, hypothesis.asset_b)
```

### Working with Models

```python
from stat_arb.storage import (
    Hypothesis,
    Dataset,
    StatisticalTestResult,
    BacktestResult,
    CriticReview,
    Experiment,
    ReportArtifact,
)

# All models are SQLAlchemy ORM models
# See models.py for full field definitions
```

## Database Schema

### Hypotheses Table

Stores trading pair candidates with rationale and novelty tracking.

**Key Fields:**
- `hypothesis_id` (PK): UUID
- `asset_a`, `asset_b`: Trading pair symbols
- `rationale`: Why this pair might be cointegrated
- `source`: "llm_generated", "rule_based", or "user_provided"
- `novelty_score`: 0.0-1.0, higher = more novel
- `status`: "new", "testing", "rejected", "approved", "quarantined"

### Datasets Table

Stores OHLCV data metadata and quality metrics.

**Key Fields:**
- `dataset_id` (PK): UUID
- `symbol`: Asset symbol
- `source`: Data source (e.g., "ccxt", "alpaca")
- `timeframe`: Bar interval (e.g., "15m", "5m")
- `bar_count`, `missing_bars`, `outlier_count`: Quality metrics
- `quality_score`: 0.0-1.0 overall quality
- `file_path`: Path to Parquet file

### Statistical Test Results Table

Stores cointegration and ADF test results.

**Key Fields:**
- `test_id` (PK): UUID
- `hypothesis_id` (FK): Reference to hypothesis
- `dataset_a_id`, `dataset_b_id` (FK): References to datasets
- `cointegration_statistic`, `cointegration_p_value`: Cointegration test results
- `adf_statistic`, `adf_p_value`: ADF test results
- `hedge_ratio`, `hedge_ratio_r_squared`: Hedge ratio estimation
- `half_life_days`: Mean reversion speed
- `passed`: Boolean pass/fail

### Backtest Results Table

Stores comprehensive backtest results with cost attribution.

**Key Fields:**
- `backtest_id` (PK): UUID
- `hypothesis_id`, `test_id` (FK): References to hypothesis and test
- `git_commit_hash`, `config_hash`: Reproducibility identifiers
- `dataset_ids`, `random_seed`, `execution_command`, `run_timestamp`, `lock_file_hash`: Reproducibility manifest fields
- `execution_time_seconds`: Optional measured runtime for the backtest execution
- `gross_pnl`, `net_pnl`: Performance metrics
- `commission_cost`, `spread_cost`, `slippage_cost`, `funding_cost`, `borrow_cost`: Cost breakdown
- `sharpe_ratio`, `sortino_ratio`, `max_drawdown`: Risk metrics
- `num_trades`, `turnover`: Trade statistics

### Critic Reviews Table

Stores validation results and objections.

**Key Fields:**
- `review_id` (PK): UUID
- `backtest_id` (FK): Reference to backtest
- `lookahead_bias_detected`: Boolean flag
- `overfitting_indicators`, `weak_assumptions`, `cost_concerns`: Lists of issues
- `status`: "approved", "rejected", "quarantined"
- `recommendation`, `objections`: Human-readable summaries

### Experiments Table

Tracks full experiment lifecycle.

**Key Fields:**
- `experiment_id` (PK): UUID
- `hypothesis_id` (FK): Reference to hypothesis
- `status`: Current stage (e.g., "data_validation", "backtesting")
- `data_quality_passed`, `statistical_tests_passed`, `backtest_completed`, `critic_approved`: Stage flags
- `final_decision`: "rejected", "quarantined", "approved", "eligible_for_demo"

### Report Artifacts Table

Stores links to generated reports.

**Key Fields:**
- `artifact_id` (PK): UUID
- `experiment_id` (FK): Reference to experiment
- `artifact_type`: Type of report (e.g., "backtest_report", "equity_curve")
- `file_path`: Path to report file
- `format`: File format (e.g., "html", "pdf", "png")

## Database Migrations

The module supports database migrations using Alembic (though not required for v1 MVP with SQLite).

```python
from stat_arb.storage import MigrationManager

# Create migration manager
migrations = MigrationManager()

# Create a new migration
migrations.create_migration("add_new_field", autogenerate=True)

# Apply migrations
migrations.upgrade()  # Upgrade to latest

# Rollback migrations
migrations.downgrade()  # Downgrade one revision

# Check current revision
migrations.current()

# View migration history
migrations.history()
```

## Requirements

This module implements:
- **Requirement 9.1-9.11**: Structured Registry with all required tables
- **Requirement 27.14**: pyproject.toml for Python project configuration

## Notes

- The database uses SQLite by default for v1 MVP (minimal setup, zero configuration)
- Foreign key constraints are enabled automatically
- All generated timestamps use UTC. The current SQLite schema stores them as naive UTC datetimes for compatibility.
- The database can be upgraded to PostgreSQL for production use without code changes
