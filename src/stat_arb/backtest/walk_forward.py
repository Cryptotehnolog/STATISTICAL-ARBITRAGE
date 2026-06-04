"""Walk-forward validation boundaries for backtests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import numpy as np
from numpy.typing import ArrayLike

from stat_arb.backtest.core import BacktestCoreResult, run_pair_backtest_core
from stat_arb.statistical.validation import (
    WalkForwardWindow,
    assert_no_lookahead,
    generate_walk_forward_windows,
)


@dataclass(frozen=True)
class BacktestWalkForwardConfig:
    """Explicit walk-forward configuration in observation periods.

    The config deliberately has no runtime defaults. Service or CLI layers may translate a
    human-readable plan such as "60 days train, 30 days test" into periods, but this core
    boundary must receive the exact period counts.
    """

    train_size: int
    test_size: int
    step_size: int
    min_folds: int

    def __post_init__(self) -> None:
        """Validate walk-forward period counts."""
        for name, value in {
            "train_size": self.train_size,
            "test_size": self.test_size,
            "step_size": self.step_size,
            "min_folds": self.min_folds,
        }.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class BacktestWalkForwardFold:
    """Backtest core output for one walk-forward test fold."""

    window: WalkForwardWindow
    result: BacktestCoreResult


@dataclass(frozen=True)
class BacktestWalkForwardResult:
    """Collection of chronological walk-forward backtest folds."""

    folds: tuple[BacktestWalkForwardFold, ...]
    config: BacktestWalkForwardConfig
    observations: int

    @property
    def windows(self) -> tuple[WalkForwardWindow, ...]:
        """Return the walk-forward windows used to build the folds."""
        return tuple(fold.window for fold in self.folds)

    @property
    def num_folds(self) -> int:
        """Return number of generated folds."""
        return len(self.folds)


def run_walk_forward_backtest_core(
    *,
    prices_a: ArrayLike,
    prices_b: ArrayLike,
    z_scores: ArrayLike,
    aligned_timestamps: tuple[datetime, ...],
    hedge_ratio: float,
    entry_threshold: float,
    exit_threshold: float,
    config: BacktestWalkForwardConfig,
) -> BacktestWalkForwardResult:
    """Run pure pair backtest core on chronological walk-forward test windows."""
    prices_a_array = np.asarray(prices_a, dtype=float)
    prices_b_array = np.asarray(prices_b, dtype=float)
    z_score_array = np.asarray(z_scores, dtype=float)
    observations = len(aligned_timestamps)
    windows = generate_walk_forward_windows(
        observations,
        train_size=config.train_size,
        test_size=config.test_size,
        step_size=config.step_size,
        min_folds=config.min_folds,
    )
    assert_no_lookahead(windows)

    folds = tuple(
        BacktestWalkForwardFold(
            window=window,
            result=run_pair_backtest_core(
                prices_a=prices_a_array[window.test.start : window.test.end],
                prices_b=prices_b_array[window.test.start : window.test.end],
                z_scores=z_score_array[window.test.start : window.test.end],
                aligned_timestamps=aligned_timestamps[window.test.start : window.test.end],
                hedge_ratio=hedge_ratio,
                entry_threshold=entry_threshold,
                exit_threshold=exit_threshold,
            ),
        )
        for window in windows
    )
    return BacktestWalkForwardResult(folds=folds, config=config, observations=observations)
