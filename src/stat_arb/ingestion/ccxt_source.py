"""CCXT OHLCV data source adapter.

This module intentionally handles only ingestion and raw parquet persistence.
Quality validation, registry writes, and Memory Agent summaries are separate tasks.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

import pandas as pd

from stat_arb.domain import DatasetSource, OHLCVBar, OHLCVBatch


class CCXTExchange(Protocol):
    """Small protocol for the CCXT exchange methods used by this adapter."""

    id: str

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: int | None = None,
        limit: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[list[Any]]:
        """Fetch OHLCV rows in CCXT format."""


def _datetime_to_milliseconds(value: datetime | None) -> int | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return int(value.astimezone(UTC).timestamp() * 1000)


def _timestamp_from_ccxt(value: Any) -> datetime:
    return datetime.fromtimestamp(int(value) / 1000, tz=UTC)


def _safe_partition_value(value: str) -> str:
    return value.strip().replace("/", "_").replace(":", "_").replace(" ", "_")


def _batch_to_dataframe(batch: OHLCVBatch, bars: Iterable[OHLCVBar]) -> pd.DataFrame:
    rows = [
        {
            "dataset_id": str(batch.dataset_id),
            "timestamp": bar.timestamp,
            "symbol": bar.symbol,
            "source": bar.source,
            "timeframe": bar.timeframe,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "exchange": bar.exchange or batch.exchange,
        }
        for bar in bars
    ]
    return pd.DataFrame.from_records(rows)


def write_ohlcv_batch_to_parquet(batch: OHLCVBatch, output_root: Path | str) -> list[Path]:
    """Persist an OHLCV batch as parquet files partitioned by exchange, symbol, timeframe, and date."""
    root = Path(output_root)
    exchange = batch.exchange or "unknown"
    written_paths: list[Path] = []

    bars_by_date: dict[str, list[OHLCVBar]] = {}
    for bar in batch.bars:
        date_key = bar.timestamp.date().isoformat()
        bars_by_date.setdefault(date_key, []).append(bar)

    for date_key, bars in sorted(bars_by_date.items()):
        partition_dir = (
            root
            / "source=ccxt"
            / f"exchange={_safe_partition_value(exchange)}"
            / f"symbol={_safe_partition_value(batch.symbol)}"
            / f"timeframe={_safe_partition_value(batch.timeframe)}"
            / f"date={date_key}"
        )
        partition_dir.mkdir(parents=True, exist_ok=True)
        file_path = partition_dir / f"{batch.dataset_id}.parquet"

        dataframe = _batch_to_dataframe(batch, bars)
        dataframe.to_parquet(file_path, index=False)
        written_paths.append(file_path)

    return written_paths


class CCXTOHLCVSource:
    """Fetch OHLCV bars from a CCXT exchange and normalize them into domain contracts."""

    def __init__(
        self,
        exchange_id: str = "bybit",
        exchange: CCXTExchange | None = None,
        *,
        max_retries: int = 3,
        retry_base_seconds: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if max_retries < 1:
            raise ValueError("max_retries must be at least 1")
        if retry_base_seconds < 0:
            raise ValueError("retry_base_seconds must be non-negative")

        self.exchange_id = exchange_id.strip().lower()
        self.exchange = exchange or self._create_exchange(self.exchange_id)
        self.max_retries = max_retries
        self.retry_base_seconds = retry_base_seconds
        self.sleep = sleep

    @staticmethod
    def _create_exchange(exchange_id: str) -> CCXTExchange:
        import ccxt  # noqa: PLC0415

        exchange_class = getattr(ccxt, exchange_id, None)
        if exchange_class is None:
            raise ValueError(f"Unsupported CCXT exchange: {exchange_id}")
        return cast(CCXTExchange, exchange_class({"enableRateLimit": True}))

    def fetch_ohlcv_batch(
        self,
        symbol: str,
        timeframe: str,
        *,
        since: datetime | None = None,
        limit: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> OHLCVBatch:
        """Fetch and normalize OHLCV rows from the configured exchange."""
        raw_rows = self._fetch_with_retries(
            symbol=symbol,
            timeframe=timeframe,
            since_ms=_datetime_to_milliseconds(since),
            limit=limit,
            params=params or {},
        )
        exchange_id = getattr(self.exchange, "id", self.exchange_id)

        bars = [
            OHLCVBar(
                symbol=symbol,
                source=DatasetSource.CCXT,
                timeframe=timeframe,
                timestamp=_timestamp_from_ccxt(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
                exchange=exchange_id,
            )
            for row in raw_rows
        ]

        return OHLCVBatch(
            symbol=symbol,
            source=DatasetSource.CCXT,
            timeframe=timeframe,
            bars=bars,
            exchange=exchange_id,
        )

    def fetch_and_write_parquet(
        self,
        symbol: str,
        timeframe: str,
        output_root: Path | str,
        *,
        since: datetime | None = None,
        limit: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> tuple[OHLCVBatch, list[Path]]:
        """Fetch a batch and persist it as partitioned parquet files."""
        batch = self.fetch_ohlcv_batch(
            symbol=symbol,
            timeframe=timeframe,
            since=since,
            limit=limit,
            params=params,
        )
        return batch, write_ohlcv_batch_to_parquet(batch, output_root)

    def _fetch_with_retries(
        self,
        *,
        symbol: str,
        timeframe: str,
        since_ms: int | None,
        limit: int | None,
        params: dict[str, Any],
    ) -> list[list[Any]]:
        last_error: Exception | None = None

        for attempt in range(1, self.max_retries + 1):
            try:
                return self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe=timeframe,
                    since=since_ms,
                    limit=limit,
                    params=params,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == self.max_retries:
                    break
                self.sleep(self.retry_base_seconds * (2 ** (attempt - 1)))

        raise RuntimeError(
            f"Failed to fetch OHLCV from {self.exchange_id} after {self.max_retries} attempts"
        ) from last_error
