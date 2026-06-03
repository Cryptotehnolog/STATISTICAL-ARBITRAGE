"""Regime change detection helpers for spread residuals."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike


@dataclass(frozen=True)
class RegimeChangePoint:
    """Detected structural break candidate."""

    index: int
    mean_shift_score: float
    volatility_ratio: float


@dataclass(frozen=True)
class RegimeChangeResult:
    """Rolling-statistics regime change detection result."""

    change_points: tuple[RegimeChangePoint, ...]
    mean_shift_scores: np.ndarray
    volatility_ratios: np.ndarray
    window: int
    observations: int
    mean_shift_threshold: float
    volatility_ratio_threshold: float

    @property
    def has_regime_change(self) -> bool:
        """Return true when at least one structural break candidate was detected."""
        return bool(self.change_points)


def detect_regime_changes(
    values: ArrayLike,
    *,
    window: int,
    mean_shift_threshold: float = 3.0,
    volatility_ratio_threshold: float = 2.5,
    min_std: float = 1e-12,
) -> RegimeChangeResult:
    """Detect structural breaks by comparing adjacent rolling windows."""
    series = _as_1d_finite_array(values, name="values")
    if window < 5:
        raise ValueError("window must be at least 5")
    if series.size < window * 2:
        raise ValueError("values must contain at least two full windows")
    if mean_shift_threshold <= 0.0:
        raise ValueError("mean_shift_threshold must be positive")
    if volatility_ratio_threshold <= 1.0:
        raise ValueError("volatility_ratio_threshold must be greater than 1")
    if min_std <= 0.0:
        raise ValueError("min_std must be positive")

    mean_scores = np.full(series.shape, np.nan, dtype=float)
    volatility_ratios = np.full(series.shape, np.nan, dtype=float)
    flagged_indices: list[int] = []

    for index in range(window, series.size - window + 1):
        left = series[index - window : index]
        right = series[index : index + window]
        left_std = float(left.std(ddof=0))
        right_std = float(right.std(ddof=0))
        pooled_std = float(np.sqrt((left_std**2 + right_std**2) / 2.0))

        mean_delta = abs(float(right.mean() - left.mean()))
        if pooled_std > min_std:
            mean_score = mean_delta / pooled_std
        elif mean_delta > min_std:
            mean_score = float("inf")
        else:
            mean_score = 0.0

        volatility_ratio = _std_ratio(left_std, right_std, min_std=min_std)
        mean_scores[index] = mean_score
        volatility_ratios[index] = volatility_ratio

        if mean_score >= mean_shift_threshold or volatility_ratio >= volatility_ratio_threshold:
            flagged_indices.append(index)

    change_points = _collapse_flagged_indices(
        flagged_indices,
        mean_scores,
        volatility_ratios,
        mean_shift_threshold=mean_shift_threshold,
        volatility_ratio_threshold=volatility_ratio_threshold,
    )

    return RegimeChangeResult(
        change_points=tuple(change_points),
        mean_shift_scores=mean_scores,
        volatility_ratios=volatility_ratios,
        window=window,
        observations=int(series.size),
        mean_shift_threshold=mean_shift_threshold,
        volatility_ratio_threshold=volatility_ratio_threshold,
    )


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _std_ratio(left_std: float, right_std: float, *, min_std: float) -> float:
    if left_std <= min_std and right_std <= min_std:
        return 1.0
    denominator = max(min(left_std, right_std), min_std)
    return max(left_std, right_std) / denominator


def _collapse_flagged_indices(
    indices: list[int],
    mean_scores: np.ndarray,
    volatility_ratios: np.ndarray,
    *,
    mean_shift_threshold: float,
    volatility_ratio_threshold: float,
) -> list[RegimeChangePoint]:
    if not indices:
        return []

    clusters: list[list[int]] = [[indices[0]]]
    for index in indices[1:]:
        if index == clusters[-1][-1] + 1:
            clusters[-1].append(index)
        else:
            clusters.append([index])

    change_points: list[RegimeChangePoint] = []
    for cluster in clusters:
        best_index = max(
            cluster,
            key=lambda item: max(
                mean_scores[item] / mean_shift_threshold,
                volatility_ratios[item] / volatility_ratio_threshold,
            ),
        )
        change_points.append(
            RegimeChangePoint(
                index=int(best_index),
                mean_shift_score=float(mean_scores[best_index]),
                volatility_ratio=float(volatility_ratios[best_index]),
            )
        )
    return change_points
