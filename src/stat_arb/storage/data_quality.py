"""Persistence helpers for OHLCV data quality reports."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from stat_arb.domain import AdjustmentMode, DataQualityReport
from stat_arb.ingestion import OHLCVIngestionResult
from stat_arb.storage.models import DataQualityReportRecord, Dataset


@dataclass(frozen=True)
class StoredOHLCVIngestionResult:
    """Database and sidecar records created for a validated OHLCV ingestion result."""

    dataset: Dataset
    quality_report: DataQualityReportRecord
    metadata_path: Path
    report_path: Path


def persist_ohlcv_ingestion_result(
    session: Session,
    result: OHLCVIngestionResult,
    metadata_root: Path | str,
    *,
    adjustment_mode: AdjustmentMode = AdjustmentMode.NONE,
    symbol_mapping: dict[str, str] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> StoredOHLCVIngestionResult:
    """Persist validated OHLCV dataset provenance and quality report in the registry."""
    if not result.quality_report.passed:
        raise ValueError("Only passed OHLCV ingestion results can be persisted as datasets")
    if not result.parquet_paths:
        raise ValueError("OHLCV ingestion result must include at least one parquet path")

    metadata_dir = _metadata_directory(metadata_root, result)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    dataset_id = str(result.batch.dataset_id)
    report_id = str(result.quality_report.report_id)
    metadata_path = metadata_dir / f"{dataset_id}.metadata.json"
    report_path = metadata_dir / f"{report_id}.quality.json"

    parquet_paths = [str(path) for path in result.parquet_paths]
    metadata_payload = {
        "dataset_id": dataset_id,
        "quality_report_id": report_id,
        "symbol": result.batch.symbol,
        "source": result.batch.source,
        "timeframe": result.batch.timeframe,
        "exchange": result.batch.exchange,
        "adjustment_mode": adjustment_mode,
        "downloaded_at": datetime.now(UTC).isoformat(),
        "symbol_mapping": symbol_mapping or {},
        "parquet_paths": parquet_paths,
        "quality_report_path": str(report_path),
        "extra_metadata": extra_metadata or {},
    }
    report_payload = result.quality_report.model_dump(mode="json")
    report_payload["parquet_paths"] = parquet_paths
    report_payload["metadata_path"] = str(metadata_path)

    _write_json(metadata_path, metadata_payload)
    _write_json(report_path, report_payload)

    dataset = Dataset(
        dataset_id=dataset_id,
        symbol=result.batch.symbol,
        source=result.batch.source,
        timeframe=result.batch.timeframe,
        start_date=_naive_utc(result.quality_report.start_date),
        end_date=_naive_utc(result.quality_report.end_date),
        bar_count=result.quality_report.bar_count,
        missing_bars=result.quality_report.missing_bars,
        outlier_count=result.quality_report.outlier_count,
        quality_score=result.quality_report.quality_score,
        adjustment_mode=adjustment_mode,
        file_path=parquet_paths[0],
        extra_metadata=metadata_payload,
    )
    quality_report = _quality_report_record(result.quality_report, report_path)

    session.add(dataset)
    session.add(quality_report)
    return StoredOHLCVIngestionResult(
        dataset=dataset,
        quality_report=quality_report,
        metadata_path=metadata_path,
        report_path=report_path,
    )


def _quality_report_record(
    report: DataQualityReport,
    report_path: Path,
) -> DataQualityReportRecord:
    return DataQualityReportRecord(
        report_id=str(report.report_id),
        dataset_id=str(report.dataset_id),
        symbol=report.symbol,
        source=report.source,
        timeframe=report.timeframe,
        start_date=_naive_utc(report.start_date),
        end_date=_naive_utc(report.end_date),
        bar_count=report.bar_count,
        expected_bar_count=report.expected_bar_count,
        missing_bars=report.missing_bars,
        duplicate_timestamps=report.duplicate_timestamps,
        outlier_count=report.outlier_count,
        zero_price_count=report.zero_price_count,
        impossible_candle_count=report.impossible_candle_count,
        abnormal_volume_count=report.abnormal_volume_count,
        timezone_normalized=report.timezone_normalized,
        alignment_score=report.alignment_score,
        quality_score=report.quality_score,
        passed=report.passed,
        issues=[issue.model_dump(mode="json") for issue in report.issues],
        report_path=str(report_path),
        generated_at=_naive_utc(report.generated_at),
    )


def _metadata_directory(metadata_root: Path | str, result: OHLCVIngestionResult) -> Path:
    exchange = result.batch.exchange or "unknown"
    return (
        Path(metadata_root)
        / "source=ccxt"
        / f"exchange={_safe_partition_value(exchange)}"
        / f"symbol={_safe_partition_value(result.batch.symbol)}"
        / f"timeframe={_safe_partition_value(result.batch.timeframe)}"
    )


def _safe_partition_value(value: str) -> str:
    return value.strip().replace("/", "_").replace(":", "_").replace(" ", "_")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
