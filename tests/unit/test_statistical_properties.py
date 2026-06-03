"""Bounded property tests for statistical testing helpers."""

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stat_arb.statistical import adf_stationarity_test, engle_granger_cointegration_test


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
