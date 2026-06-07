"""Hypothesis Agent rule-based generation and persistence boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from typing import Protocol

from sqlalchemy.orm import Session

from stat_arb.memory import MemoryRecordType, MemoryWriteRequest
from stat_arb.storage.models import Hypothesis


class MemoryWriter(Protocol):
    """Minimal Memory Agent service protocol used by this boundary."""

    def write(self, request: MemoryWriteRequest) -> object:
        """Write a policy-approved memory record."""


@dataclass(frozen=True)
class HypothesisUniverseAsset:
    """Tradable asset metadata used by rule-based pair screening."""

    symbol: str
    sector: str
    market_cap: int


@dataclass(frozen=True)
class HypothesisGenerationConfig:
    """Explicit rule-based screening configuration for Hypothesis Agent."""

    require_same_sector: bool
    min_abs_correlation: float
    min_market_cap: int
    max_market_cap: int | None
    max_pairs: int
    initial_novelty_score: float
    initial_status: str
    source: str
    created_by: str


@dataclass(frozen=True)
class HypothesisGenerationResult:
    """Result of a registry-backed hypothesis generation run."""

    hypotheses: tuple[Hypothesis, ...]
    generated_count: int
    skipped_count: int
    memory_written: bool


def generate_rule_based_hypotheses(
    *,
    assets: Sequence[HypothesisUniverseAsset],
    correlations: Mapping[tuple[str, str], float],
    config: HypothesisGenerationConfig,
    session: Session,
    memory_service: MemoryWriter | None = None,
) -> HypothesisGenerationResult:
    """Generate deterministic pair hypotheses, persist them, and write memory summaries."""
    _validate_config(config)
    normalized_assets = tuple(_normalize_asset(asset) for asset in assets)
    normalized_correlations = _normalize_correlations(correlations)

    candidates: list[tuple[HypothesisUniverseAsset, HypothesisUniverseAsset, float]] = []
    skipped_count = 0
    for asset_a, asset_b in combinations(sorted(normalized_assets, key=lambda item: item.symbol), 2):
        correlation = normalized_correlations.get(_pair_key(asset_a.symbol, asset_b.symbol))
        if correlation is None or not _passes_filters(asset_a, asset_b, correlation, config):
            skipped_count += 1
            continue
        candidates.append((asset_a, asset_b, correlation))

    candidates.sort(key=lambda item: (-abs(item[2]), item[0].symbol, item[1].symbol))
    selected = candidates[: config.max_pairs]
    skipped_count += max(0, len(candidates) - len(selected))

    stored: list[Hypothesis] = []
    for asset_a, asset_b, correlation in selected:
        hypothesis = Hypothesis(
            asset_a=asset_a.symbol,
            asset_b=asset_b.symbol,
            rationale=_rationale_for(asset_a, asset_b, correlation),
            source=config.source,
            novelty_score=config.initial_novelty_score,
            status=config.initial_status,
            created_by=config.created_by,
        )
        session.add(hypothesis)
        session.flush()
        stored.append(hypothesis)
        if memory_service is not None:
            memory_service.write(_memory_request_for(hypothesis, correlation))

    return HypothesisGenerationResult(
        hypotheses=tuple(stored),
        generated_count=len(stored),
        skipped_count=skipped_count,
        memory_written=memory_service is not None and bool(stored),
    )


def _validate_config(config: HypothesisGenerationConfig) -> None:
    if not 0.0 <= config.min_abs_correlation <= 1.0:
        raise ValueError("min_abs_correlation must be between 0.0 and 1.0")
    if config.min_market_cap < 0:
        raise ValueError("min_market_cap must be non-negative")
    if config.max_market_cap is not None and config.max_market_cap < config.min_market_cap:
        raise ValueError("max_market_cap must be greater than or equal to min_market_cap")
    if config.max_pairs <= 0:
        raise ValueError("max_pairs must be positive")
    if not 0.0 <= config.initial_novelty_score <= 1.0:
        raise ValueError("initial_novelty_score must be between 0.0 and 1.0")
    if not config.initial_status.strip():
        raise ValueError("initial_status must be non-empty")
    if not config.source.strip():
        raise ValueError("source must be non-empty")
    if not config.created_by.strip():
        raise ValueError("created_by must be non-empty")


def _normalize_asset(asset: HypothesisUniverseAsset) -> HypothesisUniverseAsset:
    symbol = asset.symbol.strip().upper()
    sector = asset.sector.strip()
    if not symbol:
        raise ValueError("asset symbol must be non-empty")
    if not sector:
        raise ValueError("asset sector must be non-empty")
    if asset.market_cap < 0:
        raise ValueError("asset market_cap must be non-negative")
    return HypothesisUniverseAsset(symbol=symbol, sector=sector, market_cap=asset.market_cap)


def _normalize_correlations(
    correlations: Mapping[tuple[str, str], float],
) -> dict[tuple[str, str], float]:
    normalized: dict[tuple[str, str], float] = {}
    for pair, value in correlations.items():
        if len(pair) != 2:
            raise ValueError("correlation keys must be two-symbol pairs")
        if not -1.0 <= value <= 1.0:
            raise ValueError("correlation values must be between -1.0 and 1.0")
        normalized[_pair_key(pair[0], pair[1])] = float(value)
    return normalized


def _pair_key(symbol_a: str, symbol_b: str) -> tuple[str, str]:
    first, second = sorted((symbol_a.strip().upper(), symbol_b.strip().upper()))
    if first == second:
        raise ValueError("pair symbols must be different")
    return first, second


def _passes_filters(
    asset_a: HypothesisUniverseAsset,
    asset_b: HypothesisUniverseAsset,
    correlation: float,
    config: HypothesisGenerationConfig,
) -> bool:
    if config.require_same_sector and asset_a.sector != asset_b.sector:
        return False
    if abs(correlation) < config.min_abs_correlation:
        return False
    for asset in (asset_a, asset_b):
        if asset.market_cap < config.min_market_cap:
            return False
        if config.max_market_cap is not None and asset.market_cap > config.max_market_cap:
            return False
    return True


def _rationale_for(
    asset_a: HypothesisUniverseAsset,
    asset_b: HypothesisUniverseAsset,
    correlation: float,
) -> str:
    return (
        f"Rule-based pair candidate: {asset_a.symbol}/{asset_b.symbol}; "
        f"same sector {asset_a.sector}; absolute correlation {abs(correlation):.4f}."
    )


def _memory_request_for(hypothesis: Hypothesis, correlation: float) -> MemoryWriteRequest:
    return MemoryWriteRequest(
        record_type=MemoryRecordType.HYPOTHESIS,
        title=f"Hypothesis generated: {hypothesis.asset_a}/{hypothesis.asset_b}",
        body=(
            "Generated rule-based pair hypothesis. Structured hypothesis details are stored "
            f"in the registry. Rationale: {hypothesis.rationale}"
        ),
        source_id=hypothesis.hypothesis_id,
        registry_reference=f"registry:hypotheses/{hypothesis.hypothesis_id}",
        tags=["hypothesis", "rule-based"],
        metadata={
            "asset_a": hypothesis.asset_a,
            "asset_b": hypothesis.asset_b,
            "correlation_abs": f"{abs(correlation):.4f}",
        },
    )
