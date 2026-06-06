"""Explicit baseline comparisons for pair backtests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import numpy as np
from numpy.typing import ArrayLike

from stat_arb.backtest.metrics import PerformanceMetricConfig


class BaselineKind(StrEnum):
    """Supported baseline strategy families."""

    BUY_AND_HOLD = "buy_and_hold"
    RANDOM_SPREAD_ENTRY = "random_spread_entry"


class BaselineAsset(StrEnum):
    """Asset selected for single-leg baselines."""

    ASSET_A = "asset_a"
    ASSET_B = "asset_b"


class BaselineSide(StrEnum):
    """Side selected for single-leg baselines."""

    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class BuyAndHoldBaselineConfig:
    """Explicit buy-and-hold baseline assumptions."""

    name: str
    asset: BaselineAsset
    side: BaselineSide
    units: float
    initial_capital: float

    def __post_init__(self) -> None:
        """Validate explicit buy-and-hold assumptions."""
        _validate_name(self.name)
        if self.asset not in {BaselineAsset.ASSET_A, BaselineAsset.ASSET_B}:
            raise ValueError("asset must be asset_a or asset_b")
        if self.side not in {BaselineSide.LONG, BaselineSide.SHORT}:
            raise ValueError("side must be long or short")
        _validate_positive(self.units, name="units")
        _validate_positive(self.initial_capital, name="initial_capital")


@dataclass(frozen=True)
class RandomSpreadBaselineConfig:
    """Explicit random spread-entry baseline assumptions."""

    name: str
    hedge_ratio: float
    seed: int
    entry_probability: float
    initial_capital: float

    def __post_init__(self) -> None:
        """Validate explicit random baseline assumptions."""
        _validate_name(self.name)
        _validate_positive(self.hedge_ratio, name="hedge_ratio")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise TypeError("seed must be an integer")
        if not np.isfinite(self.entry_probability) or not 0.0 <= self.entry_probability <= 1.0:
            raise ValueError("entry_probability must be between 0 and 1")
        _validate_positive(self.initial_capital, name="initial_capital")


@dataclass(frozen=True)
class BaselineComparisonResult:
    """Sharpe comparison between strategy and one explicit baseline."""

    baseline_name: str
    baseline_kind: BaselineKind
    strategy_sharpe_ratio: float
    baseline_sharpe_ratio: float
    sharpe_delta: float
    baseline_period_returns: tuple[float, ...]
    baseline_positions: tuple[float, ...]


def compare_to_buy_and_hold_baseline(
    *,
    strategy_period_returns: ArrayLike,
    prices_a: ArrayLike,
    prices_b: ArrayLike,
    aligned_timestamps: Sequence[datetime],
    baseline_config: BuyAndHoldBaselineConfig,
    metric_config: PerformanceMetricConfig,
) -> BaselineComparisonResult:
    """Compare strategy returns with an explicit buy-and-hold baseline."""
    prices_a_array, prices_b_array, timestamps = _validate_price_inputs(
        prices_a=prices_a,
        prices_b=prices_b,
        aligned_timestamps=aligned_timestamps,
    )
    selected_prices = prices_a_array if baseline_config.asset == BaselineAsset.ASSET_A else prices_b_array
    side_multiplier = 1.0 if baseline_config.side == BaselineSide.LONG else -1.0
    period_pnl = side_multiplier * baseline_config.units * np.diff(selected_prices)
    baseline_returns = period_pnl / baseline_config.initial_capital
    positions = tuple(
        side_multiplier * baseline_config.units for _ in range(len(timestamps) - 1)
    )

    return _comparison_result(
        strategy_period_returns=strategy_period_returns,
        baseline_returns=baseline_returns,
        baseline_positions=positions,
        baseline_name=baseline_config.name,
        baseline_kind=BaselineKind.BUY_AND_HOLD,
        metric_config=metric_config,
    )


def compare_to_random_spread_baseline(
    *,
    strategy_period_returns: ArrayLike,
    prices_a: ArrayLike,
    prices_b: ArrayLike,
    aligned_timestamps: Sequence[datetime],
    baseline_config: RandomSpreadBaselineConfig,
    metric_config: PerformanceMetricConfig,
) -> BaselineComparisonResult:
    """Compare strategy returns with an explicit seeded random spread baseline."""
    prices_a_array, prices_b_array, timestamps = _validate_price_inputs(
        prices_a=prices_a,
        prices_b=prices_b,
        aligned_timestamps=aligned_timestamps,
    )
    rng = np.random.default_rng(baseline_config.seed)
    position_probability = baseline_config.entry_probability
    positions = rng.choice(
        np.asarray([-1.0, 0.0, 1.0], dtype=float),
        size=len(timestamps) - 1,
        p=np.asarray(
            [position_probability / 2.0, 1.0 - position_probability, position_probability / 2.0],
            dtype=float,
        ),
    )
    spread_changes = np.diff(prices_a_array) - baseline_config.hedge_ratio * np.diff(prices_b_array)
    baseline_returns = positions * spread_changes / baseline_config.initial_capital

    return _comparison_result(
        strategy_period_returns=strategy_period_returns,
        baseline_returns=baseline_returns,
        baseline_positions=tuple(float(position) for position in positions),
        baseline_name=baseline_config.name,
        baseline_kind=BaselineKind.RANDOM_SPREAD_ENTRY,
        metric_config=metric_config,
    )


def _comparison_result(
    *,
    strategy_period_returns: ArrayLike,
    baseline_returns: np.ndarray,
    baseline_positions: tuple[float, ...],
    baseline_name: str,
    baseline_kind: BaselineKind,
    metric_config: PerformanceMetricConfig,
) -> BaselineComparisonResult:
    strategy_returns = _as_1d_finite_array(strategy_period_returns, name="strategy_period_returns")
    if strategy_returns.shape != baseline_returns.shape:
        raise ValueError("strategy_period_returns must match baseline period count")
    strategy_sharpe = _sharpe_ratio(strategy_returns, config=metric_config)
    baseline_sharpe = _sharpe_ratio(baseline_returns, config=metric_config)
    return BaselineComparisonResult(
        baseline_name=baseline_name,
        baseline_kind=baseline_kind,
        strategy_sharpe_ratio=strategy_sharpe,
        baseline_sharpe_ratio=baseline_sharpe,
        sharpe_delta=float(strategy_sharpe - baseline_sharpe),
        baseline_period_returns=tuple(float(value) for value in baseline_returns),
        baseline_positions=baseline_positions,
    )


def _validate_price_inputs(
    *,
    prices_a: ArrayLike,
    prices_b: ArrayLike,
    aligned_timestamps: Sequence[datetime],
) -> tuple[np.ndarray, np.ndarray, tuple[datetime, ...]]:
    prices_a_array = _as_1d_finite_array(prices_a, name="prices_a")
    prices_b_array = _as_1d_finite_array(prices_b, name="prices_b")
    timestamps = tuple(aligned_timestamps)
    if prices_a_array.shape != prices_b_array.shape:
        raise ValueError("prices_a and prices_b must have the same length")
    if prices_a_array.size < 2:
        raise ValueError("baseline comparison requires at least 2 observations")
    if np.any(prices_a_array <= 0.0) or np.any(prices_b_array <= 0.0):
        raise ValueError("prices_a and prices_b must be positive")
    if len(timestamps) != prices_a_array.size:
        raise ValueError("aligned_timestamps must match price series length")
    if any(timestamps[index] >= timestamps[index + 1] for index in range(len(timestamps) - 1)):
        raise ValueError("aligned_timestamps must be strictly increasing")
    return prices_a_array, prices_b_array, timestamps


def _sharpe_ratio(returns: np.ndarray, *, config: PerformanceMetricConfig) -> float:
    excess_returns = returns - config.risk_free_rate_per_period
    std = float(np.std(excess_returns, ddof=1)) if excess_returns.size > 1 else 0.0
    if std == 0.0:
        return 0.0
    return float((np.mean(excess_returns) / std) * np.sqrt(config.periods_per_year))


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _validate_name(name: str) -> None:
    if not name.strip():
        raise ValueError("name is required")


def _validate_positive(value: float, *, name: str) -> None:
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
