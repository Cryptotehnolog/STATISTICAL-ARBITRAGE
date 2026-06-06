"""Unit tests for chronological validation windows."""

import pytest

from stat_arb.statistical import (
    IndexWindow,
    WalkForwardWindow,
    assert_no_lookahead,
    chronological_train_test_split,
    generate_walk_forward_windows,
)


def test_chronological_train_test_split_uses_explicit_fraction() -> None:
    """Train/test split should preserve chronological order for an explicit fraction."""
    split = chronological_train_test_split(100, train_fraction=0.7)

    assert split.train == IndexWindow(start=0, end=70)
    assert split.test == IndexWindow(start=70, end=100)
    assert split.train.length == 70
    assert split.test.length == 30
    assert split.train.end == split.test.start


def test_chronological_train_test_split_requires_explicit_fraction() -> None:
    """Historical 70/30 planning values should not become runtime defaults."""
    with pytest.raises(TypeError):
        chronological_train_test_split(100)  # type: ignore[call-arg]


def test_chronological_train_test_split_respects_minimum_sizes() -> None:
    """Minimum sizes should prevent empty train/test segments."""
    split = chronological_train_test_split(10, train_fraction=0.95, min_test_size=2)

    assert split.train == IndexWindow(start=0, end=8)
    assert split.test == IndexWindow(start=8, end=10)


def test_generate_walk_forward_windows_rolls_without_lookahead() -> None:
    """Walk-forward folds should move train/test windows forward chronologically."""
    windows = generate_walk_forward_windows(
        120,
        train_size=60,
        test_size=20,
        step_size=20,
        min_folds=3,
    )

    assert windows == (
        WalkForwardWindow(fold=0, train=IndexWindow(0, 60), test=IndexWindow(60, 80)),
        WalkForwardWindow(fold=1, train=IndexWindow(20, 80), test=IndexWindow(80, 100)),
        WalkForwardWindow(fold=2, train=IndexWindow(40, 100), test=IndexWindow(100, 120)),
    )
    assert_no_lookahead(windows)


def test_generate_walk_forward_windows_defaults_step_to_test_size() -> None:
    """Default step should create non-overlapping test windows."""
    windows = generate_walk_forward_windows(50, train_size=20, test_size=10)

    assert [window.test for window in windows] == [
        IndexWindow(20, 30),
        IndexWindow(30, 40),
        IndexWindow(40, 50),
    ]


def test_assert_no_lookahead_rejects_bad_windows() -> None:
    """Lookahead guard should reject malformed manually built folds."""
    with pytest.raises(ValueError, match="empty"):
        assert_no_lookahead(())

    with pytest.raises(ValueError, match="sequential"):
        assert_no_lookahead(
            (
                WalkForwardWindow(fold=1, train=IndexWindow(0, 10), test=IndexWindow(10, 20)),
            )
        )

    with pytest.raises(ValueError, match="overlap"):
        assert_no_lookahead(
            (
                WalkForwardWindow(fold=0, train=IndexWindow(0, 15), test=IndexWindow(10, 20)),
            )
        )

    with pytest.raises(ValueError, match="move forward"):
        assert_no_lookahead(
            (
                WalkForwardWindow(fold=0, train=IndexWindow(0, 10), test=IndexWindow(10, 20)),
                WalkForwardWindow(fold=1, train=IndexWindow(0, 10), test=IndexWindow(10, 20)),
            )
        )


def test_validation_windows_reject_invalid_parameters() -> None:
    """Split helpers should reject invalid sizes and ratios."""
    with pytest.raises(TypeError, match="integer"):
        chronological_train_test_split(10.5, train_fraction=0.7)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="between 0 and 1"):
        chronological_train_test_split(10, train_fraction=1.0)

    with pytest.raises(ValueError, match="minimum"):
        chronological_train_test_split(3, train_fraction=0.7, min_train_size=2, min_test_size=2)

    with pytest.raises(ValueError, match="fit one"):
        generate_walk_forward_windows(10, train_size=8, test_size=3)

    with pytest.raises(ValueError, match="not enough"):
        generate_walk_forward_windows(100, train_size=50, test_size=20, step_size=20, min_folds=3)
