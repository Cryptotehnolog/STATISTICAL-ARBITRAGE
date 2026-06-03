"""Stationarity testing helpers for pair spread residuals."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike
from statsmodels.tsa.stattools import adfuller


@dataclass(frozen=True)
class ADFTestResult:
    """Augmented Dickey-Fuller stationarity test result."""

    statistic: float
    p_value: float
    critical_values: dict[str, float]
    used_lag: int
    observations: int
    information_criterion: float | None
    passed: bool
    alpha: float


def adf_stationarity_test(
    residuals: ArrayLike,
    *,
    alpha: float = 0.05,
    regression: str = "c",
    autolag: str | None = "AIC",
) -> ADFTestResult:
    """Run an ADF test on spread residuals."""
    series = _as_1d_finite_array(residuals, name="residuals")
    if series.size < 20:
        raise ValueError("ADF test requires at least 20 observations")
    if np.allclose(series, series[0]):
        raise ValueError("ADF test requires non-constant residuals")
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be between 0 and 1")

    result = adfuller(series, regression=regression, autolag=autolag)
    statistic = float(result[0])
    p_value = float(result[1])
    used_lag = int(result[2])
    observations = int(result[3])
    critical_values = {key: float(value) for key, value in result[4].items()}
    information_criterion = float(result[5]) if len(result) > 5 and result[5] is not None else None

    return ADFTestResult(
        statistic=statistic,
        p_value=p_value,
        critical_values=critical_values,
        used_lag=used_lag,
        observations=observations,
        information_criterion=information_criterion,
        passed=p_value <= alpha,
        alpha=alpha,
    )


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array
