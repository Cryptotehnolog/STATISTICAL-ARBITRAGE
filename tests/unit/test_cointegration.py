"""Unit tests for Engle-Granger cointegration helpers."""

import numpy as np
import pytest

from stat_arb.statistical import (
    MultipleTestingMethod,
    adjust_p_values,
    engle_granger_cointegration_test,
)


def test_engle_granger_detects_synthetic_cointegrated_pair() -> None:
    """Cointegrated random walks should pass the Engle-Granger test."""
    rng = np.random.default_rng(42)
    asset_a = np.cumsum(rng.normal(size=300)) + 100.0
    stationary_noise = rng.normal(scale=0.15, size=300)
    asset_b = 1.7 * asset_a + stationary_noise

    result = engle_granger_cointegration_test(asset_a, asset_b)

    assert result.observations == 300
    assert result.passed is True
    assert result.p_value < 0.05
    assert result.corrected_p_value == pytest.approx(result.p_value)
    assert set(result.critical_values) == {"1%", "5%", "10%"}


def test_engle_granger_rejects_short_or_misaligned_inputs() -> None:
    """The test boundary should reject invalid pair inputs before statsmodels."""
    with pytest.raises(ValueError, match="same length"):
        engle_granger_cointegration_test([1.0, 2.0] * 10, [1.0, 2.0, 3.0] * 10)

    with pytest.raises(ValueError, match="at least 20"):
        engle_granger_cointegration_test([1.0, 2.0], [1.1, 2.1])

    with pytest.raises(ValueError, match="finite"):
        engle_granger_cointegration_test([1.0, np.nan] * 10, [1.0, 2.0] * 10)


def test_cointegration_uses_corrected_p_value_for_pass_decision() -> None:
    """Multiple-testing correction should control the pass/fail decision."""
    rng = np.random.default_rng(7)
    asset_a = np.cumsum(rng.normal(size=250))
    asset_b = 0.9 * asset_a + rng.normal(scale=0.1, size=250)

    result = engle_granger_cointegration_test(
        asset_a,
        asset_b,
        corrected_p_value=0.2,
        multiple_testing_method=MultipleTestingMethod.BONFERRONI,
    )

    assert result.p_value < 0.05
    assert result.corrected_p_value == 0.2
    assert result.multiple_testing_method == MultipleTestingMethod.BONFERRONI
    assert result.passed is False


def test_adjust_p_values_supports_bonferroni_and_bh() -> None:
    """Multiple-testing helpers should return stable corrected p-values."""
    p_values = [0.01, 0.04, 0.2]

    assert adjust_p_values(p_values, method=MultipleTestingMethod.NONE) == pytest.approx((0.01, 0.04, 0.2))
    assert adjust_p_values(p_values, method=MultipleTestingMethod.BONFERRONI) == pytest.approx((0.03, 0.12, 0.6))
    assert adjust_p_values(p_values, method=MultipleTestingMethod.BENJAMINI_HOCHBERG) == pytest.approx(
        (0.03, 0.06, 0.2)
    )


def test_adjust_p_values_rejects_invalid_values() -> None:
    """Correction helpers should not silently accept invalid p-values."""
    with pytest.raises(ValueError, match="between 0 and 1"):
        adjust_p_values([0.1, 1.2])

    with pytest.raises(ValueError, match="finite"):
        adjust_p_values([0.1, np.inf])
