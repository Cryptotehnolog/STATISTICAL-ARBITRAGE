"""Checkpoint smoke for data ingestion, validation, registry, and memory boundaries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from shutil import rmtree
from typing import Any
from uuid import uuid4

import pandas as pd
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from stat_arb.data_quality import OHLCVQualityConfig
from stat_arb.domain import DataQualityReport
from stat_arb.ingestion import CCXTOHLCVSource, OHLCVQualityError, fetch_validate_write_ohlcv
from stat_arb.memory import MemoryAgentService, write_data_quality_failure_memory
from stat_arb.storage import Base, DataQualityReportRecord, Dataset, persist_ohlcv_ingestion_result


@dataclass(frozen=True)
class CheckDataPipelineResult:
    """Human-readable checkpoint summary."""

    dataset_rows: int
    quality_report_rows: int
    parquet_rows: int
    memory_filename: str
    memory_document_ids: tuple[str, ...]


class FakeExchange:
    """Minimal CCXT-like exchange for deterministic checkpoint runs."""

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
        """Return deterministic OHLCV rows."""
        _ = (symbol, timeframe, since, limit, params)
        return self.rows


class FakeApeRAGClient:
    """Fake ApeRAG writer that proves MemoryAgentService is the write boundary."""

    def __init__(self) -> None:
        self.config = type("Config", (), {"agent_collection_title": "stat-arb-agent-memory"})()
        self.calls: list[dict[str, str]] = []

    def write_markdown_document(
        self,
        *,
        filename: str,
        content: str,
        collection_title: str | None = None,
        collection_id: str | None = None,
    ) -> list[str]:
        """Record a policy-approved write without calling ApeRAG."""
        self.calls.append(
            {
                "filename": filename,
                "content": content,
                "collection_title": collection_title or "",
                "collection_id": collection_id or "",
            }
        )
        return ["checkpoint-memory-doc"]


def _strict_quality_config() -> OHLCVQualityConfig:
    return OHLCVQualityConfig(
        max_missing_bar_ratio=0.0,
        max_abnormal_volume_ratio=0.0,
        volume_spike_multiplier=10.0,
    )


def run_checkpoint() -> CheckDataPipelineResult:
    """Run a deterministic end-to-end data pipeline checkpoint."""
    root = Path("data/test_tmp") / f"stat-arb-data-pipeline-{uuid4()}"
    parquet_root = root / "parquet"
    metadata_root = root / "metadata"
    try:
        engine = create_engine("sqlite:///:memory:", echo=False)

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn: Any, _connection_record: Any) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine)
        session = session_factory()
        try:
            passed_result = fetch_validate_write_ohlcv(
                CCXTOHLCVSource(
                    exchange_id="fake",
                    exchange=FakeExchange(
                        [
                            _row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC), 100.0),
                            _row(datetime(2024, 1, 1, 0, 5, tzinfo=UTC), 101.0),
                            _row(datetime(2024, 1, 1, 0, 10, tzinfo=UTC), 102.0),
                        ]
                    ),
                    sleep=lambda _: None,
                ),
                symbol="BTC/USDT",
                timeframe="5m",
                output_root=parquet_root,
                quality_config=_strict_quality_config(),
            )
            stored = persist_ohlcv_ingestion_result(
                session,
                passed_result,
                metadata_root,
                symbol_mapping={"BTC/USDT": "BTCUSDT"},
                extra_metadata={"checkpoint": "task-5"},
            )
            session.commit()

            _assert_sidecars(stored.metadata_path, stored.report_path, passed_result.parquet_paths)
            parquet_rows = len(pd.read_parquet(passed_result.parquet_paths[0]))

            failed_report = _failed_quality_report(parquet_root)
            memory_client = FakeApeRAGClient()
            memory_result = write_data_quality_failure_memory(
                MemoryAgentService(memory_client),  # type: ignore[arg-type]
                failed_report,
            )
            if not memory_client.calls:
                raise AssertionError("Memory Agent checkpoint did not write a failure summary")

            return CheckDataPipelineResult(
                dataset_rows=session.query(Dataset).count(),
                quality_report_rows=session.query(DataQualityReportRecord).count(),
                parquet_rows=parquet_rows,
                memory_filename=memory_result.filename,
                memory_document_ids=memory_result.document_ids,
            )
        finally:
            session.close()
            engine.dispose()
    finally:
        rmtree(root, ignore_errors=True)


def _row(timestamp: datetime, open_price: float) -> list[Any]:
    return [
        int(timestamp.timestamp() * 1000),
        open_price,
        open_price + 2.0,
        open_price - 1.0,
        open_price + 1.0,
        10.0,
    ]


def _assert_sidecars(
    metadata_path: Path,
    report_path: Path,
    parquet_paths: tuple[Path, ...],
) -> None:
    if not metadata_path.exists() or not report_path.exists():
        raise AssertionError("Expected metadata and quality report sidecars")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    expected_paths = [str(path) for path in parquet_paths]
    if metadata["parquet_paths"] != expected_paths:
        raise AssertionError("Metadata sidecar parquet paths mismatch")
    if report["parquet_paths"] != expected_paths:
        raise AssertionError("Quality report sidecar parquet paths mismatch")


def _failed_quality_report(parquet_root: Path) -> DataQualityReport:
    try:
        fetch_validate_write_ohlcv(
            CCXTOHLCVSource(
                exchange_id="fake",
                exchange=FakeExchange(
                    [
                        _row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC), 100.0),
                        _row(datetime(2024, 1, 1, 0, 10, tzinfo=UTC), 102.0),
                    ]
                ),
                sleep=lambda _: None,
            ),
            symbol="ETH/USDT",
            timeframe="5m",
            output_root=parquet_root,
            quality_config=_strict_quality_config(),
        )
    except OHLCVQualityError as exc:
        return exc.report
    raise AssertionError("Expected failed data-quality validation")


def main() -> int:
    """CLI entrypoint for the checkpoint script."""
    result = run_checkpoint()
    print("Data pipeline checkpoint OK")
    print(f"- registry datasets: {result.dataset_rows}")
    print(f"- registry quality reports: {result.quality_report_rows}")
    print(f"- parquet rows: {result.parquet_rows}")
    print(f"- memory write: {result.memory_filename} -> {', '.join(result.memory_document_ids)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
