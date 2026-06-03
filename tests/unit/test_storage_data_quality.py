"""Unit tests for durable data quality report persistence."""

import json
from datetime import UTC, datetime
from pathlib import Path
from shutil import rmtree
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.ingestion import CCXTOHLCVSource, OHLCVQualityError, fetch_validate_write_ohlcv
from stat_arb.storage import (
    Base,
    DataQualityReportRecord,
    Dataset,
    persist_ohlcv_ingestion_result,
)


class FakeExchange:
    """Minimal fake exchange for registry persistence tests."""

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


@pytest.fixture
def session() -> Session:
    """Create an in-memory SQLite session with registry schema."""
    engine = create_engine("sqlite:///:memory:", echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()
    yield db_session
    db_session.close()
    engine.dispose()


def _row(timestamp: datetime, open_price: float = 100.0) -> list[Any]:
    return [
        int(timestamp.timestamp() * 1000),
        open_price,
        open_price + 2.0,
        open_price - 1.0,
        open_price + 1.0,
        10.0,
    ]


def test_persist_ohlcv_ingestion_result_writes_registry_and_sidecars(session: Session) -> None:
    """Validated ingestion output should become durable registry rows and JSON sidecars."""
    output_root = Path("data/test_tmp") / f"storage-dq-parquet-{uuid4()}"
    metadata_root = Path("data/test_tmp") / f"storage-dq-metadata-{uuid4()}"
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
        ingestion_result = fetch_validate_write_ohlcv(
            source,
            symbol="BTC/USDT",
            timeframe="5m",
            output_root=output_root,
        )
        stored = persist_ohlcv_ingestion_result(
            session,
            ingestion_result,
            metadata_root,
            symbol_mapping={"BTC/USDT": "BTCUSDT"},
            extra_metadata={"request_id": "unit-test"},
        )
        session.commit()

        dataset = session.query(Dataset).one()
        report = session.query(DataQualityReportRecord).one()

        assert dataset.dataset_id == str(ingestion_result.batch.dataset_id)
        assert dataset.quality_score == 1.0
        assert dataset.extra_metadata["symbol_mapping"] == {"BTC/USDT": "BTCUSDT"}
        assert dataset.extra_metadata["extra_metadata"] == {"request_id": "unit-test"}
        assert report.dataset_id == dataset.dataset_id
        assert report.report_id == str(ingestion_result.quality_report.report_id)
        assert report.passed is True
        assert report.issues == []
        assert stored.metadata_path.exists()
        assert stored.report_path.exists()
        metadata_payload = json.loads(stored.metadata_path.read_text(encoding="utf-8"))
        report_payload = json.loads(stored.report_path.read_text(encoding="utf-8"))

        assert metadata_payload["dataset_id"] == dataset.dataset_id
        assert metadata_payload["quality_report_id"] == report.report_id
        assert metadata_payload["symbol_mapping"] == {"BTC/USDT": "BTCUSDT"}
        assert metadata_payload["parquet_paths"] == [str(path) for path in ingestion_result.parquet_paths]
        assert metadata_payload["quality_report_path"] == str(stored.report_path)
        assert report_payload["report_id"] == report.report_id
        assert report_payload["metadata_path"] == str(stored.metadata_path)
        assert report_payload["parquet_paths"] == [str(path) for path in ingestion_result.parquet_paths]
    finally:
        rmtree(output_root, ignore_errors=True)
        rmtree(metadata_root, ignore_errors=True)


def test_persist_ohlcv_ingestion_result_requires_passing_quality(session: Session) -> None:
    """Failed quality should be rejected before registry dataset persistence."""
    output_root = Path("data/test_tmp") / f"storage-dq-failed-{uuid4()}"
    metadata_root = Path("data/test_tmp") / f"storage-dq-failed-meta-{uuid4()}"
    source = CCXTOHLCVSource(
        exchange_id="fake",
        exchange=FakeExchange(
            [
                _row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC), 100.0),
                _row(datetime(2024, 1, 1, 0, 10, tzinfo=UTC), 101.0),
            ]
        ),
        sleep=lambda _: None,
    )

    try:
        with pytest.raises(OHLCVQualityError):
            fetch_validate_write_ohlcv(
                source,
                symbol="ETH/USDT",
                timeframe="5m",
                output_root=output_root,
            )

        assert session.query(Dataset).count() == 0
        assert session.query(DataQualityReportRecord).count() == 0
        assert not metadata_root.exists()
    finally:
        rmtree(output_root, ignore_errors=True)
        rmtree(metadata_root, ignore_errors=True)
