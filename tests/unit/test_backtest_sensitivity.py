"""Unit tests for backtest cost sensitivity analysis."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from stat_arb.backtest import (
    BacktestCostConfig,
    CostAssumptionStatus,
    CostSensitivityScenario,
    run_cost_sensitivity_analysis,
    run_pair_backtest_core,
)

TASKS_PATH = Path(".kiro/specs/quant-research-architecture/tasks.md")
SENSITIVITY_PATH = Path("src/stat_arb/backtest/sensitivity.py")


def test_cost_sensitivity_analysis_compares_explicit_cost_multipliers() -> None:
    """2x and 0.5x costs should produce net PnL deltas from the same gross PnL."""
    core = run_pair_backtest_core(
        prices_a=[100.0, 103.0, 101.0, 100.0],
        prices_b=[100.0, 100.0, 100.0, 100.0],
        z_scores=[2.2, 1.2, 0.2, 0.0],
        aligned_timestamps=[
            datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 15, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 30, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 45, tzinfo=UTC),
        ],
        hedge_ratio=1.0,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )

    result = run_cost_sensitivity_analysis(
        core,
        base_cost_config=_verified_cost_config(),
        periods_per_day=96.0,
        average_portfolio_value=10_000.0,
        scenarios=(
            CostSensitivityScenario(name="double_costs", cost_multiplier=2.0),
            CostSensitivityScenario(name="half_costs", cost_multiplier=0.5),
        ),
    )

    double_costs = result.scenarios[0].pnl
    half_costs = result.scenarios[1].pnl
    assert result.base.gross_pnl == pytest.approx(double_costs.gross_pnl)
    assert result.base.gross_pnl == pytest.approx(half_costs.gross_pnl)
    assert double_costs.costs.total_cost == pytest.approx(result.base.costs.total_cost * 2.0)
    assert half_costs.costs.total_cost == pytest.approx(result.base.costs.total_cost * 0.5)
    assert result.scenarios[0].net_pnl_delta == pytest.approx(
        double_costs.net_pnl - result.base.net_pnl
    )
    assert result.scenarios[1].net_pnl_delta > 0.0


def test_cost_sensitivity_requires_explicit_scenarios() -> None:
    """Sensitivity analysis should not hide default 2x/0.5x scenarios."""
    core = run_pair_backtest_core(
        prices_a=[100.0, 101.0],
        prices_b=[100.0, 100.0],
        z_scores=[2.1, 0.0],
        aligned_timestamps=[
            datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 15, tzinfo=UTC),
        ],
        hedge_ratio=1.0,
    )

    with pytest.raises(TypeError):
        run_cost_sensitivity_analysis(  # type: ignore[call-arg]
            core,
            base_cost_config=_verified_cost_config(),
            periods_per_day=96.0,
            average_portfolio_value=10_000.0,
        )

    with pytest.raises(ValueError, match="at least one"):
        run_cost_sensitivity_analysis(
            core,
            base_cost_config=_verified_cost_config(),
            periods_per_day=96.0,
            average_portfolio_value=10_000.0,
            scenarios=(),
        )


def test_cost_sensitivity_validates_scenarios() -> None:
    """Scenario names and multipliers should be explicit and valid."""
    with pytest.raises(ValueError, match="name"):
        CostSensitivityScenario(name="", cost_multiplier=1.0)

    with pytest.raises(ValueError, match="cost_multiplier"):
        CostSensitivityScenario(name="bad", cost_multiplier=-1.0)

    core = run_pair_backtest_core(
        prices_a=[100.0, 101.0],
        prices_b=[100.0, 100.0],
        z_scores=[2.1, 0.0],
        aligned_timestamps=[
            datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 15, tzinfo=UTC),
        ],
        hedge_ratio=1.0,
    )

    with pytest.raises(ValueError, match="unique"):
        run_cost_sensitivity_analysis(
            core,
            base_cost_config=_verified_cost_config(),
            periods_per_day=96.0,
            average_portfolio_value=10_000.0,
            scenarios=(
                CostSensitivityScenario(name="duplicate", cost_multiplier=1.0),
                CostSensitivityScenario(name="duplicate", cost_multiplier=2.0),
            ),
        )


def test_cost_sensitivity_task_is_closed_without_runtime_default_scenarios() -> None:
    """Task 7.8 should be closed without hard-coded default scenario tuples."""
    tasks = TASKS_PATH.read_text(encoding="utf-8")
    implementation = SENSITIVITY_PATH.read_text(encoding="utf-8")

    assert "- [x] 7.8 Implement sensitivity analysis" in tasks
    assert "scenarios: tuple[CostSensitivityScenario, ...]" in implementation
    assert "scenarios=(" not in implementation


def _verified_cost_config() -> BacktestCostConfig:
    return BacktestCostConfig(
        commission_rate=0.001,
        spread_cost_rate=0.0005,
        slippage_rate=0.0002,
        funding_rate_daily=0.0001,
        borrow_rate_annual=0.005,
        status=CostAssumptionStatus.VERIFIED,
        source="unit-test explicit assumptions",
        verified_at=datetime(2024, 1, 1, tzinfo=UTC),
        venue="test-exchange",
        market_type="perpetual",
    )
