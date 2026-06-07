"""Unit tests for Hypothesis Agent generation and persistence boundary."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents import (
    HypothesisGenerationConfig,
    HypothesisUniverseAsset,
    generate_rule_based_hypotheses,
)
from stat_arb.memory import MemoryWriteRequest
from stat_arb.storage import Base, Hypothesis


class FakeMemoryService:
    """Fake Memory Agent service that records write requests."""

    def __init__(self) -> None:
        self.requests: list[MemoryWriteRequest] = []

    def write(self, request: MemoryWriteRequest) -> object:
        self.requests.append(request)
        return object()


def test_hypothesis_agent_generates_registry_records_and_memory_summaries() -> None:
    """Hypothesis Agent should persist deterministic pair hypotheses and memory summaries."""
    session = _session()
    memory = FakeMemoryService()

    result = generate_rule_based_hypotheses(
        assets=(
            HypothesisUniverseAsset(symbol="AAA", sector="Banks", market_cap=100_000_000_000),
            HypothesisUniverseAsset(symbol="BBB", sector="Banks", market_cap=95_000_000_000),
            HypothesisUniverseAsset(symbol="CCC", sector="Energy", market_cap=120_000_000_000),
            HypothesisUniverseAsset(symbol="DDD", sector="Banks", market_cap=10_000_000_000),
        ),
        correlations={
            ("AAA", "BBB"): 0.93,
            ("AAA", "CCC"): 0.98,
            ("AAA", "DDD"): 0.89,
            ("BBB", "DDD"): 0.72,
        },
        config=HypothesisGenerationConfig(
            require_same_sector=True,
            min_abs_correlation=0.85,
            min_market_cap=50_000_000_000,
            max_market_cap=150_000_000_000,
            max_pairs=5,
            initial_novelty_score=1.0,
            initial_status="new",
            source="rule_based",
            created_by="hypothesis_agent",
        ),
        session=session,
        memory_service=memory,
    )

    stored = session.query(Hypothesis).all()
    assert result.generated_count == 1
    assert result.skipped_count == 5
    assert len(stored) == 1
    assert stored[0].asset_a == "AAA"
    assert stored[0].asset_b == "BBB"
    assert stored[0].source == "rule_based"
    assert stored[0].created_by == "hypothesis_agent"
    assert "same sector Banks" in stored[0].rationale
    assert "absolute correlation 0.9300" in stored[0].rationale
    assert result.memory_written is True
    assert len(memory.requests) == 1
    assert memory.requests[0].registry_reference == f"registry:hypotheses/{stored[0].hypothesis_id}"
    assert "Generated rule-based pair hypothesis" in memory.requests[0].body


def test_hypothesis_agent_rejects_invalid_generation_config() -> None:
    """Research-impacting screening settings must be explicit and valid."""
    session = _session()

    try:
        generate_rule_based_hypotheses(
            assets=(),
            correlations={},
            config=HypothesisGenerationConfig(
                require_same_sector=True,
                min_abs_correlation=1.2,
                min_market_cap=1,
                max_market_cap=None,
                max_pairs=1,
                initial_novelty_score=1.0,
                initial_status="new",
                source="rule_based",
                created_by="hypothesis_agent",
            ),
            session=session,
        )
    except ValueError as exc:
        assert "min_abs_correlation" in str(exc)
    else:
        raise AssertionError("invalid min_abs_correlation should fail")


def test_hypothesis_agent_boundary_guard_is_in_pre_commit_and_ci() -> None:
    """Guard should prevent direct ApeRAG writes and registry bypass regressions."""
    script = Path("scripts/check_hypothesis_agent_boundaries.ps1").read_text(encoding="utf-8")
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "ApeRAGMemoryClient" in script
    assert "Hypothesis" in script
    assert "session.add" in script
    assert "check_hypothesis_agent_boundaries.ps1" in pre_commit
    assert "& $hypothesisAgentBoundaryCheckScript" in pre_commit
    assert "Check Hypothesis Agent boundaries" in ci
    assert "./scripts/check_hypothesis_agent_boundaries.ps1" in ci


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()
