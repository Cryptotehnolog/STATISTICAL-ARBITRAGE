"""Unit tests for CCXT OHLCV ingestion."""

from datetime import UTC, datetime
from pathlib import Path
from shutil import rmtree
from typing import Any
from uuid import uuid4

import pandas as pd
import pytest

from stat_arb.domain import DatasetSource, OHLCVBar, OHLCVBatch
from stat_arb.ingestion import CCXTOHLCVSource, write_ohlcv_batch_to_parquet


class FakeExchange:
    """Minimal fake CCXT exchange for deterministic unit tests."""

    id = "fake"

    def __init__(self, rows: list[list[Any]], failures_before_success: int = 0) -> None:
        self.rows = rows
        self.failures_before_success = failures_before_success
        self.calls: list[dict[str, Any]] = []

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: int | None = None,
        limit: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[list[Any]]:
        self.calls.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "since": since,
                "limit": limit,
                "params": params,
            }
        )
        if len(self.calls) <= self.failures_before_success:
            raise TimeoutError("temporary exchange timeout")
        return self.rows


def _row(timestamp: datetime, open_price: float = 100.0) -> list[Any]:
    return [
        int(timestamp.timestamp() * 1000),
        open_price,
        open_price + 2.0,
        open_price - 1.0,
        open_price + 1.0,
        10.0,
    ]


def test_ccxt_source_fetches_and_normalizes_ohlcv_batch() -> None:
    """CCXT rows should become normalized OHLCV domain contracts."""
    exchange = FakeExchange(
        rows=[
            _row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC), 100.0),
            _row(datetime(2024, 1, 1, 0, 5, tzinfo=UTC), 101.0),
        ]
    )
    source = CCXTOHLCVSource(exchange_id="fake", exchange=exchange, sleep=lambda _: None)

    batch = source.fetch_ohlcv_batch(
        " btc/usdt ",
        "5m",
        since=datetime(2024, 1, 1, tzinfo=UTC),
        limit=2,
        params={"price": "mark"},
    )

    assert batch.symbol == "BTC/USDT"
    assert batch.source == DatasetSource.CCXT
    assert batch.exchange == "fake"
    assert len(batch.bars) == 2
    assert batch.bars[0].timestamp == datetime(2024, 1, 1, 0, 0, tzinfo=UTC)
    assert exchange.calls == [
        {
            "symbol": " btc/usdt ",
            "timeframe": "5m",
            "since": 1704067200000,
            "limit": 2,
            "params": {"price": "mark"},
        }
    ]


def test_ccxt_source_retries_transient_fetch_errors() -> None:
    """Transient exchange failures should retry before surfacing an error."""
    exchange = FakeExchange(
        rows=[_row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC))],
        failures_before_success=2,
    )
    sleeps: list[float] = []
    source = CCXTOHLCVSource(
        exchange_id="fake",
        exchange=exchange,
        max_retries=3,
        retry_base_seconds=0.5,
        sleep=sleeps.append,
    )

    batch = source.fetch_ohlcv_batch("ETH/USDT", "15m")

    assert len(batch.bars) == 1
    assert len(exchange.calls) == 3
    assert sleeps == [0.5, 1.0]


def test_ccxt_source_raises_after_retry_exhaustion() -> None:
    """Permanent exchange failures should include retry context."""
    exchange = FakeExchange(
        rows=[_row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC))],
        failures_before_success=3,
    )
    source = CCXTOHLCVSource(
        exchange_id="fake",
        exchange=exchange,
        max_retries=2,
        sleep=lambda _: None,
    )

    with pytest.raises(RuntimeError, match="after 2 attempts"):
        source.fetch_ohlcv_batch("ETH/USDT", "15m")


def test_write_ohlcv_batch_to_parquet_partitions_by_date() -> None:
    """Raw OHLCV parquet files should be partitioned by symbol, timeframe, and date."""
    output_root = Path("data/test_tmp") / f"ccxt-source-{uuid4()}"
    bars = [
        OHLCVBar(
            symbol="BTC/USDT",
            source=DatasetSource.CCXT,
            timeframe="5m",
            timestamp=datetime(2024, 1, 1, 23, 55, tzinfo=UTC),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1.0,
            exchange="binance",
        ),
        OHLCVBar(
            symbol="BTC/USDT",
            source=DatasetSource.CCXT,
            timeframe="5m",
            timestamp=datetime(2024, 1, 2, 0, 0, tzinfo=UTC),
            open=101.0,
            high=102.0,
            low=100.0,
            close=101.5,
            volume=2.0,
            exchange="binance",
        ),
    ]
    batch = OHLCVBatch(
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="5m",
        bars=bars,
        exchange="binance",
    )

    try:
        paths = write_ohlcv_batch_to_parquet(batch, output_root)

        assert len(paths) == 2
        assert paths[0].parent.as_posix().endswith(
            "source=ccxt/exchange=binance/symbol=BTC_USDT/timeframe=5m/date=2024-01-01"
        )
        assert paths[1].parent.as_posix().endswith(
            "source=ccxt/exchange=binance/symbol=BTC_USDT/timeframe=5m/date=2024-01-02"
        )

        dataframe = pd.read_parquet(paths[0])
        assert dataframe.to_dict(orient="records")[0]["symbol"] == "BTC/USDT"
        assert dataframe.to_dict(orient="records")[0]["source"] == "ccxt"
    finally:
        rmtree(output_root, ignore_errors=True)
