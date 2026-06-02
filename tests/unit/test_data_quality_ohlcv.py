"""Unit tests for OHLCV data quality validation."""

from datetime import UTC, datetime, timedelta

import pytest

from stat_arb.data_quality import OHLCVQualityConfig, validate_ohlcv_batch
from stat_arb.domain import DataQualitySeverity, DatasetSource, OHLCVBar, OHLCVBatch


def _bar(index: int, *, volume: float = 10.0) -> OHLCVBar:
    timestamp = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(minutes=5 * index)
    return OHLCVBar(
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="5m",
        timestamp=timestamp,
        open=100.0 + index,
        high=101.0 + index,
        low=99.0 + index,
        close=100.5 + index,
        volume=volume,
        exchange="binance",
    )


def test_validate_ohlcv_batch_passes_complete_series() -> None:
    """A complete ordered series should produce a passing quality report."""
    bars = [_bar(0), _bar(1), _bar(2)]
    batch = OHLCVBatch(
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="5m",
        bars=bars,
        exchange="binance",
    )

    report = validate_ohlcv_batch(batch)

    assert report.passed is True
    assert report.bar_count == 3
    assert report.expected_bar_count == 3
    assert report.missing_bars == 0
    assert report.duplicate_timestamps == 0
    assert report.quality_score == 1.0
    assert report.issues == []


def test_validate_ohlcv_batch_detects_missing_bars() -> None:
    """Missing timestamps should be counted and fail strict validation."""
    report = validate_ohlcv_batch([_bar(0), _bar(2)])

    assert report.passed is False
    assert report.expected_bar_count == 3
    assert report.missing_bars == 1
    assert report.alignment_score == pytest.approx(2 / 3)
    assert report.issues[0].code == "missing_bars"
    assert report.issues[0].severity == DataQualitySeverity.ERROR


def test_validate_ohlcv_batch_allows_missing_bars_within_threshold() -> None:
    """Configured thresholds should downgrade small missing gaps to warnings."""
    config = OHLCVQualityConfig(max_missing_bar_ratio=0.5)

    report = validate_ohlcv_batch([_bar(0), _bar(2)], config=config)

    assert report.passed is True
    assert report.missing_bars == 1
    assert report.issues[0].severity == DataQualitySeverity.WARNING


def test_validate_ohlcv_batch_detects_duplicate_raw_timestamps() -> None:
    """Raw bar sequences should catch duplicates before OHLCVBatch construction."""
    duplicate = _bar(1).model_copy(update={"close": 101.25})

    report = validate_ohlcv_batch([_bar(0), _bar(1), duplicate, _bar(2)])

    assert report.passed is False
    assert report.bar_count == 3
    assert report.expected_bar_count == 3
    assert report.duplicate_timestamps == 1
    assert report.issues[0].code == "duplicate_timestamps"


def test_validate_ohlcv_batch_detects_abnormal_volume_spikes() -> None:
    """Volume spikes should be warning-level unless they exceed the configured ratio."""
    report = validate_ohlcv_batch([_bar(0), _bar(1), _bar(2, volume=500.0), _bar(3)])

    assert report.passed is False
    assert report.abnormal_volume_count == 1
    assert report.issues[0].code == "abnormal_volume"
    assert report.issues[0].severity == DataQualitySeverity.ERROR


def test_validate_ohlcv_batch_rejects_empty_or_mixed_series() -> None:
    """Validation input must represent one non-empty OHLCV series."""
    with pytest.raises(ValueError, match="at least one bar"):
        validate_ohlcv_batch([])

    wrong_symbol = _bar(1).model_copy(update={"symbol": "ETH/USDT"})
    with pytest.raises(ValueError, match="first bar symbol"):
        validate_ohlcv_batch([_bar(0), wrong_symbol])
