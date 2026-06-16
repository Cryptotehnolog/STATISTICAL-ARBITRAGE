"""Unit tests for durable data quality report persistence."""

import json
from datetime import UTC, datetime
from pathlib import Path
from shutil import rmtree
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.data_quality import OHLCVQualityConfig
from stat_arb.domain import (
    AdjustmentMode,
    DataQualityIssue,
    DataQualityReport,
    DataQualitySeverity,
    DatasetSource,
)
from stat_arb.ingestion import (
    CCXTOHLCVSource,
    OHLCVIngestionResult,
    OHLCVQualityError,
    fetch_validate_write_ohlcv,
)
from stat_arb.storage import (
    Base,
    DataQualityReportRecord,
    Dataset,
    ensure_sqlite_registry_schema,
    persist_ohlcv_ingestion_result,
)
from stat_arb.storage.data_quality import _quality_report_record


def _strict_quality_config() -> OHLCVQualityConfig:
    return OHLCVQualityConfig(
        max_missing_bar_ratio=0.0,
        max_abnormal_volume_ratio=0.0,
        volume_spike_multiplier=10.0,
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
    try:
        yield db_session
    finally:
        db_session.close()
        engine.dispose()
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
            quality_config=_strict_quality_config(),
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
                quality_config=_strict_quality_config(),
            )

        assert session.query(Dataset).count() == 0
        assert session.query(DataQualityReportRecord).count() == 0
        assert not metadata_root.exists()
    finally:
        rmtree(output_root, ignore_errors=True)
        rmtree(metadata_root, ignore_errors=True)


def test_persist_ohlcv_ingestion_result_rejects_raw_equity_adjustments(session: Session) -> None:
    """Registry persistence should not bypass equity adjustment policy."""
    output_root = Path("data/test_tmp") / f"storage-dq-equity-{uuid4()}"
    metadata_root = Path("data/test_tmp") / f"storage-dq-equity-meta-{uuid4()}"
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
            symbol="MSFT",
            timeframe="5m",
            output_root=output_root,
            quality_config=_strict_quality_config(),
        )
        equity_batch = ingestion_result.batch.model_copy(update={"source": DatasetSource.ALPACA})
        equity_report = ingestion_result.quality_report.model_copy(
            update={"source": DatasetSource.ALPACA}
        )
        equity_result = OHLCVIngestionResult(
            batch=equity_batch,
            quality_report=equity_report,
            parquet_paths=ingestion_result.parquet_paths,
        )

        with pytest.raises(ValueError, match="equity datasets require split_dividend"):
            persist_ohlcv_ingestion_result(
                session,
                equity_result,
                metadata_root,
                adjustment_mode=AdjustmentMode.NONE,
            )
        assert session.query(Dataset).count() == 0
    finally:
        rmtree(output_root, ignore_errors=True)
        rmtree(metadata_root, ignore_errors=True)


def test_quality_report_record_preserves_invalid_diagnostic_state() -> None:
    """Registry records should preserve insufficient-data diagnostic status."""
    timestamp = datetime(2024, 1, 1, tzinfo=UTC)
    report = DataQualityReport(
        dataset_id=uuid4(),
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="5m",
        start_date=timestamp,
        end_date=timestamp,
        bar_count=1,
        expected_bar_count=1,
        timezone_normalized=True,
        quality_score=0.0,
        passed=False,
        is_valid=False,
        invalid_reason="insufficient_data",
        issues=[
            DataQualityIssue(
                code="insufficient_data",
                severity=DataQualitySeverity.ERROR,
                message="A single OHLCV bar is diagnostic only.",
            )
        ],
    )

    record = _quality_report_record(report, Path("quality.json"))

    assert record.passed is False
    assert record.is_valid is False
    assert record.invalid_reason == "insufficient_data"


def test_ensure_sqlite_registry_schema_adds_data_quality_diagnostic_columns() -> None:
    """Existing SQLite registries should gain diagnostic columns without data loss."""
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE data_quality_reports (
                    report_id VARCHAR(36) PRIMARY KEY,
                    dataset_id VARCHAR(36) NOT NULL,
                    symbol VARCHAR(50) NOT NULL,
                    source VARCHAR(50) NOT NULL,
                    timeframe VARCHAR(10) NOT NULL,
                    start_date DATETIME NOT NULL,
                    end_date DATETIME NOT NULL,
                    bar_count INTEGER NOT NULL,
                    expected_bar_count INTEGER NOT NULL,
                    timezone_normalized BOOLEAN NOT NULL,
                    alignment_score FLOAT NOT NULL,
                    quality_score FLOAT NOT NULL,
                    passed BOOLEAN NOT NULL,
                    report_path VARCHAR(500) NOT NULL,
                    generated_at DATETIME NOT NULL
                )
                """
            )
        )

    ensure_sqlite_registry_schema(engine)

    with engine.connect() as connection:
        columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(data_quality_reports)"))
        }

    assert "is_valid" in columns
    assert "invalid_reason" in columns
