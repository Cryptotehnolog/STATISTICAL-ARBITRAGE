"""Mean-reversion and half-life estimation helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import statsmodels.api as sm
from numpy.typing import ArrayLike


@dataclass(frozen=True)
class HalfLifeResult:
    """Mean-reversion half-life estimate for spread residuals."""

    half_life_periods: float
    half_life_days: float
    ar1_phi: float
    mean_reversion_speed: float
    r_squared: float
    observations: int


def estimate_half_life(
    residuals: ArrayLike,
    *,
    periods_per_day: float = 1.0,
) -> HalfLifeResult:
    """Estimate mean-reversion half-life from spread residuals."""
    series = _as_1d_finite_array(residuals, name="residuals")
    if series.size < 20:
        raise ValueError("half-life estimation requires at least 20 observations")
    if np.allclose(series, series[0]):
        raise ValueError("half-life estimation requires non-constant residuals")
    if periods_per_day <= 0.0:
        raise ValueError("periods_per_day must be positive")

    lagged = series[:-1]
    delta = np.diff(series)
    design = sm.add_constant(lagged)
    model = sm.OLS(delta, design).fit()
    beta = float(model.params[1])
    phi = 1.0 + beta
    if not 0.0 < phi < 1.0:
        raise ValueError("residuals do not show positive mean reversion")

    half_life_periods = float(-np.log(2.0) / np.log(phi))
    return HalfLifeResult(
        half_life_periods=half_life_periods,
        half_life_days=half_life_periods / periods_per_day,
        ar1_phi=float(phi),
        mean_reversion_speed=float(-np.log(phi)),
        r_squared=float(model.rsquared),
        observations=int(series.size),
    )


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array
