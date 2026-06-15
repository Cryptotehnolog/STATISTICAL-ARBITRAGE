"""Unit tests for OHLCV data quality validation."""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stat_arb.data_quality import (
    OHLCVQualityConfig,
    summarize_data_quality_failure,
    validate_ohlcv_batch,
)
from stat_arb.domain import (
    DataQualityFailureSummary,
    DataQualitySeverity,
    DatasetSource,
    OHLCVBar,
    OHLCVBatch,
)


def _strict_quality_config() -> OHLCVQualityConfig:
    return OHLCVQualityConfig(
        max_missing_bar_ratio=0.0,
        max_abnormal_volume_ratio=0.0,
        volume_spike_multiplier=10.0,
    )


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

    report = validate_ohlcv_batch(batch, config=_strict_quality_config())

    assert report.passed is True
    assert report.bar_count == 3
    assert report.expected_bar_count == 3
    assert report.missing_bars == 0
    assert report.duplicate_timestamps == 0
    assert report.quality_score == 1.0
    assert report.issues == []


def test_validate_ohlcv_batch_returns_single_bar_diagnostic_report() -> None:
    """A single bar should be diagnostic only, not a passing quality report."""
    bar = _bar(0)

    report = validate_ohlcv_batch([bar], config=_strict_quality_config())

    assert report.passed is False
    assert report.is_valid is False
    assert report.invalid_reason == "insufficient_data"
    assert report.start_date == bar.timestamp
    assert report.end_date == bar.timestamp
    assert report.bar_count == 1
    assert report.expected_bar_count == 1
    assert report.quality_score == 0.0
    assert report.issues[0].code == "insufficient_data"
    assert report.issues[0].severity == DataQualitySeverity.ERROR


def test_validate_ohlcv_batch_detects_missing_bars() -> None:
    """Missing timestamps should be counted and fail strict validation."""
    report = validate_ohlcv_batch([_bar(0), _bar(2)], config=_strict_quality_config())

    assert report.passed is False
    assert report.expected_bar_count == 3
    assert report.missing_bars == 1
    assert report.alignment_score == pytest.approx(2 / 3)
    assert report.issues[0].code == "missing_bars"
    assert report.issues[0].severity == DataQualitySeverity.ERROR


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(indexes=st.sets(st.integers(min_value=0, max_value=60), min_size=2, max_size=30))
def test_validate_ohlcv_batch_missing_bar_count_is_complete(indexes: set[int]) -> None:
    """Property 2: missing-bar count should equal gaps in the timestamp sequence."""
    ordered_indexes = sorted(indexes)

    report = validate_ohlcv_batch([_bar(index) for index in ordered_indexes], config=_strict_quality_config())

    expected_bar_count = ordered_indexes[-1] - ordered_indexes[0] + 1
    assert report.expected_bar_count == expected_bar_count
    assert report.missing_bars == expected_bar_count - len(ordered_indexes)


def test_validate_ohlcv_batch_allows_missing_bars_within_threshold() -> None:
    """Configured thresholds should downgrade small missing gaps to warnings."""
    config = OHLCVQualityConfig(
        max_missing_bar_ratio=0.5,
        max_abnormal_volume_ratio=0.0,
        volume_spike_multiplier=10.0,
    )

    report = validate_ohlcv_batch([_bar(0), _bar(2)], config=config)

    assert report.passed is True
    assert report.missing_bars == 1
    assert report.issues[0].severity == DataQualitySeverity.WARNING


def test_validate_ohlcv_batch_detects_duplicate_raw_timestamps() -> None:
    """Raw bar sequences should catch duplicates before OHLCVBatch construction."""
    duplicate = _bar(1).model_copy(update={"close": 101.25})

    report = validate_ohlcv_batch([_bar(0), _bar(1), duplicate, _bar(2)], config=_strict_quality_config())

    assert report.passed is False
    assert report.bar_count == 3
    assert report.expected_bar_count == 3
    assert report.duplicate_timestamps == 1
    assert report.issues[0].code == "duplicate_timestamps"


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(
    duplicate_index=st.integers(min_value=0, max_value=9),
    duplicate_count=st.integers(min_value=1, max_value=5),
)
def test_validate_ohlcv_batch_duplicate_count_is_complete(
    duplicate_index: int,
    duplicate_count: int,
) -> None:
    """Property 3: duplicate timestamp detection should count every repeated raw bar."""
    bars = [_bar(index) for index in range(10)]
    bars.extend(_bar(duplicate_index).model_copy(update={"close": 101.25}) for _ in range(duplicate_count))

    report = validate_ohlcv_batch(bars, config=_strict_quality_config())

    assert report.duplicate_timestamps == duplicate_count
    assert any(issue.code == "duplicate_timestamps" for issue in report.issues)
    assert report.passed is False


def test_validate_ohlcv_batch_detects_abnormal_volume_spikes() -> None:
    """Volume spikes should be warning-level unless they exceed the configured ratio."""
    report = validate_ohlcv_batch(
        [_bar(0), _bar(1), _bar(2, volume=500.0), _bar(3)],
        config=_strict_quality_config(),
    )

    assert report.passed is False
    assert report.abnormal_volume_count == 1
    assert report.issues[0].code == "abnormal_volume"
    assert report.issues[0].severity == DataQualitySeverity.ERROR


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(
    bar_count=st.integers(min_value=3, max_value=40),
    spike_index=st.integers(min_value=0, max_value=39),
)
def test_validate_ohlcv_batch_volume_spike_detection_is_sensitive(
    bar_count: int,
    spike_index: int,
) -> None:
    """Property 4: a single large volume spike should be detected in valid series."""
    spike_index %= bar_count
    bars = [_bar(index) for index in range(bar_count)]
    bars[spike_index] = _bar(spike_index, volume=500.0)

    report = validate_ohlcv_batch(bars, config=_strict_quality_config())

    assert report.abnormal_volume_count == 1
    assert any(issue.code == "abnormal_volume" for issue in report.issues)


def test_validate_ohlcv_batch_rejects_empty_or_mixed_series() -> None:
    """Validation input must represent one non-empty OHLCV series."""
    with pytest.raises(ValueError, match="at least one bar"):
        validate_ohlcv_batch([], config=_strict_quality_config())

    wrong_symbol = _bar(1).model_copy(update={"symbol": "ETH/USDT"})
    with pytest.raises(ValueError, match="first bar symbol"):
        validate_ohlcv_batch([_bar(0), wrong_symbol], config=_strict_quality_config())


def test_summarize_data_quality_failure_builds_memory_safe_contract() -> None:
    """Failed reports should produce concise summaries for future Memory Agent writes."""
    report = validate_ohlcv_batch([_bar(0), _bar(2)], config=_strict_quality_config())

    summary = summarize_data_quality_failure(report)

    assert summary.report_id == report.report_id
    assert summary.dataset_id == report.dataset_id
    assert summary.symbol == "BTC/USDT"
    assert summary.issue_codes == ["missing_bars"]
    assert summary.registry_reference == f"data_quality_reports/{report.report_id}"
    assert "failed data quality validation" in summary.summary
    assert "missing_bars: 1" in summary.summary

    restored = DataQualityFailureSummary.model_validate_json(summary.model_dump_json())
    assert restored == summary


def test_summarize_data_quality_failure_rejects_passing_reports() -> None:
    """Passing reports should not be written to failure memory."""
    report = validate_ohlcv_batch([_bar(0), _bar(1), _bar(2)], config=_strict_quality_config())

    with pytest.raises(ValueError, match="Only failed data quality reports"):
        summarize_data_quality_failure(report)
