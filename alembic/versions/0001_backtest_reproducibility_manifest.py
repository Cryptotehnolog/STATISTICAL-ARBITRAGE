"""Add backtest reproducibility manifest fields.

Revision ID: 0001_backtest_reproducibility_manifest
Revises:
Create Date: 2026-06-09
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision = "0001_backtest_reproducibility_manifest"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add reproducibility manifest columns to backtest results."""
    op.add_column("backtest_results", sa.Column("dataset_ids", sa.JSON(), nullable=True))
    op.add_column("backtest_results", sa.Column("random_seed", sa.Integer(), nullable=True))
    op.add_column("backtest_results", sa.Column("execution_command", sa.JSON(), nullable=True))
    op.add_column("backtest_results", sa.Column("run_timestamp", sa.DateTime(), nullable=True))
    op.add_column("backtest_results", sa.Column("lock_file_hash", sa.String(length=64), nullable=True))
    op.add_column(
        "backtest_results",
        sa.Column("execution_time_seconds", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Remove reproducibility manifest columns from backtest results."""
    columns: Sequence[str] = (
        "execution_time_seconds",
        "lock_file_hash",
        "run_timestamp",
        "execution_command",
        "random_seed",
        "dataset_ids",
    )
    for column in columns:
        op.drop_column("backtest_results", column)
