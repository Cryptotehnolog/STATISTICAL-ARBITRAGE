"""Unit tests for residual stationarity helpers."""

import numpy as np
import pytest

from stat_arb.statistical import adf_stationarity_test


def _ar1_series(*, phi: float, size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    values = np.zeros(size)
    shocks = rng.normal(size=size)
    for index in range(1, size):
        values[index] = phi * values[index - 1] + shocks[index]
    return values


def test_adf_accepts_stationary_residuals() -> None:
    """ADF should reject the unit-root null for stationary residuals."""
    residuals = _ar1_series(phi=0.45, size=300, seed=21)

    result = adf_stationarity_test(residuals)

    assert result.passed is True
    assert result.p_value < 0.05
    assert result.observations > 250
    assert result.used_lag >= 0
    assert {"1%", "5%", "10%"} <= set(result.critical_values)


def test_adf_rejects_non_stationary_random_walk() -> None:
    """ADF should fail to reject the unit-root null for a random walk."""
    rng = np.random.default_rng(84)
    residuals = np.cumsum(rng.normal(size=300))

    result = adf_stationarity_test(residuals)

    assert result.passed is False
    assert result.p_value > 0.05


def test_adf_rejects_invalid_inputs() -> None:
    """ADF boundary should validate shape, finiteness, sample size, and alpha."""
    with pytest.raises(ValueError, match="one-dimensional"):
        adf_stationarity_test([[1.0, 2.0], [3.0, 4.0]])

    with pytest.raises(ValueError, match="finite"):
        adf_stationarity_test([1.0, np.nan] * 20)

    with pytest.raises(ValueError, match="at least 20"):
        adf_stationarity_test([1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="non-constant"):
        adf_stationarity_test([1.0] * 30)

    with pytest.raises(ValueError, match="alpha"):
        adf_stationarity_test(np.arange(30), alpha=1.5)
