"""Unit tests for Coordinator Agent lifecycle and memory boundary."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents.coordinator import (
    CoordinatorTaskRequest,
    CoordinatorTransitionRequest,
    ExperimentFinalDecision,
    ExperimentLifecycleStatus,
    claim_next_coordinator_task,
    complete_coordinator_task,
    enqueue_coordinator_task,
    fail_coordinator_task,
    list_recoverable_coordinator_tasks,
    transition_experiment_lifecycle,
)
from stat_arb.memory import MemoryWriteRequest
from stat_arb.storage import Base, CoordinatorTask, Experiment, Hypothesis


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


def test_coordinator_queue_claims_highest_priority_pending_task(session: Session) -> None:
    """Coordinator queue should persist tasks and claim the highest-priority pending work."""
    first_experiment_id = _seed_experiment(session, status="data_validation")
    second_experiment_id = _seed_experiment(session, status="data_validation")
    low = enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=first_experiment_id,
            task_type="validate_data",
            agent_name="data_agent",
            priority=10,
            max_attempts=2,
            payload={"symbol": "AAA"},
        ),
        session=session,
    )
    high = enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=second_experiment_id,
            task_type="validate_data",
            agent_name="data_agent",
            priority=1,
            max_attempts=2,
            payload={"symbol": "BBB"},
        ),
        session=session,
    )

    claimed = claim_next_coordinator_task(agent_name="data_agent", session=session)

    assert claimed is not None
    assert claimed.task_id == high.task_id
    assert claimed.status == "running"
    assert claimed.attempt_count == 1
    assert claimed.started_at is not None
    assert session.query(CoordinatorTask).filter_by(task_id=low.task_id).one().status == "pending"


def test_coordinator_queue_records_retryable_failure_and_exhausted_failure(
    session: Session,
) -> None:
    """Failed tasks should either return to pending or become failed after retry budget."""
    experiment_id = _seed_experiment(session, status="statistical_testing")
    enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=experiment_id,
            task_type="run_statistical_tests",
            agent_name="statistical_testing_agent",
            priority=5,
            max_attempts=2,
            payload={"test_id": "synthetic"},
        ),
        session=session,
    )

    claimed = claim_next_coordinator_task(agent_name="statistical_testing_agent", session=session)
    assert claimed is not None
    retryable = fail_coordinator_task(
        task_id=claimed.task_id,
        error_summary="temporary exchange outage",
        session=session,
    )
    assert retryable.status == "pending"
    assert retryable.last_error == "temporary exchange outage"

    claimed_again = claim_next_coordinator_task(
        agent_name="statistical_testing_agent",
        session=session,
    )
    assert claimed_again is not None
    exhausted = fail_coordinator_task(
        task_id=claimed_again.task_id,
        error_summary="statistical input missing",
        session=session,
    )
    assert exhausted.status == "failed"
    assert exhausted.completed_at is not None


def test_coordinator_queue_recovers_running_tasks_after_restart(session: Session) -> None:
    """Recovery should expose unfinished running tasks without marking completed work."""
    experiment_id = _seed_experiment(session, status="backtesting")
    task = enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=experiment_id,
            task_type="run_backtest",
            agent_name="backtest_agent",
            priority=3,
            max_attempts=3,
            payload={"backtest": "synthetic"},
        ),
        session=session,
    )
    claimed = claim_next_coordinator_task(agent_name="backtest_agent", session=session)
    assert claimed is not None
    enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=experiment_id,
            task_type="write_report",
            agent_name="report_agent",
            priority=4,
            max_attempts=1,
            payload={},
        ),
        session=session,
    )
    completed = claim_next_coordinator_task(agent_name="report_agent", session=session)
    assert completed is not None
    complete_coordinator_task(task_id=completed.task_id, session=session)

    recoverable = list_recoverable_coordinator_tasks(session=session)

    assert [item.task_id for item in recoverable] == [task.task_id]
    assert recoverable[0].status == "running"
    assert recoverable[0].agent_name == "backtest_agent"


def test_coordinator_task_request_requires_explicit_retry_and_priority() -> None:
    """Task queue inputs must not hide priority or retry policy defaults."""
    with pytest.raises(TypeError):
        CoordinatorTaskRequest(  # type: ignore[call-arg]
            experiment_id=str(uuid4()),
            task_type="run_backtest",
            agent_name="backtest_agent",
            payload={},
        )


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
