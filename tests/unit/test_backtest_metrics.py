"""Unit tests for backtest performance metrics."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from stat_arb.backtest import (
    PerformanceMetricConfig,
    calculate_performance_metrics,
    run_pair_backtest_core,
)

README_PATH = Path("README.md")
TASKS_PATH = Path(".kiro/specs/quant-research-architecture/tasks.md")
STAT_VALIDATION_PATH = Path("src/stat_arb/statistical/validation.py")
STATISTICAL_AGENT_PATH = Path("src/stat_arb/agents/statistical_testing.py")
DECISIONS_STATISTICAL_PATH = Path("docs/knowledge/decisions_statistical_testing.md")


def test_performance_metrics_calculate_core_report_values() -> None:
    """Performance metrics should use explicit annualization and risk-free assumptions."""
    core = run_pair_backtest_core(
        prices_a=[100.0, 103.0, 101.0, 100.0, 99.0],
        prices_b=[100.0, 100.0, 100.0, 100.0, 100.0],
        z_scores=[2.2, 1.2, 0.2, -2.1, 0.0],
        aligned_timestamps=_timestamps(5),
        hedge_ratio=1.0,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )
    returns = np.asarray([0.02, -0.01, 0.015, 0.005])
    equity = np.asarray([100.0, 102.0, 100.98, 102.4947, 103.0071735])
    result = calculate_performance_metrics(
        equity_curve=equity,
        period_returns=returns,
        trade_pnls=[5.0, -2.0, 3.0],
        core_result=core,
        config=PerformanceMetricConfig(
            periods_per_year=96 * 365,
            risk_free_rate_per_period=0.0,
            var_confidence=0.95,
            cvar_confidence=0.95,
        ),
    )

    assert result.sharpe_ratio == pytest.approx(
        (returns.mean() / returns.std(ddof=1)) * np.sqrt(96 * 365)
    )
    assert result.sortino_ratio > result.sharpe_ratio
    assert result.volatility == pytest.approx(returns.std(ddof=1) * np.sqrt(96 * 365))
    assert result.max_drawdown == pytest.approx((102.0 - 100.98) / 102.0)
    assert result.win_rate == pytest.approx(2 / 3)
    assert result.profit_factor == pytest.approx(8.0 / 2.0)
    assert result.value_at_risk > 0.0
    assert result.conditional_value_at_risk >= result.value_at_risk
    assert result.holding_times.completed_holds == 1
    assert result.holding_times.average_holding_time_hours == pytest.approx(0.5)
    assert result.exposure.asset_a_short > 0.0
    assert result.exposure.asset_a_long > 0.0


def test_performance_metric_config_requires_explicit_assumptions() -> None:
    """Metric config should not hide annualization or risk-free defaults."""
    with pytest.raises(TypeError):
        PerformanceMetricConfig()  # type: ignore[call-arg]

    with pytest.raises(ValueError, match="periods_per_year"):
        PerformanceMetricConfig(
            periods_per_year=0,
            risk_free_rate_per_period=0.0,
            var_confidence=0.95,
            cvar_confidence=0.95,
        )

    with pytest.raises(ValueError, match="var_confidence"):
        PerformanceMetricConfig(
            periods_per_year=252,
            risk_free_rate_per_period=0.0,
            var_confidence=1.0,
            cvar_confidence=0.95,
        )


def test_performance_metrics_handle_no_trades_without_fake_profitability() -> None:
    """No completed trades should produce neutral trade and holding metrics."""
    core = run_pair_backtest_core(
        prices_a=[100.0, 101.0, 102.0],
        prices_b=[100.0, 100.0, 100.0],
        z_scores=[0.0, 0.1, -0.1],
        aligned_timestamps=_timestamps(3),
        hedge_ratio=1.0,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )
    result = calculate_performance_metrics(
        equity_curve=[100.0, 100.0, 100.0],
        period_returns=[0.0, 0.0],
        trade_pnls=[],
        core_result=core,
        config=PerformanceMetricConfig(
            periods_per_year=365,
            risk_free_rate_per_period=0.0,
            var_confidence=0.95,
            cvar_confidence=0.95,
        ),
    )

    assert result.sharpe_ratio == 0.0
    assert result.sortino_ratio == 0.0
    assert result.volatility == 0.0
    assert result.max_drawdown == 0.0
    assert result.win_rate == 0.0
    assert result.profit_factor == 0.0
    assert result.holding_times.completed_holds == 0


def test_performance_metrics_validate_inputs() -> None:
    """Metric inputs should reject malformed arrays and mismatched core observations."""
    core = run_pair_backtest_core(
        prices_a=[100.0, 101.0, 102.0],
        prices_b=[100.0, 100.0, 100.0],
        z_scores=[0.0, 0.1, -0.1],
        aligned_timestamps=_timestamps(3),
        hedge_ratio=1.0,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )

    with pytest.raises(ValueError, match="positive"):
        calculate_performance_metrics(
            equity_curve=[100.0, 0.0, 101.0],
            period_returns=[0.0, 0.01],
            trade_pnls=[],
            core_result=core,
            config=_metric_config(),
        )

    with pytest.raises(ValueError, match="match equity_curve"):
        calculate_performance_metrics(
            equity_curve=[100.0, 101.0],
            period_returns=[0.01],
            trade_pnls=[],
            core_result=core,
            config=_metric_config(),
        )


def test_old_planning_window_defaults_are_not_exposed_to_runtime_or_readme() -> None:
    """Historical 60/30 and 70/30 planning values should not leak into active contracts."""
    readme = README_PATH.read_text(encoding="utf-8")
    tasks = TASKS_PATH.read_text(encoding="utf-8")
    validation = STAT_VALIDATION_PATH.read_text(encoding="utf-8")
    agent = STATISTICAL_AGENT_PATH.read_text(encoding="utf-8")
    decisions = DECISIONS_STATISTICAL_PATH.read_text(encoding="utf-8")

    assert "--train-window 60" not in readme
    assert "--test-window 30" not in readme
    assert "70/30 default" not in tasks
    assert "train_fraction: float = 0.7" not in validation
    assert "train_fraction: float = 0.7" not in agent
    assert "default train/test is 70/30" not in decisions


def _metric_config() -> PerformanceMetricConfig:
    return PerformanceMetricConfig(
        periods_per_year=365,
        risk_free_rate_per_period=0.0,
        var_confidence=0.95,
        cvar_confidence=0.95,
    )


def _timestamps(count: int) -> tuple[datetime, ...]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return tuple(start + timedelta(minutes=15 * index) for index in range(count))
