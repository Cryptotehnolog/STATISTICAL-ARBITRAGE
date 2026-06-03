"""Unit tests for deterministic OHLCV resampling."""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stat_arb.data_quality import resample_ohlcv_batch
from stat_arb.domain import DatasetSource, OHLCVBar, OHLCVBatch


def _bar(index: int, *, start: datetime | None = None) -> OHLCVBar:
    base = start or datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    open_price = 100.0 + index
    return OHLCVBar(
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="1m",
        timestamp=base + timedelta(minutes=index),
        open=open_price,
        high=open_price + 1.0,
        low=open_price - 1.0,
        close=open_price + 0.5,
        volume=10.0 + index,
        exchange="binance",
    )


def _batch(count: int, *, start: datetime | None = None) -> OHLCVBatch:
    return OHLCVBatch(
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="1m",
        bars=[_bar(index, start=start) for index in range(count)],
        exchange="binance",
    )


def _five_minute_batch(count: int) -> OHLCVBatch:
    bars = [
        _bar(index, start=datetime(2024, 1, 1, 0, 0, tzinfo=UTC)).model_copy(
            update={
                "timeframe": "5m",
                "timestamp": datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
                + timedelta(minutes=5 * index),
            }
        )
        for index in range(count)
    ]
    return OHLCVBatch(
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="5m",
        bars=bars,
        exchange="binance",
    )


@st.composite
def _complete_one_minute_batches(draw) -> OHLCVBatch:
    window_count = draw(st.integers(min_value=1, max_value=8))
    bar_count = window_count * 5
    start_hour = draw(st.integers(min_value=0, max_value=23))
    start_minute = draw(st.sampled_from([0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55]))
    base_price = draw(st.floats(min_value=1.0, max_value=10_000.0, allow_nan=False, allow_infinity=False))
    step = draw(st.floats(min_value=0.01, max_value=10.0, allow_nan=False, allow_infinity=False))
    volumes = draw(
        st.lists(
            st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
            min_size=bar_count,
            max_size=bar_count,
        )
    )
    start = datetime(2024, 1, 1, start_hour, start_minute, tzinfo=UTC)
    bars: list[OHLCVBar] = []
    for index, volume in enumerate(volumes):
        open_price = base_price + (index * step)
        bars.append(
            OHLCVBar(
                symbol="BTC/USDT",
                source=DatasetSource.CCXT,
                timeframe="1m",
                timestamp=start + timedelta(minutes=index),
                open=open_price,
                high=open_price + step,
                low=max(0.01, open_price - step),
                close=open_price + (step / 2),
                volume=volume,
                exchange="binance",
            )
        )

    return OHLCVBatch(
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="1m",
        bars=bars,
        exchange="binance",
    )


def test_resample_ohlcv_batch_aggregates_ohlcv_deterministically() -> None:
    """Open, high, low, close, volume, and labels should follow deterministic rules."""
    result = resample_ohlcv_batch(_batch(10), "5m")

    assert result.timeframe == "5m"
    assert len(result.bars) == 2
    first = result.bars[0]
    assert first.timestamp == datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    assert first.open == 100.0
    assert first.high == 105.0
    assert first.low == 99.0
    assert first.close == 104.5
    assert first.volume == 60.0
    assert first.metadata["resampled_from"] == "1m"
    assert first.metadata["bars_in_window"] == 5


def test_resample_ohlcv_batch_drops_incomplete_windows_by_default() -> None:
    """Incomplete trailing windows should not become trusted aggregate bars by default."""
    result = resample_ohlcv_batch(_batch(7), "5m")

    assert len(result.bars) == 1
    assert result.bars[0].timestamp == datetime(2024, 1, 1, 0, 0, tzinfo=UTC)


def test_resample_ohlcv_batch_can_keep_partial_windows_explicitly() -> None:
    """Callers may keep partial windows when they want diagnostics or exploratory output."""
    result = resample_ohlcv_batch(_batch(7), "5m", require_complete_windows=False)

    assert len(result.bars) == 2
    assert result.bars[1].timestamp == datetime(2024, 1, 1, 0, 5, tzinfo=UTC)
    assert result.bars[1].metadata["bars_in_window"] == 2


def test_resample_ohlcv_batch_aligns_window_labels_to_utc_boundaries() -> None:
    """Window labels should be UTC starts even when input starts inside the window."""
    start = datetime(2024, 1, 1, 0, 2, tzinfo=UTC)
    result = resample_ohlcv_batch(
        _batch(3, start=start),
        "5m",
        require_complete_windows=False,
    )

    assert result.bars[0].timestamp == datetime(2024, 1, 1, 0, 0, tzinfo=UTC)


def test_resample_ohlcv_batch_rejects_finer_or_non_multiple_targets() -> None:
    """Resampling should only downsample to exact multiple timeframes."""
    batch = _batch(5)

    with pytest.raises(ValueError, match="coarser"):
        resample_ohlcv_batch(batch, "1m")

    with pytest.raises(ValueError, match="exact multiple"):
        resample_ohlcv_batch(_five_minute_batch(3), "7m")


def test_resample_ohlcv_batch_requires_at_least_one_output_window() -> None:
    """Strict resampling should fail if every window is incomplete."""
    with pytest.raises(ValueError, match="no complete"):
        resample_ohlcv_batch(_batch(4), "5m")


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(batch=_complete_one_minute_batches())
def test_resample_ohlcv_batch_is_idempotent_for_same_input(batch: OHLCVBatch) -> None:
    """Property 5: identical resampling inputs should always produce identical outputs."""
    first = resample_ohlcv_batch(batch, "5m")
    second = resample_ohlcv_batch(batch, "5m")

    assert second.model_dump(mode="json") == first.model_dump(mode="json")
