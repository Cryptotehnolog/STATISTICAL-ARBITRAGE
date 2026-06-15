"""Deterministic OHLCV data quality validation."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from stat_arb.domain import (
    DataQualityFailureSummary,
    DataQualityIssue,
    DataQualityReport,
    DataQualitySeverity,
    OHLCVBar,
    OHLCVBatch,
)

_TIMEFRAME_UNITS = {
    "m": "minutes",
    "h": "hours",
    "d": "days",
    "w": "weeks",
}


@dataclass(frozen=True)
class OHLCVQualityConfig:
    """Thresholds for OHLCV quality validation."""

    max_missing_bar_ratio: float
    max_abnormal_volume_ratio: float
    volume_spike_multiplier: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.max_missing_bar_ratio <= 1.0:
            raise ValueError("max_missing_bar_ratio must be between 0.0 and 1.0")
        if not 0.0 <= self.max_abnormal_volume_ratio <= 1.0:
            raise ValueError("max_abnormal_volume_ratio must be between 0.0 and 1.0")
        if self.volume_spike_multiplier <= 1.0:
            raise ValueError("volume_spike_multiplier must be greater than 1.0")


def validate_ohlcv_batch(
    data: OHLCVBatch | Sequence[OHLCVBar],
    *,
    config: OHLCVQualityConfig,
) -> DataQualityReport:
    """Validate one OHLCV series and return a domain quality report.

    ``OHLCVBatch`` already enforces sorted unique timestamps. A raw ``Sequence[OHLCVBar]``
    is accepted so duplicate timestamp detection can run before batch construction.
    """
    bars, batch = _normalize_input(data)
    sorted_bars = sorted(bars, key=lambda bar: bar.timestamp)
    timestamps = [bar.timestamp for bar in sorted_bars]
    timestamp_counts = Counter(timestamps)
    duplicate_count = sum(count - 1 for count in timestamp_counts.values() if count > 1)
    unique_timestamps = sorted(timestamp_counts)
    expected_timestamps = _expected_timestamps(unique_timestamps[0], unique_timestamps[-1], batch.timeframe)
    missing_timestamps = sorted(set(expected_timestamps) - set(unique_timestamps))

    abnormal_volume_count = _count_abnormal_volume_spikes(sorted_bars, config.volume_spike_multiplier)
    expected_bar_count = len(expected_timestamps)
    missing_bar_ratio = len(missing_timestamps) / expected_bar_count if expected_bar_count else 0.0
    abnormal_volume_ratio = abnormal_volume_count / len(sorted_bars)

    issues: list[DataQualityIssue] = []
    insufficient_data = len(unique_timestamps) < 2
    if insufficient_data:
        issues.append(
            DataQualityIssue(
                code="insufficient_data",
                severity=DataQualitySeverity.ERROR,
                message="A single OHLCV bar is diagnostic only and cannot validate data quality.",
                count=len(unique_timestamps),
                first_timestamp=unique_timestamps[0],
                last_timestamp=unique_timestamps[-1],
            )
        )

    if missing_timestamps:
        severity = (
            DataQualitySeverity.ERROR
            if missing_bar_ratio > config.max_missing_bar_ratio
            else DataQualitySeverity.WARNING
        )
        issues.append(
            DataQualityIssue(
                code="missing_bars",
                severity=severity,
                message="Missing OHLCV bars detected in the timestamp sequence.",
                count=len(missing_timestamps),
                first_timestamp=missing_timestamps[0],
                last_timestamp=missing_timestamps[-1],
            )
        )

    if duplicate_count:
        duplicate_timestamps = [timestamp for timestamp, count in timestamp_counts.items() if count > 1]
        issues.append(
            DataQualityIssue(
                code="duplicate_timestamps",
                severity=DataQualitySeverity.ERROR,
                message="Duplicate OHLCV timestamps detected.",
                count=duplicate_count,
                first_timestamp=min(duplicate_timestamps),
                last_timestamp=max(duplicate_timestamps),
            )
        )

    if abnormal_volume_count:
        severity = (
            DataQualitySeverity.ERROR
            if abnormal_volume_ratio > config.max_abnormal_volume_ratio
            else DataQualitySeverity.WARNING
        )
        issues.append(
            DataQualityIssue(
                code="abnormal_volume",
                severity=severity,
                message="OHLCV volume spikes exceed the configured multiplier.",
                count=abnormal_volume_count,
            )
        )

    passed = not any(issue.severity == DataQualitySeverity.ERROR for issue in issues)
    quality_score = (
        0.0
        if insufficient_data
        else _quality_score(
            expected_bar_count=expected_bar_count,
            missing_bars=len(missing_timestamps),
            duplicate_timestamps=duplicate_count,
            abnormal_volume_count=abnormal_volume_count,
        )
    )

    return DataQualityReport(
        dataset_id=batch.dataset_id,
        symbol=batch.symbol,
        source=batch.source,
        timeframe=batch.timeframe,
        start_date=unique_timestamps[0],
        end_date=unique_timestamps[-1],
        bar_count=len(unique_timestamps),
        expected_bar_count=expected_bar_count,
        missing_bars=len(missing_timestamps),
        duplicate_timestamps=duplicate_count,
        abnormal_volume_count=abnormal_volume_count,
        timezone_normalized=all(timestamp.tzinfo is not None for timestamp in timestamps),
        alignment_score=1.0 - missing_bar_ratio,
        quality_score=quality_score,
        passed=passed,
        is_valid=not insufficient_data,
        invalid_reason="insufficient_data" if insufficient_data else None,
        issues=issues,
    )


def summarize_data_quality_failure(report: DataQualityReport) -> DataQualityFailureSummary:
    """Build a concise Memory Agent input from a failed quality report."""
    if report.passed:
        raise ValueError("Only failed data quality reports can be summarized as failures")

    error_issues = [
        issue for issue in report.issues if issue.severity == DataQualitySeverity.ERROR
    ]
    blocking_issues = error_issues or report.issues
    issue_codes = [issue.code for issue in blocking_issues]
    issue_fragments = [
        f"{issue.code}: {issue.count}" for issue in blocking_issues
    ]
    summary = (
        f"Dataset {report.symbol} {report.timeframe} from {report.source} failed "
        f"data quality validation. Quality score {report.quality_score:.3f}; "
        f"issues: {', '.join(issue_fragments)}."
    )

    return DataQualityFailureSummary(
        report_id=report.report_id,
        dataset_id=report.dataset_id,
        symbol=report.symbol,
        source=report.source,
        timeframe=report.timeframe,
        quality_score=report.quality_score,
        issue_codes=issue_codes,
        summary=summary,
        registry_reference=f"data_quality_reports/{report.report_id}",
    )


def _normalize_input(data: OHLCVBatch | Sequence[OHLCVBar]) -> tuple[list[OHLCVBar], OHLCVBatch]:
    if isinstance(data, OHLCVBatch):
        return list(data.bars), data

    bars = list(data)
    if not bars:
        raise ValueError("OHLCV quality validation requires at least one bar")

    first = bars[0]
    for bar in bars:
        if bar.symbol != first.symbol:
            raise ValueError("all bars must match the first bar symbol")
        if bar.source != first.source:
            raise ValueError("all bars must match the first bar source")
        if bar.timeframe != first.timeframe:
            raise ValueError("all bars must match the first bar timeframe")

    unique_bars = []
    seen_timestamps = set()
    for bar in sorted(bars, key=lambda item: item.timestamp):
        if bar.timestamp in seen_timestamps:
            continue
        seen_timestamps.add(bar.timestamp)
        unique_bars.append(bar)

    batch = OHLCVBatch(
        symbol=first.symbol,
        source=first.source,
        timeframe=first.timeframe,
        bars=unique_bars,
        exchange=first.exchange,
    )
    return bars, batch


def _timeframe_delta(timeframe: str) -> timedelta:
    quantity = int(timeframe[:-1])
    unit = timeframe[-1]
    if unit not in _TIMEFRAME_UNITS:
        raise ValueError(f"Unsupported OHLCV timeframe: {timeframe}")
    return timedelta(**{_TIMEFRAME_UNITS[unit]: quantity})


def _expected_timestamps(start: datetime, end: datetime, timeframe: str) -> list[datetime]:
    delta = _timeframe_delta(timeframe)
    timestamps = []
    current = start
    while current <= end:
        timestamps.append(current)
        current += delta
    return timestamps


def _count_abnormal_volume_spikes(bars: Sequence[OHLCVBar], multiplier: float) -> int:
    positive_volumes = sorted(bar.volume for bar in bars if bar.volume > 0)
    if len(positive_volumes) < 3:
        return 0
    midpoint = len(positive_volumes) // 2
    if len(positive_volumes) % 2:
        median = positive_volumes[midpoint]
    else:
        median = (positive_volumes[midpoint - 1] + positive_volumes[midpoint]) / 2
    if median <= 0:
        return 0
    return sum(1 for bar in bars if bar.volume > median * multiplier)


def _quality_score(
    *,
    expected_bar_count: int,
    missing_bars: int,
    duplicate_timestamps: int,
    abnormal_volume_count: int,
) -> float:
    if expected_bar_count == 0:
        return 0.0
    penalty = missing_bars + duplicate_timestamps + (0.25 * abnormal_volume_count)
    return max(0.0, round(1.0 - penalty / expected_bar_count, 6))
