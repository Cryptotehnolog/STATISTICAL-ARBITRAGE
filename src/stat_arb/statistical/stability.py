"""Rolling hedge-ratio and cointegration stability diagnostics."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np
from numpy.typing import ArrayLike

from stat_arb.statistical.cointegration import (
    MultipleTestingMethod,
    adjust_p_values,
    engle_granger_cointegration_test,
)
from stat_arb.statistical.hedge_ratio import estimate_hedge_ratio


@dataclass(frozen=True)
class StabilityDiagnosticsConfig:
    """Explicit rolling stability diagnostic configuration."""

    window_size: int
    step_size: int
    alpha: float
    multiple_testing_method: MultipleTestingMethod
    include_intercept: bool

    def __post_init__(self) -> None:
        if self.window_size < 20:
            raise ValueError("window_size must be at least 20 for Engle-Granger diagnostics")
        if self.step_size <= 0:
            raise ValueError("step_size must be positive")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must be between 0 and 1")
        if not isinstance(self.include_intercept, bool):
            raise TypeError("include_intercept must be a bool")


@dataclass(frozen=True)
class StabilityDiagnosticsResult:
    """Rolling stability evidence for one aligned asset pair."""

    window_count: int
    window_ranges: tuple[tuple[int, int], ...]
    hedge_ratios: tuple[float, ...]
    hedge_ratio_r_squared: tuple[float, ...]
    hedge_ratio_mean: float
    hedge_ratio_std: float
    hedge_ratio_max_abs_change: float
    cointegration_p_values: tuple[float, ...]
    corrected_cointegration_p_values: tuple[float, ...]
    cointegration_pass_ratio: float
    cointegration_min_p_value: float
    cointegration_max_p_value: float


def diagnose_pair_stability(
    asset_a: ArrayLike,
    asset_b: ArrayLike,
    *,
    config: StabilityDiagnosticsConfig,
) -> StabilityDiagnosticsResult:
    """Measure rolling hedge-ratio and cointegration stability for aligned prices."""
    series_a = _as_1d_finite_array(asset_a, name="asset_a")
    series_b = _as_1d_finite_array(asset_b, name="asset_b")
    if series_a.shape != series_b.shape:
        raise ValueError("asset_a and asset_b must have the same length")

    windows = _rolling_windows(series_a.size, config.window_size, config.step_size)
    if len(windows) < 2:
        raise ValueError("stability diagnostics require at least two rolling windows")

    hedge_ratios: list[float] = []
    r_squared_values: list[float] = []
    p_values: list[float] = []
    for start, end in windows:
        window_a = series_a[start:end]
        window_b = series_b[start:end]
        hedge_ratio = estimate_hedge_ratio(
            window_a,
            window_b,
            include_intercept=config.include_intercept,
        )
        cointegration = engle_granger_cointegration_test(
            window_a,
            window_b,
            alpha=config.alpha,
            multiple_testing_method=MultipleTestingMethod.NONE,
        )
        hedge_ratios.append(hedge_ratio.hedge_ratio)
        r_squared_values.append(hedge_ratio.r_squared)
        p_values.append(cointegration.p_value)

    corrected = adjust_p_values(p_values, method=config.multiple_testing_method)
    hedge_array = np.asarray(hedge_ratios, dtype=float)
    p_value_array = np.asarray(p_values, dtype=float)
    corrected_array = np.asarray(corrected, dtype=float)
    changes = np.abs(np.diff(hedge_array))

    return StabilityDiagnosticsResult(
        window_count=len(windows),
        window_ranges=tuple(windows),
        hedge_ratios=tuple(float(value) for value in hedge_array),
        hedge_ratio_r_squared=tuple(float(value) for value in r_squared_values),
        hedge_ratio_mean=float(np.mean(hedge_array)),
        hedge_ratio_std=float(np.std(hedge_array, ddof=0)),
        hedge_ratio_max_abs_change=float(np.max(changes)) if changes.size else 0.0,
        cointegration_p_values=tuple(float(value) for value in p_value_array),
        corrected_cointegration_p_values=tuple(float(value) for value in corrected_array),
        cointegration_pass_ratio=float(np.mean(corrected_array <= config.alpha)),
        cointegration_min_p_value=float(np.min(p_value_array)),
        cointegration_max_p_value=float(np.max(p_value_array)),
    )


def _rolling_windows(
    observations: int,
    window_size: int,
    step_size: int,
) -> tuple[tuple[int, int], ...]:
    if observations < window_size:
        raise ValueError("asset series length must be at least window_size")
    return tuple(
        (start, start + window_size)
        for start in range(0, observations - window_size + 1, step_size)
    )


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    if not all(isfinite(float(value)) for value in array):
        raise ValueError(f"{name} must contain only finite values")
    return array
