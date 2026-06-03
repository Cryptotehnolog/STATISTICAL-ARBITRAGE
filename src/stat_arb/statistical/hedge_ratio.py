"""OLS hedge-ratio estimation helpers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import statsmodels.api as sm
from numpy.typing import ArrayLike


@dataclass(frozen=True)
class HedgeRatioResult:
    """OLS hedge-ratio estimate for a pair spread."""

    hedge_ratio: float
    intercept: float
    r_squared: float
    observations: int


def estimate_hedge_ratio(
    dependent: ArrayLike,
    independent: ArrayLike,
    *,
    include_intercept: bool = True,
) -> HedgeRatioResult:
    """Estimate hedge ratio by regressing dependent prices on independent prices."""
    y = _as_1d_finite_array(dependent, name="dependent")
    x = _as_1d_finite_array(independent, name="independent")
    if y.shape != x.shape:
        raise ValueError("dependent and independent series must have the same length")
    if y.size < 3:
        raise ValueError("hedge ratio estimation requires at least 3 observations")
    if np.allclose(x, x[0]):
        raise ValueError("independent series must not be constant")

    design = sm.add_constant(x) if include_intercept else x[:, np.newaxis]
    model = sm.OLS(y, design).fit()
    hedge_ratio = float(model.params[1] if include_intercept else model.params[0])
    intercept = float(model.params[0] if include_intercept else 0.0)

    return HedgeRatioResult(
        hedge_ratio=hedge_ratio,
        intercept=intercept,
        r_squared=float(model.rsquared),
        observations=int(y.size),
    )


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array
