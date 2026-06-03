"""Unit tests for deterministic OHLCV pair alignment."""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stat_arb.data_quality import align_ohlcv_pair
from stat_arb.domain import DatasetSource, OHLCVBar, OHLCVBatch


def _bar(symbol: str, index: int) -> OHLCVBar:
    open_price = 100.0 + index
    return OHLCVBar(
        symbol=symbol,
        source=DatasetSource.CCXT,
        timeframe="5m",
        timestamp=datetime(2024, 1, 1, tzinfo=UTC) + timedelta(minutes=5 * index),
        open=open_price,
        high=open_price + 1.0,
        low=open_price - 1.0,
        close=open_price + 0.5,
        volume=10.0 + index,
        exchange="binance",
    )


def _batch(symbol: str, indexes: list[int]) -> OHLCVBatch:
    return OHLCVBatch(
        symbol=symbol,
        source=DatasetSource.CCXT,
        timeframe="5m",
        bars=[_bar(symbol, index) for index in indexes],
        exchange="binance",
    )


def test_align_ohlcv_pair_keeps_only_shared_timestamps() -> None:
    """Partial overlap should be trimmed to identical timestamps in both assets."""
    result = align_ohlcv_pair(_batch("BTC/USDT", [0, 1, 2, 3]), _batch("ETH/USDT", [1, 2, 4]))

    assert result.bar_count == 2
    assert result.dropped_asset_a_bars == 2
    assert result.dropped_asset_b_bars == 1
    assert [bar.timestamp for bar in result.asset_a.bars] == list(result.aligned_timestamps)
    assert [bar.timestamp for bar in result.asset_b.bars] == list(result.aligned_timestamps)
    assert result.asset_a.bars[0].metadata["paired_symbol"] == "ETH/USDT"
    assert result.asset_b.bars[0].metadata["paired_symbol"] == "BTC/USDT"


def test_align_ohlcv_pair_can_require_full_overlap() -> None:
    """Strict callers can reject pairs with missing timestamps on either side."""
    with pytest.raises(ValueError, match="full timestamp overlap"):
        align_ohlcv_pair(
            _batch("BTC/USDT", [0, 1, 2]),
            _batch("ETH/USDT", [1, 2]),
            require_full_overlap=True,
        )


def test_align_ohlcv_pair_rejects_incompatible_or_empty_pairs() -> None:
    """Alignment should fail early for invalid pair boundaries."""
    with pytest.raises(ValueError, match="different symbols"):
        align_ohlcv_pair(_batch("BTC/USDT", [0]), _batch("BTC/USDT", [0]))

    with pytest.raises(ValueError, match="no overlapping timestamps"):
        align_ohlcv_pair(_batch("BTC/USDT", [0]), _batch("ETH/USDT", [1]))

    with pytest.raises(ValueError, match="min_overlap_ratio"):
        align_ohlcv_pair(
            _batch("BTC/USDT", [0, 1, 2, 3]),
            _batch("ETH/USDT", [0]),
            min_overlap_ratio=0.5,
        )


@st.composite
def _overlapping_index_sets(draw) -> tuple[list[int], list[int]]:
    common = draw(st.sets(st.integers(min_value=0, max_value=40), min_size=1, max_size=20))
    extra_a = draw(st.sets(st.integers(min_value=41, max_value=80), min_size=0, max_size=10))
    extra_b = draw(st.sets(st.integers(min_value=81, max_value=120), min_size=0, max_size=10))
    return sorted(common | extra_a), sorted(common | extra_b)


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(index_sets=_overlapping_index_sets())
def test_align_ohlcv_pair_has_consistent_timestamps(index_sets: tuple[list[int], list[int]]) -> None:
    """Property 6: aligned timestamps should exist in both output series."""
    indexes_a, indexes_b = index_sets
    result = align_ohlcv_pair(_batch("BTC/USDT", indexes_a), _batch("ETH/USDT", indexes_b))

    timestamps_a = tuple(bar.timestamp for bar in result.asset_a.bars)
    timestamps_b = tuple(bar.timestamp for bar in result.asset_b.bars)

    assert timestamps_a == result.aligned_timestamps
    assert timestamps_b == result.aligned_timestamps
    assert set(result.aligned_timestamps).issubset({_bar("BTC/USDT", index).timestamp for index in indexes_a})
    assert set(result.aligned_timestamps).issubset({_bar("ETH/USDT", index).timestamp for index in indexes_b})
