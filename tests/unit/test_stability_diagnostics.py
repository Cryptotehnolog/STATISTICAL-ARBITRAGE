"""Unit tests for rolling cointegration and hedge-ratio stability diagnostics."""

import numpy as np
import pytest

from stat_arb.statistical import (
    MultipleTestingMethod,
    StabilityDiagnosticsConfig,
    diagnose_pair_stability,
)


def test_diagnose_pair_stability_reports_stable_cointegrated_pair() -> None:
    """Stable synthetic pairs should produce low hedge-ratio dispersion."""
    rng = np.random.default_rng(41)
    asset_b = np.cumsum(rng.normal(size=270)) + 100.0
    residuals = rng.normal(scale=0.08, size=270)
    asset_a = 1.7 * asset_b + residuals

    result = diagnose_pair_stability(
        asset_a,
        asset_b,
        config=StabilityDiagnosticsConfig(
            window_size=90,
            step_size=45,
            alpha=0.05,
            multiple_testing_method=MultipleTestingMethod.NONE,
            include_intercept=True,
        ),
    )

    assert result.window_count == 5
    assert result.hedge_ratio_mean == pytest.approx(1.7, abs=0.03)
    assert result.hedge_ratio_std < 0.03
    assert result.hedge_ratio_max_abs_change < 0.05
    assert result.cointegration_pass_ratio == pytest.approx(1.0)
    assert all(0.0 <= value <= 1.0 for value in result.cointegration_p_values)


def test_diagnose_pair_stability_exposes_unstable_hedge_ratio() -> None:
    """Rolling diagnostics should expose a clear hedge-ratio break."""
    rng = np.random.default_rng(72)
    asset_b = np.cumsum(rng.normal(size=180)) + 100.0
    first_half = 1.2 * asset_b[:90] + rng.normal(scale=0.05, size=90)
    second_half = 2.4 * asset_b[90:] + rng.normal(scale=0.05, size=90)
    asset_a = np.concatenate([first_half, second_half])

    result = diagnose_pair_stability(
        asset_a,
        asset_b,
        config=StabilityDiagnosticsConfig(
            window_size=60,
            step_size=30,
            alpha=0.05,
            multiple_testing_method=MultipleTestingMethod.NONE,
            include_intercept=True,
        ),
    )

    assert result.window_count == 5
    assert result.hedge_ratio_std > 0.4
    assert result.hedge_ratio_max_abs_change > 0.9


def test_diagnose_pair_stability_rejects_hidden_or_invalid_config() -> None:
    """Rolling diagnostics require explicit finite research configuration."""
    with pytest.raises(ValueError, match="window_size"):
        StabilityDiagnosticsConfig(
            window_size=19,
            step_size=5,
            alpha=0.05,
            multiple_testing_method=MultipleTestingMethod.NONE,
            include_intercept=True,
        )

    with pytest.raises(ValueError, match="step_size"):
        StabilityDiagnosticsConfig(
            window_size=20,
            step_size=0,
            alpha=0.05,
            multiple_testing_method=MultipleTestingMethod.NONE,
            include_intercept=True,
        )

    with pytest.raises(ValueError, match="at least two rolling windows"):
        diagnose_pair_stability(
            [1.0] * 50,
            [2.0] * 50,
            config=StabilityDiagnosticsConfig(
                window_size=40,
                step_size=20,
                alpha=0.05,
                multiple_testing_method=MultipleTestingMethod.NONE,
                include_intercept=True,
            ),
        )
