"""Unit tests for regime change detection."""

import numpy as np
import pytest

from stat_arb.statistical import detect_regime_changes


def test_detect_regime_changes_flags_mean_shift() -> None:
    """Adjacent rolling windows should flag a clear structural mean break."""
    values = np.concatenate([np.zeros(80), np.full(80, 5.0)])

    result = detect_regime_changes(values, window=20, mean_shift_threshold=2.0)

    assert result.has_regime_change is True
    assert len(result.change_points) == 1
    assert result.change_points[0].index == pytest.approx(80, abs=5)
    assert result.change_points[0].mean_shift_score >= 2.0


def test_detect_regime_changes_flags_volatility_shift() -> None:
    """Adjacent rolling windows should flag a clear volatility break."""
    low_vol = np.tile([-0.1, 0.1], 50)
    high_vol = np.tile([-3.0, 3.0], 50)
    values = np.concatenate([low_vol, high_vol])

    result = detect_regime_changes(
        values,
        window=20,
        mean_shift_threshold=100.0,
        volatility_ratio_threshold=5.0,
    )

    assert result.has_regime_change is True
    assert len(result.change_points) == 1
    assert result.change_points[0].index == pytest.approx(100, abs=5)
    assert result.change_points[0].volatility_ratio >= 5.0


def test_detect_regime_changes_ignores_stable_series() -> None:
    """Stable periodic residuals should not produce false regime breaks."""
    values = np.tile([-1.0, 0.0, 1.0, 0.0], 80)

    result = detect_regime_changes(values, window=24)

    assert result.has_regime_change is False
    assert result.change_points == ()


def test_detect_regime_changes_rejects_invalid_inputs() -> None:
    """Regime detection should validate shape, finiteness, and thresholds."""
    with pytest.raises(ValueError, match="one-dimensional"):
        detect_regime_changes([[1.0, 2.0], [3.0, 4.0]], window=5)

    with pytest.raises(ValueError, match="finite"):
        detect_regime_changes([1.0, np.nan, 2.0, 3.0, 4.0, 5.0], window=5)

    with pytest.raises(ValueError, match="at least 5"):
        detect_regime_changes(np.arange(12.0), window=4)

    with pytest.raises(ValueError, match="two full windows"):
        detect_regime_changes(np.arange(9.0), window=5)

    with pytest.raises(ValueError, match="mean_shift_threshold"):
        detect_regime_changes(np.arange(12.0), window=5, mean_shift_threshold=0.0)

    with pytest.raises(ValueError, match="volatility_ratio_threshold"):
        detect_regime_changes(np.arange(12.0), window=5, volatility_ratio_threshold=1.0)
