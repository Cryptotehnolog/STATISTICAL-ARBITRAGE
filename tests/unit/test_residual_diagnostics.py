"""Unit tests for residual diagnostic helpers."""

from __future__ import annotations

import numpy as np
import pytest

from stat_arb.statistical import diagnose_residuals


def test_diagnose_residuals_reports_autocorrelation_and_distribution_stats() -> None:
    """Residual diagnostics should expose explicit p-values and excess kurtosis."""
    rng = np.random.default_rng(42)
    shocks = rng.normal(size=300)
    residuals = np.zeros(300)
    for index in range(1, residuals.size):
        residuals[index] = 0.85 * residuals[index - 1] + shocks[index]

    result = diagnose_residuals(residuals, ljung_box_lags=10)

    assert result.observations == 300
    assert result.lags == 10
    assert 0.0 <= result.ljung_box_p_value <= 1.0
    assert result.ljung_box_p_value < 0.05
    assert 0.0 <= result.jarque_bera_p_value <= 1.0
    assert np.isfinite(result.excess_kurtosis)


def test_diagnose_residuals_rejects_invalid_inputs() -> None:
    """Residual diagnostics should fail early on invalid residual inputs."""
    with pytest.raises(ValueError, match="at least 4"):
        diagnose_residuals([1.0, 2.0, 3.0], ljung_box_lags=1)
    with pytest.raises(ValueError, match="non-constant"):
        diagnose_residuals([1.0, 1.0, 1.0, 1.0], ljung_box_lags=1)
    with pytest.raises(ValueError, match="positive integer"):
        diagnose_residuals([1.0, 2.0, 3.0, 4.0], ljung_box_lags=0)
    with pytest.raises(ValueError, match="lower than observation count"):
        diagnose_residuals([1.0, 2.0, 3.0, 4.0], ljung_box_lags=4)
