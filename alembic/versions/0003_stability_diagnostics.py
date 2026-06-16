"""Add rolling stability diagnostics to statistical test results.

Revision ID: 0003_stability_diagnostics
Revises: 0002_backtest_and_residual_provenance
Create Date: 2026-06-16
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0003_stability_diagnostics"
down_revision = "0002_backtest_and_residual_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable diagnostics so legacy rows do not receive fake stability evidence."""
    columns: Sequence[sa.Column] = (
        sa.Column("stability_window", sa.Integer(), nullable=True),
        sa.Column("stability_step", sa.Integer(), nullable=True),
        sa.Column("stability_window_count", sa.Integer(), nullable=True),
        sa.Column("hedge_ratio_stability_std", sa.Float(), nullable=True),
        sa.Column("hedge_ratio_stability_max_abs_change", sa.Float(), nullable=True),
        sa.Column("cointegration_stability_pass_ratio", sa.Float(), nullable=True),
    )
    for column in columns:
        op.add_column("statistical_test_results", column)


def downgrade() -> None:
    """Remove rolling stability diagnostics."""
    for column_name in (
        "cointegration_stability_pass_ratio",
        "hedge_ratio_stability_max_abs_change",
        "hedge_ratio_stability_std",
        "stability_window_count",
        "stability_step",
        "stability_window",
    ):
        op.drop_column("statistical_test_results", column_name)
