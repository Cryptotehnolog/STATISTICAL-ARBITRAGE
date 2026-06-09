"""Add backtest exit policy and residual diagnostics provenance.

Revision ID: 0002_backtest_and_residual_provenance
Revises: 0001_backtest_reproducibility_manifest
Create Date: 2026-06-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision = "0002_backtest_and_residual_provenance"
down_revision = "0001_backtest_reproducibility_manifest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add provenance fields used by statistical and backtest agents."""
    op.add_column(
        "statistical_test_results",
        sa.Column("residual_ljung_box_p_value", sa.Float(), nullable=True),
    )
    op.add_column(
        "statistical_test_results",
        sa.Column("residual_jarque_bera_p_value", sa.Float(), nullable=True),
    )
    op.add_column(
        "statistical_test_results",
        sa.Column("residual_excess_kurtosis", sa.Float(), nullable=True),
    )
    op.add_column(
        "statistical_test_results",
        sa.Column("residual_diagnostics_lags", sa.Integer(), nullable=True),
    )
    op.add_column("backtest_results", sa.Column("risk_exit_policy", sa.JSON(), nullable=True))
    op.add_column(
        "backtest_results",
        sa.Column("risk_exit_policy_disabled_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove provenance fields."""
    columns: Sequence[tuple[str, str]] = (
        ("backtest_results", "risk_exit_policy_disabled_reason"),
        ("backtest_results", "risk_exit_policy"),
        ("statistical_test_results", "residual_diagnostics_lags"),
        ("statistical_test_results", "residual_excess_kurtosis"),
        ("statistical_test_results", "residual_jarque_bera_p_value"),
        ("statistical_test_results", "residual_ljung_box_p_value"),
    )
    for table_name, column_name in columns:
        op.drop_column(table_name, column_name)
