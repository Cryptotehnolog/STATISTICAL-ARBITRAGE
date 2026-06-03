"""Deterministic OHLCV resampling helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from stat_arb.domain import OHLCVBar, OHLCVBatch

_TIMEFRAME_UNITS = {
    "m": "minutes",
    "h": "hours",
    "d": "days",
    "w": "weeks",
}


def resample_ohlcv_batch(
    batch: OHLCVBatch,
    target_timeframe: str,
    *,
    require_complete_windows: bool = True,
) -> OHLCVBatch:
    """Aggregate an OHLCV batch into a coarser deterministic timeframe."""
    source_delta = _timeframe_delta(batch.timeframe)
    target_delta = _timeframe_delta(target_timeframe)
    if target_delta <= source_delta:
        raise ValueError("target_timeframe must be coarser than the source timeframe")
    if _delta_seconds(target_delta) % _delta_seconds(source_delta) != 0:
        raise ValueError("target_timeframe must be an exact multiple of the source timeframe")

    expected_bars_per_window = _delta_seconds(target_delta) // _delta_seconds(source_delta)
    windows: dict[datetime, list[OHLCVBar]] = defaultdict(list)
    for bar in batch.bars:
        window_start = _floor_timestamp(bar.timestamp, target_delta)
        windows[window_start].append(bar)

    resampled_bars: list[OHLCVBar] = []
    for window_start in sorted(windows):
        bars = sorted(windows[window_start], key=lambda item: item.timestamp)
        if require_complete_windows and len(bars) != expected_bars_per_window:
            continue
        resampled_bars.append(
            OHLCVBar(
                symbol=batch.symbol,
                source=batch.source,
                timeframe=target_timeframe,
                timestamp=window_start,
                open=bars[0].open,
                high=max(bar.high for bar in bars),
                low=min(bar.low for bar in bars),
                close=bars[-1].close,
                volume=sum(bar.volume for bar in bars),
                exchange=batch.exchange,
                metadata={
                    "resampled_from": batch.timeframe,
                    "bars_in_window": len(bars),
                    "source_dataset_id": str(batch.dataset_id),
                },
            )
        )

    if not resampled_bars:
        raise ValueError("resampling produced no complete OHLCV windows")

    return OHLCVBatch(
        symbol=batch.symbol,
        source=batch.source,
        timeframe=target_timeframe,
        bars=resampled_bars,
        exchange=batch.exchange,
    )


def _timeframe_delta(timeframe: str) -> timedelta:
    quantity = int(timeframe[:-1])
    unit = timeframe[-1]
    if unit not in _TIMEFRAME_UNITS:
        raise ValueError(f"Unsupported OHLCV timeframe: {timeframe}")
    return timedelta(**{_TIMEFRAME_UNITS[unit]: quantity})


def _delta_seconds(delta: timedelta) -> int:
    return int(delta.total_seconds())


def _floor_timestamp(timestamp: datetime, window: timedelta) -> datetime:
    normalized = timestamp
    if normalized.tzinfo is None:
        normalized = normalized.replace(tzinfo=UTC)
    normalized = normalized.astimezone(UTC)
    epoch = datetime(1970, 1, 1, tzinfo=UTC)
    elapsed_seconds = int((normalized - epoch).total_seconds())
    window_seconds = _delta_seconds(window)
    floored_seconds = elapsed_seconds - (elapsed_seconds % window_seconds)
    return epoch + timedelta(seconds=floored_seconds)
