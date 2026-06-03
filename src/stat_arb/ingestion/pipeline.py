"""Service-level OHLCV ingestion pipeline boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from stat_arb.data_quality import OHLCVQualityConfig, validate_ohlcv_batch
from stat_arb.domain import DataQualityReport, OHLCVBatch
from stat_arb.ingestion.ccxt_source import CCXTOHLCVSource, write_ohlcv_batch_to_parquet


@dataclass(frozen=True)
class OHLCVIngestionResult:
    """Result of fetching, validating, and optionally persisting one OHLCV batch."""

    batch: OHLCVBatch
    quality_report: DataQualityReport
    parquet_paths: tuple[Path, ...]


class OHLCVQualityError(ValueError):
    """Raised when an OHLCV batch fails validation before persistence."""

    def __init__(self, report: DataQualityReport) -> None:
        self.report = report
        issue_codes = ", ".join(issue.code for issue in report.issues) or "unknown"
        super().__init__(
            f"OHLCV quality validation failed for {report.symbol} {report.timeframe}: {issue_codes}"
        )


def fetch_validate_write_ohlcv(
    source: CCXTOHLCVSource,
    *,
    symbol: str,
    timeframe: str,
    output_root: Path | str,
    since: datetime | None = None,
    limit: int | None = None,
    params: dict[str, Any] | None = None,
    quality_config: OHLCVQualityConfig | None = None,
) -> OHLCVIngestionResult:
    """Fetch OHLCV data, validate it, and persist parquet only when validation passes."""
    batch = source.fetch_ohlcv_batch(
        symbol=symbol,
        timeframe=timeframe,
        since=since,
        limit=limit,
        params=params,
    )
    quality_report = validate_ohlcv_batch(batch, config=quality_config)
    if not quality_report.passed:
        raise OHLCVQualityError(quality_report)

    parquet_paths = tuple(write_ohlcv_batch_to_parquet(batch, output_root))
    return OHLCVIngestionResult(
        batch=batch,
        quality_report=quality_report,
        parquet_paths=parquet_paths,
    )
