"""Backtest engine core for pair-trading signal and position construction."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import numpy as np
from numpy.typing import ArrayLike


class SpreadPosition(StrEnum):
    """Pair spread position state."""

    FLAT = "flat"
    LONG_SPREAD = "long_spread"
    SHORT_SPREAD = "short_spread"


class BacktestAction(StrEnum):
    """Position transition emitted by the backtest core."""

    HOLD = "hold"
    ENTER_LONG_SPREAD = "enter_long_spread"
    ENTER_SHORT_SPREAD = "enter_short_spread"
    EXIT = "exit"


@dataclass(frozen=True)
class BacktestStep:
    """One aligned pair-trading position step."""

    index: int
    timestamp: datetime
    price_a: float
    price_b: float
    z_score: float
    position: SpreadPosition
    position_a: float
    position_b: float
    action: BacktestAction


@dataclass(frozen=True)
class BacktestCoreResult:
    """Pure backtest core output before PnL and cost attribution."""

    steps: tuple[BacktestStep, ...]
    hedge_ratio: float
    entry_threshold: float
    exit_threshold: float

    @property
    def observations(self) -> int:
        """Return number of aligned observations processed."""
        return len(self.steps)

    @property
    def trades(self) -> tuple[BacktestStep, ...]:
        """Return entry and exit transition steps."""
        return tuple(step for step in self.steps if step.action != BacktestAction.HOLD)


def run_pair_backtest_core(
    *,
    prices_a: ArrayLike,
    prices_b: ArrayLike,
    z_scores: ArrayLike,
    aligned_timestamps: Sequence[datetime],
    hedge_ratio: float,
    entry_threshold: float = 2.0,
    exit_threshold: float = 0.5,
) -> BacktestCoreResult:
    """Build deterministic pair-trading positions from aligned prices and z-scores.

    Positive z-scores indicate an expensive spread: short asset A and long
    `hedge_ratio` units of asset B. Negative z-scores indicate a cheap spread: long asset A
    and short `hedge_ratio` units of asset B.
    """
    prices_a_array = _as_1d_finite_array(prices_a, name="prices_a")
    prices_b_array = _as_1d_finite_array(prices_b, name="prices_b")
    z_score_array = _as_1d_array(z_scores, name="z_scores")
    timestamps = tuple(aligned_timestamps)
    _validate_core_inputs(
        prices_a=prices_a_array,
        prices_b=prices_b_array,
        z_scores=z_score_array,
        aligned_timestamps=timestamps,
        hedge_ratio=hedge_ratio,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
    )

    position = SpreadPosition.FLAT
    steps: list[BacktestStep] = []
    for index, (timestamp, price_a, price_b, z_score) in enumerate(
        zip(timestamps, prices_a_array, prices_b_array, z_score_array)
    ):
        action = BacktestAction.HOLD
        if np.isfinite(z_score):
            if position == SpreadPosition.FLAT:
                if z_score >= entry_threshold:
                    position = SpreadPosition.SHORT_SPREAD
                    action = BacktestAction.ENTER_SHORT_SPREAD
                elif z_score <= -entry_threshold:
                    position = SpreadPosition.LONG_SPREAD
                    action = BacktestAction.ENTER_LONG_SPREAD
            elif abs(float(z_score)) <= exit_threshold:
                position = SpreadPosition.FLAT
                action = BacktestAction.EXIT

        position_a, position_b = _position_weights(position, hedge_ratio=hedge_ratio)
        steps.append(
            BacktestStep(
                index=index,
                timestamp=timestamp,
                price_a=float(price_a),
                price_b=float(price_b),
                z_score=float(z_score),
                position=position,
                position_a=position_a,
                position_b=position_b,
                action=action,
            )
        )

    return BacktestCoreResult(
        steps=tuple(steps),
        hedge_ratio=float(hedge_ratio),
        entry_threshold=float(entry_threshold),
        exit_threshold=float(exit_threshold),
    )


def _position_weights(position: SpreadPosition, *, hedge_ratio: float) -> tuple[float, float]:
    if position == SpreadPosition.LONG_SPREAD:
        return 1.0, -float(hedge_ratio)
    if position == SpreadPosition.SHORT_SPREAD:
        return -1.0, float(hedge_ratio)
    return 0.0, 0.0


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = _as_1d_array(values, name=name)
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _as_1d_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    return array


def _validate_core_inputs(
    *,
    prices_a: np.ndarray,
    prices_b: np.ndarray,
    z_scores: np.ndarray,
    aligned_timestamps: Sequence[datetime],
    hedge_ratio: float,
    entry_threshold: float,
    exit_threshold: float,
) -> None:
    if prices_a.shape != prices_b.shape or prices_a.shape != z_scores.shape:
        raise ValueError("prices_a, prices_b, and z_scores must have the same length")
    if prices_a.size < 2:
        raise ValueError("backtest core requires at least 2 observations")
    if np.any(prices_a <= 0.0) or np.any(prices_b <= 0.0):
        raise ValueError("prices_a and prices_b must be positive")
    if np.any(np.isinf(z_scores)):
        raise ValueError("z_scores may contain NaN warm-up values but not infinity")
    if len(aligned_timestamps) != prices_a.size:
        raise ValueError("aligned_timestamps must match price series length")
    if any(
        aligned_timestamps[index] >= aligned_timestamps[index + 1]
        for index in range(len(aligned_timestamps) - 1)
    ):
        raise ValueError("aligned_timestamps must be strictly increasing")
    if not np.isfinite(hedge_ratio) or hedge_ratio <= 0.0:
        raise ValueError("hedge_ratio must be finite and positive")
    if not np.isfinite(entry_threshold) or entry_threshold <= 0.0:
        raise ValueError("entry_threshold must be finite and positive")
    if not np.isfinite(exit_threshold) or exit_threshold < 0.0:
        raise ValueError("exit_threshold must be finite and non-negative")
    if exit_threshold >= entry_threshold:
        raise ValueError("exit_threshold must be lower than entry_threshold")
