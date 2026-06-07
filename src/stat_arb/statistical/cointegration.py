"""Engle-Granger cointegration testing helpers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import ArrayLike
from statsmodels.tsa.stattools import coint


class MultipleTestingMethod(StrEnum):
    """Supported p-value correction methods for pair screening."""

    NONE = "none"
    BONFERRONI = "bonferroni"
    BENJAMINI_HOCHBERG = "benjamini_hochberg"


@dataclass(frozen=True)
class CointegrationTestResult:
    """Engle-Granger result for one aligned asset pair."""

    statistic: float
    p_value: float
    critical_values: dict[str, float]
    corrected_p_value: float
    multiple_testing_method: MultipleTestingMethod
    passed: bool
    alpha: float
    observations: int


def engle_granger_cointegration_test(
    asset_a: ArrayLike,
    asset_b: ArrayLike,
    *,
    alpha: float,
    multiple_testing_method: MultipleTestingMethod,
    corrected_p_value: float | None = None,
) -> CointegrationTestResult:
    """Run the Engle-Granger two-step cointegration test on aligned price series."""
    series_a = _as_1d_finite_array(asset_a, name="asset_a")
    series_b = _as_1d_finite_array(asset_b, name="asset_b")
    if series_a.shape != series_b.shape:
        raise ValueError("asset_a and asset_b must have the same length")
    if series_a.size < 20:
        raise ValueError("Engle-Granger test requires at least 20 observations")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between 0 and 1")

    statistic, p_value, critical_values = coint(series_a, series_b)
    effective_p_value = float(p_value if corrected_p_value is None else corrected_p_value)
    if not 0.0 <= effective_p_value <= 1.0:
        raise ValueError("corrected_p_value must be between 0 and 1")

    return CointegrationTestResult(
        statistic=float(statistic),
        p_value=float(p_value),
        critical_values={
            "1%": float(critical_values[0]),
            "5%": float(critical_values[1]),
            "10%": float(critical_values[2]),
        },
        corrected_p_value=effective_p_value,
        multiple_testing_method=multiple_testing_method,
        passed=effective_p_value <= alpha,
        alpha=alpha,
        observations=int(series_a.size),
    )


def adjust_p_values(
    p_values: Iterable[float],
    *,
    method: MultipleTestingMethod,
) -> tuple[float, ...]:
    """Apply a multiple-testing correction to p-values."""
    values = np.asarray(tuple(p_values), dtype=float)
    if values.ndim != 1:
        raise ValueError("p_values must be one-dimensional")
    if values.size == 0:
        return ()
    if not np.all(np.isfinite(values)):
        raise ValueError("p_values must be finite")
    if np.any((values < 0.0) | (values > 1.0)):
        raise ValueError("p_values must be between 0 and 1")

    if method == MultipleTestingMethod.NONE:
        return tuple(float(value) for value in values)
    if method == MultipleTestingMethod.BONFERRONI:
        return tuple(float(value) for value in np.minimum(values * values.size, 1.0))
    if method == MultipleTestingMethod.BENJAMINI_HOCHBERG:
        return _benjamini_hochberg(values)
    raise ValueError(f"unsupported multiple testing method: {method}")


def _benjamini_hochberg(values: np.ndarray) -> tuple[float, ...]:
    order = np.argsort(values)
    sorted_values = values[order]
    ranks = np.arange(1, values.size + 1, dtype=float)
    adjusted_sorted = sorted_values * values.size / ranks
    adjusted_sorted = np.minimum.accumulate(adjusted_sorted[::-1])[::-1]
    adjusted_sorted = np.clip(adjusted_sorted, 0.0, 1.0)

    adjusted = np.empty_like(adjusted_sorted)
    adjusted[order] = adjusted_sorted
    return tuple(float(value) for value in adjusted)


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array
