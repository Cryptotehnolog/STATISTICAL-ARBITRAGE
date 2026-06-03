"""Unit tests for mean-reversion half-life estimation."""

import numpy as np
import pytest

from stat_arb.statistical import estimate_half_life


def _mean_reverting_series(*, half_life_periods: float, size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    phi = float(np.exp(-np.log(2.0) / half_life_periods))
    values = np.zeros(size)
    shocks = rng.normal(scale=0.35, size=size)
    for index in range(1, size):
        values[index] = phi * values[index - 1] + shocks[index]
    return values


def test_estimate_half_life_recovers_synthetic_ou_process() -> None:
    """Estimator should recover a known mean-reversion half-life."""
    residuals = _mean_reverting_series(half_life_periods=8.0, size=900, seed=91)

    result = estimate_half_life(residuals, periods_per_day=24.0)

    assert result.observations == 900
    assert result.half_life_periods == pytest.approx(8.0, rel=0.2)
    assert result.half_life_days == pytest.approx(result.half_life_periods / 24.0)
    assert 0.0 < result.ar1_phi < 1.0
    assert result.mean_reversion_speed > 0.0


def test_estimate_half_life_rejects_non_mean_reverting_series() -> None:
    """Trending residuals should not produce a positive half-life."""
    residuals = np.linspace(0.0, 100.0, 200)

    with pytest.raises(ValueError, match="positive mean reversion"):
        estimate_half_life(residuals)


def test_estimate_half_life_rejects_invalid_inputs() -> None:
    """Half-life boundary should validate residual inputs and scaling."""
    with pytest.raises(ValueError, match="one-dimensional"):
        estimate_half_life([[1.0, 2.0], [3.0, 4.0]])

    with pytest.raises(ValueError, match="finite"):
        estimate_half_life([1.0, np.nan] * 20)

    with pytest.raises(ValueError, match="at least 20"):
        estimate_half_life([1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="non-constant"):
        estimate_half_life([1.0] * 30)

    with pytest.raises(ValueError, match="periods_per_day"):
        estimate_half_life(np.arange(30), periods_per_day=0.0)
