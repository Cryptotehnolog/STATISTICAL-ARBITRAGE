"""Unit tests for rolling z-score construction."""

import numpy as np
import pytest

from stat_arb.statistical import construct_rolling_zscore


def test_construct_rolling_zscore_matches_manual_window_calculation() -> None:
    """Rolling z-score should match the explicit trailing-window formula."""
    residuals = np.array([1.0, 2.0, 4.0, 7.0, 11.0])

    result = construct_rolling_zscore(residuals, window=3)

    assert result.observations == 5
    assert result.window == 3
    assert np.isnan(result.z_scores[:2]).all()
    window = residuals[2:5]
    expected = (residuals[-1] - window.mean()) / window.std(ddof=0)
    assert result.z_scores[-1] == pytest.approx(expected)
    assert result.rolling_mean[-1] == pytest.approx(window.mean())
    assert result.rolling_std[-1] == pytest.approx(window.std(ddof=0))


def test_construct_rolling_zscore_leaves_constant_windows_undefined() -> None:
    """Constant rolling windows should not produce infinite z-scores."""
    result = construct_rolling_zscore([5.0, 5.0, 5.0, 5.0], window=2)

    assert np.isnan(result.z_scores).all()
    assert np.nanmax(result.rolling_std) == 0.0


def test_construct_rolling_zscore_standardizes_stationary_tail() -> None:
    """Rolling z-scores should be roughly centered on stationary data."""
    rng = np.random.default_rng(33)
    residuals = rng.normal(size=400)

    result = construct_rolling_zscore(residuals, window=40)
    finite = result.z_scores[np.isfinite(result.z_scores)]

    assert abs(float(finite.mean())) < 0.2
    assert float(finite.std(ddof=0)) == pytest.approx(1.0, rel=0.2)


def test_construct_rolling_zscore_rejects_invalid_inputs() -> None:
    """Z-score boundary should validate shape, finiteness, and window settings."""
    with pytest.raises(ValueError, match="one-dimensional"):
        construct_rolling_zscore([[1.0, 2.0], [3.0, 4.0]], window=2)

    with pytest.raises(ValueError, match="finite"):
        construct_rolling_zscore([1.0, np.nan, 2.0], window=2)

    with pytest.raises(ValueError, match="at least 2"):
        construct_rolling_zscore([1.0, 2.0, 3.0], window=1)

    with pytest.raises(ValueError, match="cannot exceed"):
        construct_rolling_zscore([1.0, 2.0, 3.0], window=4)

    with pytest.raises(ValueError, match="ddof"):
        construct_rolling_zscore([1.0, 2.0, 3.0], window=2, ddof=-1)
