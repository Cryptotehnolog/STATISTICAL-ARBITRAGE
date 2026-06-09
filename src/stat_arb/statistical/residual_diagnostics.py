"""Residual diagnostic helpers for statistical arbitrage assumptions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike
from scipy.stats import jarque_bera, kurtosis
from statsmodels.stats.diagnostic import acorr_ljungbox


@dataclass(frozen=True)
class ResidualDiagnosticsResult:
    """Autocorrelation and distribution diagnostics for spread residuals."""

    ljung_box_p_value: float
    jarque_bera_p_value: float
    excess_kurtosis: float
    observations: int
    lags: int


def diagnose_residuals(
    residuals: ArrayLike,
    *,
    ljung_box_lags: int,
) -> ResidualDiagnosticsResult:
    """Compute residual diagnostics with explicit Ljung-Box lag count."""
    series = _as_1d_finite_array(residuals, name="residuals")
    if series.size < 4:
        raise ValueError("residual diagnostics require at least 4 observations")
    if np.allclose(series, series[0]):
        raise ValueError("residual diagnostics require non-constant residuals")
    if isinstance(ljung_box_lags, bool) or ljung_box_lags <= 0:
        raise ValueError("ljung_box_lags must be a positive integer")
    if ljung_box_lags >= series.size:
        raise ValueError("ljung_box_lags must be lower than observation count")

    ljung_box = acorr_ljungbox(series, lags=[ljung_box_lags], return_df=True)
    jb = jarque_bera(series)
    return ResidualDiagnosticsResult(
        ljung_box_p_value=float(ljung_box["lb_pvalue"].iloc[-1]),
        jarque_bera_p_value=float(jb.pvalue),
        excess_kurtosis=float(kurtosis(series, fisher=True, bias=False)),
        observations=int(series.size),
        lags=int(ljung_box_lags),
    )


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array
