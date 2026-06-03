"""Market data ingestion utilities."""

from stat_arb.ingestion.ccxt_source import CCXTOHLCVSource, write_ohlcv_batch_to_parquet
from stat_arb.ingestion.pipeline import (
    OHLCVIngestionResult,
    OHLCVQualityError,
    fetch_validate_write_ohlcv,
)

__all__ = [
    "CCXTOHLCVSource",
    "OHLCVIngestionResult",
    "OHLCVQualityError",
    "fetch_validate_write_ohlcv",
    "write_ohlcv_batch_to_parquet",
]
