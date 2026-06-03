"""Z-score construction helpers for spread residuals."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike


@dataclass(frozen=True)
class ZScoreResult:
    """Rolling z-score series for spread residuals."""

    z_scores: np.ndarray
    rolling_mean: np.ndarray
    rolling_std: np.ndarray
    window: int
    observations: int


def construct_rolling_zscore(
    residuals: ArrayLike,
    *,
    window: int,
    ddof: int = 0,
) -> ZScoreResult:
    """Construct rolling z-scores from spread residuals."""
    series = _as_1d_finite_array(residuals, name="residuals")
    if window < 2:
        raise ValueError("window must be at least 2")
    if window > series.size:
        raise ValueError("window cannot exceed residual count")
    if ddof < 0:
        raise ValueError("ddof must be non-negative")

    rolling = pd.Series(series).rolling(window=window, min_periods=window)
    rolling_mean = rolling.mean().to_numpy(dtype=float)
    rolling_std = rolling.std(ddof=ddof).to_numpy(dtype=float)
    z_scores = np.full(series.shape, np.nan, dtype=float)
    valid = np.isfinite(rolling_std) & (rolling_std > 0.0)
    z_scores[valid] = (series[valid] - rolling_mean[valid]) / rolling_std[valid]

    return ZScoreResult(
        z_scores=z_scores,
        rolling_mean=rolling_mean,
        rolling_std=rolling_std,
        window=window,
        observations=int(series.size),
    )


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array
