"""Bounded property tests for statistical testing helpers."""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stat_arb.statistical import (
    adf_stationarity_test,
    construct_rolling_zscore,
    engle_granger_cointegration_test,
    estimate_half_life,
)


@pytest.mark.property
@settings(max_examples=12, deadline=None)
@given(
    seed=st.integers(min_value=1, max_value=10_000),
    beta=st.floats(min_value=0.5, max_value=2.5, allow_nan=False, allow_infinity=False),
    noise_scale=st.floats(min_value=0.03, max_value=0.25, allow_nan=False, allow_infinity=False),
)
def test_cointegration_detects_synthetic_cointegrated_pairs(seed: int, beta: float, noise_scale: float) -> None:
    """Property 7: generated cointegrated random walks should pass Engle-Granger."""
    rng = np.random.default_rng(seed)
    asset_a = np.cumsum(rng.normal(size=220)) + 100.0
    asset_b = beta * asset_a + rng.normal(scale=noise_scale, size=220)

    result = engle_granger_cointegration_test(asset_a, asset_b)

    assert result.passed is True
    assert result.p_value < 0.05


@pytest.mark.property
@settings(max_examples=12, deadline=None)
@given(
    seed=st.integers(min_value=1, max_value=10_000),
    phi=st.floats(min_value=0.05, max_value=0.75, allow_nan=False, allow_infinity=False),
)
def test_adf_detects_stationary_ar1_residuals(seed: int, phi: float) -> None:
    """Property 8: generated stationary AR(1) residuals should pass ADF."""
    rng = np.random.default_rng(seed)
    residuals = np.zeros(240)
    shocks = rng.normal(size=240)
    for index in range(1, residuals.size):
        residuals[index] = phi * residuals[index - 1] + shocks[index]

    result = adf_stationarity_test(residuals)

    assert result.passed is True
    assert result.p_value < 0.05


@pytest.mark.property
@settings(max_examples=20, deadline=None)
@given(
    half_life=st.floats(min_value=3.0, max_value=20.0, allow_nan=False, allow_infinity=False),
)
def test_half_life_estimation_tracks_synthetic_mean_reversion(half_life: float) -> None:
    """Property 9: generated OU-like residuals should recover half-life within 20%."""
    phi = float(np.exp(-np.log(2.0) / half_life))
    residuals = phi ** np.arange(500)

    result = estimate_half_life(residuals)

    assert result.half_life_periods == pytest.approx(half_life, rel=0.2)


@pytest.mark.property
@settings(max_examples=16, deadline=None)
@given(
    window=st.integers(min_value=5, max_value=30),
    offset=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    scale=st.floats(min_value=0.5, max_value=20.0, allow_nan=False, allow_infinity=False),
)
def test_rolling_zscore_standardizes_repeating_window(window: int, offset: float, scale: float) -> None:
    """Property 10: rolling z-scores should stay centered and unit-scaled."""
    base = np.linspace(-1.0, 1.0, window)
    base = (base - base.mean()) / base.std(ddof=0)
    residuals = offset + scale * np.tile(base, 30)

    result = construct_rolling_zscore(residuals, window=window)
    finite = result.z_scores[np.isfinite(result.z_scores)]

    assert finite.size >= window * 20
    assert abs(float(finite.mean())) < 0.05
    assert float(finite.std(ddof=0)) == pytest.approx(1.0, rel=0.05)
