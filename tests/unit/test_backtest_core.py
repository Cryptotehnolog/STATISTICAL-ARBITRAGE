"""Unit tests for pair backtest signal and position construction."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from stat_arb.backtest import BacktestAction, SpreadPosition, run_pair_backtest_core


def test_pair_backtest_core_enters_and_exits_short_spread() -> None:
    """Positive z-score entry should short asset A and long hedge-ratio asset B."""
    result = run_pair_backtest_core(
        prices_a=[101.0, 103.0, 102.0, 100.5, 100.0],
        prices_b=[100.0, 100.0, 100.0, 100.0, 100.0],
        z_scores=[np.nan, 2.2, 1.4, 0.4, -0.2],
        aligned_timestamps=_timestamps(5),
        hedge_ratio=1.5,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )

    assert result.observations == 5
    assert [step.action for step in result.trades] == [
        BacktestAction.ENTER_SHORT_SPREAD,
        BacktestAction.EXIT,
    ]
    entry = result.steps[1]
    assert entry.position == SpreadPosition.SHORT_SPREAD
    assert entry.position_a == -1.0
    assert entry.position_b == pytest.approx(1.5)
    assert result.steps[2].position == SpreadPosition.SHORT_SPREAD
    assert result.steps[3].position == SpreadPosition.FLAT


def test_pair_backtest_core_enters_and_exits_long_spread() -> None:
    """Negative z-score entry should long asset A and short hedge-ratio asset B."""
    result = run_pair_backtest_core(
        prices_a=[98.0, 97.0, 98.5, 99.0],
        prices_b=[100.0, 100.0, 100.0, 100.0],
        z_scores=[-2.1, -1.0, -0.25, 1.0],
        aligned_timestamps=_timestamps(4),
        hedge_ratio=0.8,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )

    entry = result.steps[0]
    assert entry.action == BacktestAction.ENTER_LONG_SPREAD
    assert entry.position == SpreadPosition.LONG_SPREAD
    assert entry.position_a == 1.0
    assert entry.position_b == pytest.approx(-0.8)
    assert result.steps[2].action == BacktestAction.EXIT
    assert result.steps[2].position == SpreadPosition.FLAT


def test_pair_backtest_core_ignores_undefined_zscore_until_signal_exists() -> None:
    """Rolling-window NaN z-scores should not create phantom entries."""
    result = run_pair_backtest_core(
        prices_a=[100.0, 101.0, 102.0],
        prices_b=[100.0, 100.0, 100.0],
        z_scores=[np.nan, np.nan, 2.5],
        aligned_timestamps=_timestamps(3),
        hedge_ratio=1.0,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )

    assert result.steps[0].position == SpreadPosition.FLAT
    assert result.steps[1].position == SpreadPosition.FLAT
    assert result.steps[2].action == BacktestAction.ENTER_SHORT_SPREAD


def test_pair_backtest_core_validates_aligned_inputs() -> None:
    """Core must reject unaligned shapes and non-chronological timestamps."""
    with pytest.raises(ValueError, match="same length"):
        run_pair_backtest_core(
            prices_a=[100.0, 101.0],
            prices_b=[100.0],
            z_scores=[0.0, 1.0],
            aligned_timestamps=_timestamps(2),
            hedge_ratio=1.0,
            entry_threshold=2.0,
            exit_threshold=0.5,
        )

    timestamps = list(_timestamps(3))
    timestamps[2] = timestamps[1]
    with pytest.raises(ValueError, match="strictly increasing"):
        run_pair_backtest_core(
            prices_a=[100.0, 101.0, 102.0],
            prices_b=[100.0, 100.0, 100.0],
            z_scores=[0.0, 1.0, 2.0],
            aligned_timestamps=timestamps,
            hedge_ratio=1.0,
            entry_threshold=2.0,
            exit_threshold=0.5,
        )


def test_pair_backtest_core_validates_thresholds_and_hedge_ratio() -> None:
    """Invalid trading parameters should fail before positions are emitted."""
    with pytest.raises(ValueError, match="hedge_ratio"):
        run_pair_backtest_core(
            prices_a=[100.0, 101.0],
            prices_b=[100.0, 100.0],
            z_scores=[0.0, 1.0],
            aligned_timestamps=_timestamps(2),
            hedge_ratio=0.0,
            entry_threshold=2.0,
            exit_threshold=0.5,
        )

    with pytest.raises(ValueError, match="exit_threshold"):
        run_pair_backtest_core(
            prices_a=[100.0, 101.0],
            prices_b=[100.0, 100.0],
            z_scores=[0.0, 1.0],
            aligned_timestamps=_timestamps(2),
            hedge_ratio=1.0,
            entry_threshold=1.0,
            exit_threshold=1.0,
        )

    with pytest.raises(ValueError, match="not infinity"):
        run_pair_backtest_core(
            prices_a=[100.0, 101.0],
            prices_b=[100.0, 100.0],
            z_scores=[0.0, np.inf],
            aligned_timestamps=_timestamps(2),
            hedge_ratio=1.0,
            entry_threshold=2.0,
            exit_threshold=0.5,
        )


def test_pair_backtest_core_requires_explicit_thresholds() -> None:
    """Trading thresholds are research assumptions and must be passed explicitly."""
    implementation = Path("src/stat_arb/backtest/core.py").read_text(encoding="utf-8")

    assert "entry_threshold: float = " not in implementation
    assert "exit_threshold: float = " not in implementation


def _timestamps(count: int) -> tuple[datetime, ...]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return tuple(start + timedelta(minutes=15 * index) for index in range(count))
