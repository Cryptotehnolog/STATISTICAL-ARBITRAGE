"""Unit tests for explicit backtest baseline comparison."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from stat_arb.backtest import (
    BaselineAsset,
    BaselineKind,
    BaselineSide,
    BuyAndHoldBaselineConfig,
    PerformanceMetricConfig,
    RandomSpreadBaselineConfig,
    compare_to_buy_and_hold_baseline,
    compare_to_random_spread_baseline,
)

TASKS_PATH = Path(".kiro/specs/quant-research-architecture/tasks.md")
BASELINE_PATH = Path("src/stat_arb/backtest/baseline.py")
DECISIONS_BACKTESTING_PATH = Path("docs/knowledge/decisions_backtesting.md")


def test_buy_and_hold_baseline_compares_strategy_sharpe_explicitly() -> None:
    """Buy-and-hold baseline should persist its config identity and Sharpe delta."""
    prices_a = np.asarray([100.0, 102.0, 101.0, 104.0])
    strategy_returns = np.asarray([0.03, -0.005, 0.025])
    result = compare_to_buy_and_hold_baseline(
        strategy_period_returns=strategy_returns,
        prices_a=prices_a,
        prices_b=[50.0, 50.5, 51.0, 51.5],
        aligned_timestamps=_timestamps(4),
        baseline_config=BuyAndHoldBaselineConfig(
            name="long_asset_a_one_unit",
            asset=BaselineAsset.ASSET_A,
            side=BaselineSide.LONG,
            units=1.0,
            initial_capital=100.0,
        ),
        metric_config=_metric_config(),
    )

    expected_baseline_returns = np.asarray([0.02, -0.01, 0.03])
    assert result.baseline_name == "long_asset_a_one_unit"
    assert result.baseline_kind == BaselineKind.BUY_AND_HOLD
    assert result.baseline_period_returns == pytest.approx(tuple(expected_baseline_returns))
    assert result.baseline_positions == pytest.approx((1.0, 1.0, 1.0))
    assert result.strategy_sharpe_ratio == pytest.approx(_sharpe(strategy_returns))
    assert result.baseline_sharpe_ratio == pytest.approx(_sharpe(expected_baseline_returns))
    assert result.sharpe_delta == pytest.approx(result.strategy_sharpe_ratio - result.baseline_sharpe_ratio)


def test_short_buy_and_hold_baseline_uses_explicit_side_and_asset() -> None:
    """Short single-asset baselines should invert selected asset returns."""
    result = compare_to_buy_and_hold_baseline(
        strategy_period_returns=[0.0, 0.0],
        prices_a=[100.0, 101.0, 102.0],
        prices_b=[50.0, 49.0, 47.0],
        aligned_timestamps=_timestamps(3),
        baseline_config=BuyAndHoldBaselineConfig(
            name="short_asset_b_two_units",
            asset=BaselineAsset.ASSET_B,
            side=BaselineSide.SHORT,
            units=2.0,
            initial_capital=100.0,
        ),
        metric_config=_metric_config(),
    )

    assert result.baseline_period_returns == pytest.approx((0.02, 0.04))
    assert result.baseline_positions == pytest.approx((-2.0, -2.0))


def test_random_spread_baseline_is_reproducible_with_explicit_seed() -> None:
    """Random baseline should be deterministic only because the seed is explicit."""
    config = RandomSpreadBaselineConfig(
        name="seeded_random_spread",
        hedge_ratio=1.0,
        seed=123,
        entry_probability=0.75,
        initial_capital=100.0,
    )
    kwargs = {
        "strategy_period_returns": [0.01, 0.02, -0.01],
        "prices_a": [100.0, 102.0, 101.0, 103.0],
        "prices_b": [50.0, 51.0, 51.5, 52.0],
        "aligned_timestamps": _timestamps(4),
        "baseline_config": config,
        "metric_config": _metric_config(),
    }

    first = compare_to_random_spread_baseline(**kwargs)
    second = compare_to_random_spread_baseline(**kwargs)

    assert first.baseline_kind == BaselineKind.RANDOM_SPREAD_ENTRY
    assert first.baseline_positions == second.baseline_positions
    assert first.baseline_period_returns == pytest.approx(second.baseline_period_returns)


def test_baseline_configs_require_explicit_research_assumptions() -> None:
    """Baseline configs should not hide asset, side, seed, probability, or capital defaults."""
    with pytest.raises(TypeError):
        BuyAndHoldBaselineConfig()  # type: ignore[call-arg]

    with pytest.raises(TypeError):
        RandomSpreadBaselineConfig()  # type: ignore[call-arg]

    with pytest.raises(ValueError, match="initial_capital"):
        BuyAndHoldBaselineConfig(
            name="bad",
            asset=BaselineAsset.ASSET_A,
            side=BaselineSide.LONG,
            units=1.0,
            initial_capital=0.0,
        )

    with pytest.raises(TypeError, match="seed"):
        RandomSpreadBaselineConfig(
            name="bad",
            hedge_ratio=1.0,
            seed=True,  # type: ignore[arg-type]
            entry_probability=0.5,
            initial_capital=100.0,
        )

    with pytest.raises(ValueError, match="entry_probability"):
        RandomSpreadBaselineConfig(
            name="bad",
            hedge_ratio=1.0,
            seed=7,
            entry_probability=1.1,
            initial_capital=100.0,
        )


def test_baseline_comparison_validates_aligned_inputs_and_return_counts() -> None:
    """Baseline comparison should fail on unaligned or mismatched inputs."""
    config = BuyAndHoldBaselineConfig(
        name="long_a",
        asset=BaselineAsset.ASSET_A,
        side=BaselineSide.LONG,
        units=1.0,
        initial_capital=100.0,
    )

    with pytest.raises(ValueError, match="strictly increasing"):
        compare_to_buy_and_hold_baseline(
            strategy_period_returns=[0.0, 0.0],
            prices_a=[100.0, 101.0, 102.0],
            prices_b=[50.0, 51.0, 52.0],
            aligned_timestamps=(
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 1, tzinfo=UTC),
                datetime(2024, 1, 1, 0, 15, tzinfo=UTC),
            ),
            baseline_config=config,
            metric_config=_metric_config(),
        )

    with pytest.raises(ValueError, match="match baseline period count"):
        compare_to_buy_and_hold_baseline(
            strategy_period_returns=[0.0],
            prices_a=[100.0, 101.0, 102.0],
            prices_b=[50.0, 51.0, 52.0],
            aligned_timestamps=_timestamps(3),
            baseline_config=config,
            metric_config=_metric_config(),
        )


def test_baseline_task_is_closed_without_hidden_baseline_defaults() -> None:
    """Task 7.9 should be closed and baseline configs should avoid hidden defaults."""
    tasks = TASKS_PATH.read_text(encoding="utf-8")
    implementation = BASELINE_PATH.read_text(encoding="utf-8")
    decisions = DECISIONS_BACKTESTING_PATH.read_text(encoding="utf-8")

    assert "- [x] 7.9 Implement baseline comparison" in tasks
    assert "DEC-0045" in decisions
    forbidden_default_patterns = (
        "asset: BaselineAsset =",
        "side: BaselineSide =",
        "units: float =",
        "initial_capital: float =",
        "seed: int =",
        "entry_probability: float =",
        "hedge_ratio: float =",
    )
    for pattern in forbidden_default_patterns:
        assert pattern not in implementation


def _metric_config() -> PerformanceMetricConfig:
    return PerformanceMetricConfig(
        periods_per_year=365,
        risk_free_rate_per_period=0.0,
        var_confidence=0.95,
        cvar_confidence=0.95,
    )


def _sharpe(returns: np.ndarray) -> float:
    return float((returns.mean() / returns.std(ddof=1)) * np.sqrt(365))


def _timestamps(count: int) -> tuple[datetime, ...]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return tuple(start + timedelta(minutes=15 * index) for index in range(count))
