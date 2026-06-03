"""Deterministic OHLCV timestamp alignment helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid5

from stat_arb.domain import OHLCVBar, OHLCVBatch

_ALIGNMENT_NAMESPACE = UUID("95b745ea-9ef9-45a3-9851-7c6c1ed5a9c4")


@dataclass(frozen=True)
class PairAlignmentResult:
    """Aligned OHLCV batches for a two-asset statistical test boundary."""

    asset_a: OHLCVBatch
    asset_b: OHLCVBatch
    aligned_timestamps: tuple[datetime, ...]
    dropped_asset_a_bars: int
    dropped_asset_b_bars: int

    @property
    def bar_count(self) -> int:
        """Return the number of bars retained in both aligned batches."""
        return len(self.aligned_timestamps)

    @property
    def asset_a_retention_ratio(self) -> float:
        """Return retained share of the original asset A bars."""
        total = self.bar_count + self.dropped_asset_a_bars
        return self.bar_count / total if total else 0.0

    @property
    def asset_b_retention_ratio(self) -> float:
        """Return retained share of the original asset B bars."""
        total = self.bar_count + self.dropped_asset_b_bars
        return self.bar_count / total if total else 0.0


def align_ohlcv_pair(
    asset_a: OHLCVBatch,
    asset_b: OHLCVBatch,
    *,
    require_full_overlap: bool = False,
    min_overlap_ratio: float = 0.0,
) -> PairAlignmentResult:
    """Align two OHLCV batches to their shared timestamps.

    Partial overlaps are allowed by default. Callers can require full overlap or set a
    minimum retained-share threshold before statistical testing.
    """
    if asset_a.symbol == asset_b.symbol:
        raise ValueError("asset_a and asset_b must be different symbols")
    if asset_a.source != asset_b.source:
        raise ValueError("asset_a and asset_b must have the same source")
    if asset_a.timeframe != asset_b.timeframe:
        raise ValueError("asset_a and asset_b must have the same timeframe")
    if not 0.0 <= min_overlap_ratio <= 1.0:
        raise ValueError("min_overlap_ratio must be between 0 and 1")

    bars_a = {bar.timestamp: bar for bar in asset_a.bars}
    bars_b = {bar.timestamp: bar for bar in asset_b.bars}
    aligned_timestamps = tuple(sorted(set(bars_a) & set(bars_b)))
    if not aligned_timestamps:
        raise ValueError("asset_a and asset_b have no overlapping timestamps")

    dropped_a = len(asset_a.bars) - len(aligned_timestamps)
    dropped_b = len(asset_b.bars) - len(aligned_timestamps)
    if require_full_overlap and (dropped_a or dropped_b):
        raise ValueError("asset_a and asset_b must have full timestamp overlap")

    ratio_a = len(aligned_timestamps) / len(asset_a.bars)
    ratio_b = len(aligned_timestamps) / len(asset_b.bars)
    if min(ratio_a, ratio_b) < min_overlap_ratio:
        raise ValueError("timestamp overlap ratio is below min_overlap_ratio")

    alignment_key = _alignment_key(asset_a, asset_b, aligned_timestamps)
    aligned_a = _aligned_batch(asset_a, asset_b.symbol, aligned_timestamps, bars_a, alignment_key)
    aligned_b = _aligned_batch(asset_b, asset_a.symbol, aligned_timestamps, bars_b, alignment_key)

    return PairAlignmentResult(
        asset_a=aligned_a,
        asset_b=aligned_b,
        aligned_timestamps=aligned_timestamps,
        dropped_asset_a_bars=dropped_a,
        dropped_asset_b_bars=dropped_b,
    )


def _aligned_batch(
    batch: OHLCVBatch,
    paired_symbol: str,
    aligned_timestamps: tuple[datetime, ...],
    bars_by_timestamp: dict[datetime, OHLCVBar],
    alignment_key: str,
) -> OHLCVBatch:
    bars: list[OHLCVBar] = []
    for timestamp in aligned_timestamps:
        bar = bars_by_timestamp[timestamp]
        metadata = dict(bar.metadata)
        metadata.update(
            {
                "aligned_from_dataset_id": str(batch.dataset_id),
                "pair_alignment_id": alignment_key,
                "paired_symbol": paired_symbol,
            }
        )
        bars.append(bar.model_copy(update={"metadata": metadata}))

    return OHLCVBatch(
        dataset_id=uuid5(_ALIGNMENT_NAMESPACE, f"{alignment_key}|{batch.dataset_id}|{batch.symbol}"),
        symbol=batch.symbol,
        source=batch.source,
        timeframe=batch.timeframe,
        bars=bars,
        exchange=batch.exchange,
    )


def _alignment_key(
    asset_a: OHLCVBatch,
    asset_b: OHLCVBatch,
    aligned_timestamps: tuple[datetime, ...],
) -> str:
    identity = "|".join(
        [
            str(asset_a.dataset_id),
            str(asset_b.dataset_id),
            asset_a.symbol,
            asset_b.symbol,
            str(asset_a.source),
            asset_a.timeframe,
            aligned_timestamps[0].isoformat(),
            aligned_timestamps[-1].isoformat(),
            str(len(aligned_timestamps)),
        ]
    )
    return str(uuid5(_ALIGNMENT_NAMESPACE, identity))
