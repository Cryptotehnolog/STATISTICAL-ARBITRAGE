"""
Storage layer for the Structured Registry.

This module provides database models, initialization, and migration utilities
for the SQLite-based Structured Registry.

The Structured Registry stores:
- Hypotheses: Trading pair candidates with rationale
- Datasets: OHLCV data with quality metrics
- Statistical Test Results: Cointegration and ADF test results
- Backtest Results: Performance metrics and cost attribution
- Critic Reviews: Validation and objection tracking
- Experiments: Full lifecycle tracking from hypothesis to decision
- Report Artifacts: Links to generated reports

Requirements: 9.1-9.11, 27.14
"""

# Import models
# Import database utilities
from .database import (
    DEFAULT_DB_PATH,
    DatabaseManager,
    create_database_engine,
    create_session_factory,
    get_database_url,
    get_session,
    init_database,
)

# Import migration utilities
from .migrations import (
    DEFAULT_ALEMBIC_DIR,
    MigrationManager,
    create_migration,
    downgrade_database,
    get_alembic_config,
    show_current_revision,
    show_migration_history,
    stamp_database,
    upgrade_database,
)
from .models import (
    BacktestResult,
    Base,
    CriticReview,
    Dataset,
    Experiment,
    Hypothesis,
    ReportArtifact,
    StatisticalTestResult,
)

__all__ = [
    # Models
    "Base",
    "Hypothesis",
    "Dataset",
    "StatisticalTestResult",
    "BacktestResult",
    "CriticReview",
    "Experiment",
    "ReportArtifact",
    # Database utilities
    "DatabaseManager",
    "get_database_url",
    "create_database_engine",
    "init_database",
    "create_session_factory",
    "get_session",
    "DEFAULT_DB_PATH",
    # Migration utilities
    "MigrationManager",
    "get_alembic_config",
    "create_migration",
    "upgrade_database",
    "downgrade_database",
    "show_current_revision",
    "show_migration_history",
    "stamp_database",
    "DEFAULT_ALEMBIC_DIR",
]
