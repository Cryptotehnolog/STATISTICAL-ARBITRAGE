"""Market data ingestion utilities."""

from stat_arb.ingestion.ccxt_source import CCXTOHLCVSource, write_ohlcv_batch_to_parquet

__all__ = [
    "CCXTOHLCVSource",
    "write_ohlcv_batch_to_parquet",
]
