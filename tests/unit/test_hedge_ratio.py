"""Unit tests for OLS hedge-ratio estimation."""

import numpy as np
import pytest

from stat_arb.statistical import estimate_hedge_ratio


def test_estimate_hedge_ratio_recovers_synthetic_beta_with_intercept() -> None:
    """OLS should recover the synthetic pair hedge ratio and regression quality."""
    rng = np.random.default_rng(123)
    independent = np.linspace(50.0, 120.0, 250)
    dependent = 3.5 + 1.65 * independent + rng.normal(scale=0.05, size=independent.size)

    result = estimate_hedge_ratio(dependent, independent)

    assert result.observations == 250
    assert result.hedge_ratio == pytest.approx(1.65, abs=0.005)
    assert result.intercept == pytest.approx(3.5, abs=0.05)
    assert result.r_squared > 0.999


def test_estimate_hedge_ratio_can_omit_intercept() -> None:
    """No-intercept mode should estimate beta through the origin."""
    independent = np.linspace(1.0, 100.0, 200)
    dependent = 2.25 * independent

    result = estimate_hedge_ratio(dependent, independent, include_intercept=False)

    assert result.hedge_ratio == pytest.approx(2.25)
    assert result.intercept == 0.0
    assert result.r_squared == pytest.approx(1.0)


def test_estimate_hedge_ratio_rejects_invalid_inputs() -> None:
    """Hedge-ratio boundary should reject malformed pair series."""
    with pytest.raises(ValueError, match="same length"):
        estimate_hedge_ratio([1.0, 2.0, 3.0], [1.0, 2.0])

    with pytest.raises(ValueError, match="at least 3"):
        estimate_hedge_ratio([1.0, 2.0], [1.0, 2.0])

    with pytest.raises(ValueError, match="finite"):
        estimate_hedge_ratio([1.0, np.inf, 3.0], [1.0, 2.0, 3.0])

    with pytest.raises(ValueError, match="constant"):
        estimate_hedge_ratio([1.0, 2.0, 3.0], [5.0, 5.0, 5.0])
