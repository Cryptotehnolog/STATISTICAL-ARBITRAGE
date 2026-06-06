"""Train/test and walk-forward validation windows."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IndexWindow:
    """Half-open index interval."""

    start: int
    end: int

    @property
    def length(self) -> int:
        """Number of observations in the interval."""
        return self.end - self.start


@dataclass(frozen=True)
class TrainTestSplit:
    """Chronological train/test split."""

    train: IndexWindow
    test: IndexWindow
    observations: int
    train_fraction: float


@dataclass(frozen=True)
class WalkForwardWindow:
    """One chronological walk-forward validation fold."""

    fold: int
    train: IndexWindow
    test: IndexWindow


def chronological_train_test_split(
    observations: int,
    *,
    train_fraction: float,
    min_train_size: int = 1,
    min_test_size: int = 1,
) -> TrainTestSplit:
    """Create a chronological train/test split without shuffling."""
    _validate_observation_count(observations)
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be between 0 and 1")
    if min_train_size < 1:
        raise ValueError("min_train_size must be positive")
    if min_test_size < 1:
        raise ValueError("min_test_size must be positive")

    split_index = int(observations * train_fraction)
    train_size = max(split_index, min_train_size)
    max_train_size = observations - min_test_size
    if min_train_size > max_train_size:
        raise ValueError("observations cannot satisfy minimum train/test sizes")
    train_size = min(train_size, max_train_size)

    train = IndexWindow(start=0, end=train_size)
    test = IndexWindow(start=train.end, end=observations)
    return TrainTestSplit(
        train=train,
        test=test,
        observations=observations,
        train_fraction=train_fraction,
    )


def generate_walk_forward_windows(
    observations: int,
    *,
    train_size: int,
    test_size: int,
    step_size: int | None = None,
    min_folds: int = 1,
) -> tuple[WalkForwardWindow, ...]:
    """Generate chronological rolling train/test windows."""
    _validate_observation_count(observations)
    if train_size < 1:
        raise ValueError("train_size must be positive")
    if test_size < 1:
        raise ValueError("test_size must be positive")
    if step_size is None:
        step_size = test_size
    if step_size < 1:
        raise ValueError("step_size must be positive")
    if min_folds < 1:
        raise ValueError("min_folds must be positive")
    if observations < train_size + test_size:
        raise ValueError("observations cannot fit one train/test window")

    windows: list[WalkForwardWindow] = []
    fold = 0
    train_start = 0
    while train_start + train_size + test_size <= observations:
        train = IndexWindow(start=train_start, end=train_start + train_size)
        test = IndexWindow(start=train.end, end=train.end + test_size)
        windows.append(WalkForwardWindow(fold=fold, train=train, test=test))
        fold += 1
        train_start += step_size

    if len(windows) < min_folds:
        raise ValueError("not enough walk-forward folds")
    return tuple(windows)


def assert_no_lookahead(windows: tuple[WalkForwardWindow, ...]) -> None:
    """Validate that every fold uses strictly past train data for its test window."""
    if not windows:
        raise ValueError("windows must not be empty")
    previous_test_start: int | None = None
    for expected_fold, window in enumerate(windows):
        if window.fold != expected_fold:
            raise ValueError("walk-forward folds must be sequential")
        if window.train.start < 0 or window.test.start < 0:
            raise ValueError("window indices must be non-negative")
        if window.train.start >= window.train.end:
            raise ValueError("train window must be non-empty")
        if window.test.start >= window.test.end:
            raise ValueError("test window must be non-empty")
        if window.train.end > window.test.start:
            raise ValueError("train window must not overlap or follow test window")
        if previous_test_start is not None and window.test.start <= previous_test_start:
            raise ValueError("test windows must move forward")
        previous_test_start = window.test.start


def _validate_observation_count(observations: int) -> None:
    if isinstance(observations, bool) or not isinstance(observations, int):
        raise TypeError("observations must be an integer")
    if observations < 2:
        raise ValueError("observations must be at least 2")
