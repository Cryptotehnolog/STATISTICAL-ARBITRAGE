"""Unit tests for Coordinator Agent lifecycle and memory boundary."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents.coordinator import (
    CoordinatorTransitionRequest,
    ExperimentFinalDecision,
    ExperimentLifecycleStatus,
    transition_experiment_lifecycle,
)
from stat_arb.memory import MemoryWriteRequest
from stat_arb.storage import Base, Experiment, Hypothesis


class FakeMemoryService:
    """Fake Memory Agent service that records write requests."""

    def __init__(self) -> None:
        self.requests: list[MemoryWriteRequest] = []

    def write(self, request: MemoryWriteRequest) -> object:
        self.requests.append(request)
        return object()


@pytest.fixture
def session() -> Session:
    """Create an in-memory registry session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db_session = session_factory()
    try:
        yield db_session
    finally:
        db_session.close()


def test_coordinator_persists_valid_lifecycle_transition_and_memory_event(
    session: Session,
) -> None:
    """Coordinator should persist allowed transitions and write a concise memory event."""
    experiment_id = _seed_experiment(session, status="new")
    memory = FakeMemoryService()

    result = transition_experiment_lifecycle(
        CoordinatorTransitionRequest(
            experiment_id=experiment_id,
            target_status=ExperimentLifecycleStatus.DATA_VALIDATION,
            reason="Data validation is the next lifecycle stage.",
            actor="coordinator_agent",
        ),
        session=session,
        memory_service=memory,
    )

    stored = session.query(Experiment).one()
    assert result.previous_status == ExperimentLifecycleStatus.NEW
    assert result.current_status == ExperimentLifecycleStatus.DATA_VALIDATION
    assert stored.status == "data_validation"
    assert stored.current_agent == "data_agent"
    assert stored.completed_at is None
    assert result.memory_written is True
    assert len(memory.requests) == 1
    assert memory.requests[0].record_type == "agent_decision"
    assert memory.requests[0].registry_reference == f"registry:experiments/{stored.experiment_id}"
    assert "Lifecycle transition" in memory.requests[0].body
    assert "raw log" not in memory.requests[0].body.lower()


def test_coordinator_rejects_invalid_transition_without_mutating_registry(
    session: Session,
) -> None:
    """Coordinator should not jump over required lifecycle stages."""
    experiment_id = _seed_experiment(session, status="new")

    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        transition_experiment_lifecycle(
            CoordinatorTransitionRequest(
                experiment_id=experiment_id,
                target_status=ExperimentLifecycleStatus.BACKTESTING,
                reason="Skipping the prerequisite stages would hide missing validation.",
                actor="coordinator_agent",
            ),
            session=session,
        )

    stored = session.query(Experiment).one()
    assert stored.status == "new"
    assert stored.current_agent is None
    assert stored.final_decision is None
    assert stored.completed_at is None


def test_coordinator_requires_reason_for_reject_or_quarantine(
    session: Session,
) -> None:
    """Rejected and quarantined decisions must explain the decision."""
    experiment_id = _seed_experiment(session, status="critic_review")

    with pytest.raises(ValueError, match="reason is required"):
        transition_experiment_lifecycle(
            CoordinatorTransitionRequest(
                experiment_id=experiment_id,
                target_status=ExperimentLifecycleStatus.FINAL_DECISION,
                reason=" ",
                actor="coordinator_agent",
                final_decision=ExperimentFinalDecision.REJECTED,
            ),
            session=session,
        )

    stored = session.query(Experiment).one()
    assert stored.status == "critic_review"
    assert stored.final_decision is None
    assert stored.rejection_reason is None


def test_coordinator_persists_final_decision_and_completion_timestamp(
    session: Session,
) -> None:
    """Final decisions should be stored in the registry and summarized through memory policy."""
    experiment_id = _seed_experiment(session, status="reporting")
    memory = FakeMemoryService()

    result = transition_experiment_lifecycle(
        CoordinatorTransitionRequest(
            experiment_id=experiment_id,
            target_status=ExperimentLifecycleStatus.FINAL_DECISION,
            reason="Critic and report artifacts support demo review.",
            actor="coordinator_agent",
            final_decision=ExperimentFinalDecision.APPROVED,
        ),
        session=session,
        memory_service=memory,
    )

    stored = session.query(Experiment).one()
    assert result.current_status == ExperimentLifecycleStatus.FINAL_DECISION
    assert stored.status == "final_decision"
    assert stored.current_agent is None
    assert stored.final_decision == "approved"
    assert stored.rejection_reason is None
    assert stored.completed_at is not None
    assert stored.completed_at.tzinfo is None
    assert memory.requests[0].source_id == stored.experiment_id
    assert memory.requests[0].metadata["final_decision"] == "approved"


def test_coordinator_boundary_guard_is_in_pre_commit_and_ci() -> None:
    """Guard should prevent direct ApeRAG writes and lifecycle registry bypass regressions."""
    script = Path("scripts/check_coordinator_agent_boundaries.ps1").read_text(encoding="utf-8")
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "ApeRAGMemoryClient" in script
    assert "Experiment" in script
    assert "memory_service\\.write" in script
    assert "check_coordinator_agent_boundaries.ps1" in pre_commit
    assert "& $coordinatorAgentBoundaryCheckScript" in pre_commit
    assert "Check Coordinator Agent boundaries" in ci
    assert "./scripts/check_coordinator_agent_boundaries.ps1" in ci


def _seed_experiment(session: Session, *, status: str) -> str:
    hypothesis_id = uuid4()
    experiment_id = uuid4()
    session.add(
        Hypothesis(
            hypothesis_id=str(hypothesis_id),
            asset_a="AAA",
            asset_b="BBB",
            rationale="Synthetic coordinator pair",
            source="unit-test",
            created_by="pytest",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
    )
    session.flush()
    session.add(
        Experiment(
            experiment_id=str(experiment_id),
            hypothesis_id=str(hypothesis_id),
            status=status,
            current_agent=None,
        )
    )
    session.commit()
    return str(experiment_id)
