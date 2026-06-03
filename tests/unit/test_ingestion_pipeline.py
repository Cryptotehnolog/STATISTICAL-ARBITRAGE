"""Unit tests for service-level OHLCV ingestion pipeline."""

from datetime import UTC, datetime
from pathlib import Path
from shutil import rmtree
from typing import Any
from uuid import uuid4

import pandas as pd
import pytest

from stat_arb.data_quality import OHLCVQualityConfig
from stat_arb.ingestion import CCXTOHLCVSource, OHLCVQualityError, fetch_validate_write_ohlcv


class FakeExchange:
    """Minimal fake exchange for pipeline tests."""

    id = "fake"

    def __init__(self, rows: list[list[Any]]) -> None:
        self.rows = rows

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: int | None = None,
        limit: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[list[Any]]:
        return self.rows


def _row(timestamp: datetime, open_price: float = 100.0, volume: float = 10.0) -> list[Any]:
    return [
        int(timestamp.timestamp() * 1000),
        open_price,
        open_price + 2.0,
        open_price - 1.0,
        open_price + 1.0,
        volume,
    ]


def test_fetch_validate_write_ohlcv_persists_passed_batch() -> None:
    """Passed quality reports should allow parquet persistence."""
    output_root = Path("data/test_tmp") / f"ingestion-pipeline-pass-{uuid4()}"
    source = CCXTOHLCVSource(
        exchange_id="fake",
        exchange=FakeExchange(
            [
                _row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC), 100.0),
                _row(datetime(2024, 1, 1, 0, 5, tzinfo=UTC), 101.0),
            ]
        ),
        sleep=lambda _: None,
    )

    try:
        result = fetch_validate_write_ohlcv(
            source,
            symbol="BTC/USDT",
            timeframe="5m",
            output_root=output_root,
        )

        assert result.quality_report.passed is True
        assert result.quality_report.missing_bars == 0
        assert len(result.parquet_paths) == 1
        dataframe = pd.read_parquet(result.parquet_paths[0])
        assert dataframe["symbol"].tolist() == ["BTC/USDT", "BTC/USDT"]
    finally:
        rmtree(output_root, ignore_errors=True)


def test_fetch_validate_write_ohlcv_does_not_persist_failed_batch() -> None:
    """Failed quality reports should return diagnostics without writing parquet."""
    output_root = Path("data/test_tmp") / f"ingestion-pipeline-fail-{uuid4()}"
    source = CCXTOHLCVSource(
        exchange_id="fake",
        exchange=FakeExchange(
            [
                _row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC), 100.0),
                _row(datetime(2024, 1, 1, 0, 10, tzinfo=UTC), 102.0),
            ]
        ),
        sleep=lambda _: None,
    )

    with pytest.raises(OHLCVQualityError) as exc_info:
        fetch_validate_write_ohlcv(
            source,
            symbol="ETH/USDT",
            timeframe="5m",
            output_root=output_root,
        )

    assert exc_info.value.report.passed is False
    assert exc_info.value.report.missing_bars == 1
    assert not output_root.exists()


def test_fetch_validate_write_ohlcv_accepts_quality_thresholds() -> None:
    """Quality thresholds should control whether small gaps block persistence."""
    output_root = Path("data/test_tmp") / f"ingestion-pipeline-threshold-{uuid4()}"
    source = CCXTOHLCVSource(
        exchange_id="fake",
        exchange=FakeExchange(
            [
                _row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC), 100.0),
                _row(datetime(2024, 1, 1, 0, 10, tzinfo=UTC), 102.0),
            ]
        ),
        sleep=lambda _: None,
    )

    try:
        result = fetch_validate_write_ohlcv(
            source,
            symbol="ETH/USDT",
            timeframe="5m",
            output_root=output_root,
            quality_config=OHLCVQualityConfig(max_missing_bar_ratio=0.5),
        )

        assert result.quality_report.passed is True
        assert result.quality_report.issues[0].code == "missing_bars"
        assert len(result.parquet_paths) == 1
    finally:
        rmtree(output_root, ignore_errors=True)
