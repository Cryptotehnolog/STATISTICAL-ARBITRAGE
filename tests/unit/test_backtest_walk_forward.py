"""Unit tests for walk-forward backtest boundaries."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from stat_arb.backtest import BacktestWalkForwardConfig, run_walk_forward_backtest_core
from stat_arb.statistical import IndexWindow, WalkForwardWindow, assert_no_lookahead

TASKS_PATH = Path(".kiro/specs/quant-research-architecture/tasks.md")
WALK_FORWARD_PATH = Path("src/stat_arb/backtest/walk_forward.py")


def test_walk_forward_backtest_runs_only_on_test_windows() -> None:
    """Backtest folds should use chronological test slices and no lookahead."""
    result = run_walk_forward_backtest_core(
        prices_a=[100.0 + index for index in range(14)],
        prices_b=[100.0 for _ in range(14)],
        z_scores=[0.0, 0.0, 0.0, 2.1, 0.0, 0.0, 0.0, -2.2, 0.0, 0.0, 2.5, 0.0, 0.0, 0.0],
        aligned_timestamps=_timestamps(14),
        hedge_ratio=1.0,
        entry_threshold=2.0,
        exit_threshold=0.5,
        config=BacktestWalkForwardConfig(train_size=4, test_size=2, step_size=2, min_folds=3),
    )

    assert result.num_folds == 5
    assert result.windows[:3] == (
        WalkForwardWindow(fold=0, train=IndexWindow(0, 4), test=IndexWindow(4, 6)),
        WalkForwardWindow(fold=1, train=IndexWindow(2, 6), test=IndexWindow(6, 8)),
        WalkForwardWindow(fold=2, train=IndexWindow(4, 8), test=IndexWindow(8, 10)),
    )
    assert_no_lookahead(result.windows)
    assert result.folds[0].result.steps[0].timestamp == _timestamps(14)[4]
    assert result.folds[0].result.steps[-1].timestamp == _timestamps(14)[5]


def test_walk_forward_config_requires_explicit_period_counts() -> None:
    """Backtest walk-forward config should not hide planning defaults."""
    with pytest.raises(TypeError):
        BacktestWalkForwardConfig()  # type: ignore[call-arg]

    with pytest.raises(ValueError, match="train_size"):
        BacktestWalkForwardConfig(train_size=0, test_size=2, step_size=2, min_folds=1)


def test_walk_forward_backtest_requires_minimum_fold_count() -> None:
    """Backtest walk-forward should enforce configured minimum folds."""
    with pytest.raises(ValueError, match="not enough"):
        run_walk_forward_backtest_core(
            prices_a=[100.0 + index for index in range(10)],
            prices_b=[100.0 for _ in range(10)],
            z_scores=[0.0 for _ in range(10)],
            aligned_timestamps=_timestamps(10),
            hedge_ratio=1.0,
            entry_threshold=2.0,
            exit_threshold=0.5,
            config=BacktestWalkForwardConfig(train_size=6, test_size=2, step_size=2, min_folds=3),
        )


def test_walk_forward_backtest_does_not_expose_kiro_planning_windows_as_defaults() -> None:
    """Historical 60/30 day planning values should not become runtime defaults."""
    tasks = TASKS_PATH.read_text(encoding="utf-8")
    implementation = WALK_FORWARD_PATH.read_text(encoding="utf-8")

    assert "60 days train, 30 days test" not in tasks
    assert "train_size: int = 60" not in implementation
    assert "test_size: int = 30" not in implementation


def _timestamps(count: int) -> tuple[datetime, ...]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return tuple(start + timedelta(minutes=15 * index) for index in range(count))
