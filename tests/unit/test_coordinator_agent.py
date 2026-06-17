"""Unit tests for Coordinator Agent lifecycle and memory boundary."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents.audit import AgentAuditEvent
from stat_arb.agents.coordinator import (
    AgentToolPermissionPolicy,
    AgentToolPermissionRequest,
    AgentToolPermissionScope,
    CoordinatorApprovalActionRequest,
    CoordinatorFinalDecisionEvidence,
    CoordinatorFinalDecisionPolicy,
    CoordinatorResourcePolicy,
    CoordinatorTaskRequest,
    CoordinatorTransitionRequest,
    ExperimentFinalDecision,
    ExperimentLifecycleStatus,
    apply_coordinator_approval_action,
    apply_coordinator_final_decision,
    claim_coordinator_task_by_id,
    claim_next_coordinator_task,
    complete_coordinator_task,
    decide_coordinator_final_decision,
    enforce_agent_tool_permission,
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


class FakeAuditWriter:
    """Fake audit sink that records sanitized agent audit events."""

    def __init__(self) -> None:
        self.events: list[AgentAuditEvent] = []

    def append(self, event: AgentAuditEvent) -> object:
        self.events.append(event)
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
        engine.dispose()


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


def test_coordinator_lifecycle_transition_writes_safe_audit_event(
    session: Session,
) -> None:
    """Coordinator lifecycle transitions should leave an operator-safe audit event."""
    experiment_id = _seed_experiment(session, status="new")
    memory = FakeMemoryService()
    audit = FakeAuditWriter()

    transition_experiment_lifecycle(
        CoordinatorTransitionRequest(
            experiment_id=experiment_id,
            target_status=ExperimentLifecycleStatus.DATA_VALIDATION,
            reason="Data validation is the next lifecycle stage.",
            actor="coordinator_agent",
        ),
        session=session,
        memory_service=memory,
        audit_writer=audit,
    )

    assert len(audit.events) == 1
    event = audit.events[0]
    assert event.agent_name == "coordinator_agent"
    assert event.action == "experiment_lifecycle_transition"
    assert event.status == "data_validation"
    assert event.reason == "Data validation is the next lifecycle stage."
    assert event.registry_refs == (f"registry:experiments/{experiment_id}",)
    assert event.memory_refs == (f"registry:experiments/{experiment_id}",)
    assert event.metadata["previous_status"] == "new"
    assert event.metadata["current_status"] == "data_validation"
    assert event.metadata["actor"] == "coordinator_agent"
    assert "raw_payload" not in event.to_safe_dict()["metadata"]


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
    assert "CoordinatorResourcePolicy" in script
    assert "max_running_tasks_per_agent" in script
    assert "CoordinatorFinalDecisionPolicy" in script
    assert "require_retest_justification" in script
    assert "CoordinatorApprovalActionRequest" in script
    assert "apply_coordinator_approval_action" in script
    assert "apply_coordinator_final_decision" in script
    assert "AgentToolPermissionPolicy" in script
    assert "enforce_agent_tool_permission" in script
    assert "AgentAuditEvent" in script
    assert "audit_writer\\.append" in script
    assert "memory_service\\.write" in script
    assert "check_coordinator_agent_boundaries.ps1" in pre_commit
    assert "Invoke-RequiredCheck $coordinatorAgentBoundaryCheckScript" in pre_commit
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

    claimed = claim_next_coordinator_task(
        agent_name="data_agent",
        policy=_resource_policy(data_agent=1),
        session=session,
    )

    assert claimed is not None
    assert claimed.task_id == high.task_id
    assert claimed.status == "running"
    assert claimed.attempt_count == 1
    assert claimed.started_at is not None
    assert session.query(CoordinatorTask).filter_by(task_id=low.task_id).one().status == "pending"


def test_coordinator_queue_claims_specific_pending_task_by_id(session: Session) -> None:
    """Stage executors should claim an explicit task without bypassing resource policy."""
    experiment_id = _seed_experiment(session, status="statistical_testing")
    task = enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=experiment_id,
            task_type="run_statistical_tests",
            agent_name="statistical_testing_agent",
            priority=5,
            max_attempts=2,
            payload={"dataset_a_id": "dataset-a"},
        ),
        session=session,
    )

    claimed = claim_coordinator_task_by_id(
        task_id=task.task_id,
        policy=_resource_policy(statistical_testing_agent=1),
        session=session,
    )

    assert claimed.task_id == task.task_id
    assert claimed.status == "running"
    assert claimed.attempt_count == 1
    assert claimed.started_at is not None


def test_coordinator_queue_claim_by_id_blocks_resource_limit(session: Session) -> None:
    """Task-id claims should obey the same global and per-agent limits as next-task claims."""
    experiment_id = _seed_experiment(session, status="statistical_testing")
    running = enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=experiment_id,
            task_type="run_statistical_tests",
            agent_name="statistical_testing_agent",
            priority=1,
            max_attempts=1,
            payload={},
        ),
        session=session,
    )
    pending = enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=experiment_id,
            task_type="run_statistical_tests",
            agent_name="statistical_testing_agent",
            priority=2,
            max_attempts=1,
            payload={},
        ),
        session=session,
    )
    claim_coordinator_task_by_id(
        task_id=running.task_id,
        policy=_resource_policy(statistical_testing_agent=1),
        session=session,
    )

    blocked = claim_coordinator_task_by_id(
        task_id=pending.task_id,
        policy=_resource_policy(statistical_testing_agent=1),
        session=session,
    )

    assert blocked is None
    assert session.query(CoordinatorTask).filter_by(task_id=pending.task_id).one().status == "pending"


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

    claimed = claim_next_coordinator_task(
        agent_name="statistical_testing_agent",
        policy=_resource_policy(statistical_testing_agent=1),
        session=session,
    )
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
        policy=_resource_policy(statistical_testing_agent=1),
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
    claimed = claim_next_coordinator_task(
        agent_name="backtest_agent",
        policy=_resource_policy(backtest_agent=1, report_agent=1),
        session=session,
    )
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
    completed = claim_next_coordinator_task(
        agent_name="report_agent",
        policy=_resource_policy(backtest_agent=1, report_agent=1),
        session=session,
    )
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


def test_coordinator_resource_policy_blocks_per_agent_parallelism_limit(
    session: Session,
) -> None:
    """Per-agent limits should prevent claiming more running tasks for one agent."""
    experiment_id = _seed_experiment(session, status="data_validation")
    policy = CoordinatorResourcePolicy(
        max_running_tasks=3,
        max_running_tasks_per_agent={"data_agent": 1, "report_agent": 1},
    )
    for symbol in ("AAA", "BBB"):
        enqueue_coordinator_task(
            CoordinatorTaskRequest(
                experiment_id=experiment_id,
                task_type="validate_data",
                agent_name="data_agent",
                priority=1,
                max_attempts=1,
                payload={"symbol": symbol},
            ),
            session=session,
        )

    first = claim_next_coordinator_task(agent_name="data_agent", policy=policy, session=session)
    second = claim_next_coordinator_task(agent_name="data_agent", policy=policy, session=session)

    assert first is not None
    assert second is None
    assert session.query(CoordinatorTask).filter_by(status="running").count() == 1
    assert session.query(CoordinatorTask).filter_by(status="pending").count() == 1


def test_coordinator_resource_policy_blocks_global_parallelism_limit(
    session: Session,
) -> None:
    """Global limits should prevent claiming work even when an agent has free capacity."""
    experiment_id = _seed_experiment(session, status="backtesting")
    policy = CoordinatorResourcePolicy(
        max_running_tasks=1,
        max_running_tasks_per_agent={"backtest_agent": 1, "report_agent": 1},
    )
    enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=experiment_id,
            task_type="run_backtest",
            agent_name="backtest_agent",
            priority=1,
            max_attempts=1,
            payload={},
        ),
        session=session,
    )
    enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=experiment_id,
            task_type="write_report",
            agent_name="report_agent",
            priority=1,
            max_attempts=1,
            payload={},
        ),
        session=session,
    )

    first = claim_next_coordinator_task(agent_name="backtest_agent", policy=policy, session=session)
    second = claim_next_coordinator_task(agent_name="report_agent", policy=policy, session=session)

    assert first is not None
    assert second is None
    assert session.query(CoordinatorTask).filter_by(status="running").count() == 1
    assert session.query(CoordinatorTask).filter_by(status="pending").count() == 1


def test_coordinator_claim_requires_explicit_resource_policy(session: Session) -> None:
    """Claiming work without resource policy should fail at the API boundary."""
    experiment_id = _seed_experiment(session, status="data_validation")
    enqueue_coordinator_task(
        CoordinatorTaskRequest(
            experiment_id=experiment_id,
            task_type="validate_data",
            agent_name="data_agent",
            priority=1,
            max_attempts=1,
            payload={},
        ),
        session=session,
    )

    with pytest.raises(TypeError):
        claim_next_coordinator_task(agent_name="data_agent", session=session)  # type: ignore[call-arg]


def test_coordinator_final_decision_rejects_critical_critic_status() -> None:
    """Coordinator should convert explicit critical Critic status into final rejection."""
    result = decide_coordinator_final_decision(
        CoordinatorFinalDecisionEvidence(
            critic_status="rejected",
            critic_objections=("lookahead_bias: signal used future data",),
            hypothesis_status="testing",
            retest_justification=None,
        ),
        policy=_final_decision_policy(),
    )

    assert result.final_decision == ExperimentFinalDecision.REJECTED
    assert "lookahead_bias" in result.reason
    assert result.checked_rules == ("critic_status_mapping", "retest_justification")


def test_coordinator_final_decision_quarantines_moderate_critic_status() -> None:
    """Coordinator should quarantine moderate issues without silently approving them."""
    result = decide_coordinator_final_decision(
        CoordinatorFinalDecisionEvidence(
            critic_status="quarantined",
            critic_objections=("weak_assumption: p-value too close to threshold",),
            hypothesis_status="testing",
            retest_justification=None,
        ),
        policy=_final_decision_policy(),
    )

    assert result.final_decision == ExperimentFinalDecision.QUARANTINED
    assert "weak_assumption" in result.reason


def test_coordinator_final_decision_approves_clean_critic_status() -> None:
    """Coordinator should approve only when policy maps the Critic status to approval."""
    result = decide_coordinator_final_decision(
        CoordinatorFinalDecisionEvidence(
            critic_status="approved",
            critic_objections=(),
            hypothesis_status="testing",
            retest_justification=None,
        ),
        policy=_final_decision_policy(),
    )

    assert result.final_decision == ExperimentFinalDecision.APPROVED
    assert "Critic status approved" in result.reason


def test_coordinator_final_decision_requires_retest_justification() -> None:
    """Retests of rejected hypotheses should not pass final decision without justification."""
    with pytest.raises(ValueError, match="retest_justification is required"):
        decide_coordinator_final_decision(
            CoordinatorFinalDecisionEvidence(
                critic_status="approved",
                critic_objections=(),
                hypothesis_status="retest",
                retest_justification=" ",
            ),
            policy=_final_decision_policy(),
        )


def test_coordinator_final_decision_allows_justified_retest() -> None:
    """A justified retest can proceed while preserving the operator rationale."""
    result = decide_coordinator_final_decision(
        CoordinatorFinalDecisionEvidence(
            critic_status="approved",
            critic_objections=(),
            hypothesis_status="retest",
            retest_justification="New six-month data window after structural market change.",
        ),
        policy=_final_decision_policy(),
    )

    assert result.final_decision == ExperimentFinalDecision.APPROVED
    assert "New six-month data window" in result.reason


def test_coordinator_final_decision_rejects_unmapped_critic_status() -> None:
    """Unknown Critic statuses must not be converted into hidden defaults."""
    with pytest.raises(ValueError, match="no final decision mapping"):
        decide_coordinator_final_decision(
            CoordinatorFinalDecisionEvidence(
                critic_status="needs_manual_review",
                critic_objections=("operator_review: ambiguous result",),
                hypothesis_status="testing",
                retest_justification=None,
            ),
            policy=_final_decision_policy(),
        )


def test_coordinator_applies_final_decision_through_transition_and_memory(
    session: Session,
) -> None:
    """Final decision integration should persist via lifecycle transition and memory policy."""
    experiment_id = _seed_experiment(session, status="reporting")
    memory = FakeMemoryService()

    result = apply_coordinator_final_decision(
        experiment_id=experiment_id,
        evidence=CoordinatorFinalDecisionEvidence(
            critic_status="approved",
            critic_objections=(),
            hypothesis_status="testing",
            retest_justification=None,
        ),
        policy=_final_decision_policy(),
        actor="coordinator_agent",
        session=session,
        memory_service=memory,
    )

    stored = session.query(Experiment).one()
    assert result.current_status == ExperimentLifecycleStatus.FINAL_DECISION
    assert stored.status == "final_decision"
    assert stored.final_decision == "approved"
    assert stored.completed_at is not None
    assert len(memory.requests) == 1
    assert memory.requests[0].metadata["final_decision"] == "approved"
    assert memory.requests[0].registry_reference == f"registry:experiments/{experiment_id}"
    assert "Critic status approved" in memory.requests[0].body


def test_coordinator_approval_action_requires_reason_and_writes_memory(
    session: Session,
) -> None:
    """Task 16.8b should expose audited approve/reject actions through Coordinator only."""
    experiment_id = _seed_experiment(session, status="reporting")
    memory = FakeMemoryService()

    result = apply_coordinator_approval_action(
        CoordinatorApprovalActionRequest(
            experiment_id=experiment_id,
            final_decision=ExperimentFinalDecision.APPROVED,
            reason="Human reviewer approved the report package for demo review.",
            actor="victor",
        ),
        session=session,
        memory_service=memory,
    )

    stored = session.query(Experiment).one()
    assert result.current_status == ExperimentLifecycleStatus.FINAL_DECISION
    assert stored.final_decision == "approved"
    assert stored.completed_at is not None
    assert memory.requests[0].registry_reference == f"registry:experiments/{experiment_id}"
    assert memory.requests[0].metadata["actor"] == "victor"
    assert memory.requests[0].metadata["final_decision"] == "approved"


def test_coordinator_approval_action_rejects_missing_reason_without_mutation(
    session: Session,
) -> None:
    """Manual approval actions must not hide actor/reason provenance."""
    experiment_id = _seed_experiment(session, status="reporting")
    memory = FakeMemoryService()

    with pytest.raises(ValueError, match="reason is required"):
        apply_coordinator_approval_action(
            CoordinatorApprovalActionRequest(
                experiment_id=experiment_id,
                final_decision=ExperimentFinalDecision.REJECTED,
                reason=" ",
                actor="victor",
            ),
            session=session,
            memory_service=memory,
        )

    stored = session.query(Experiment).one()
    assert stored.status == "reporting"
    assert stored.final_decision is None
    assert memory.requests == []


def test_coordinator_final_decision_integration_blocks_unjustified_retest_without_mutation(
    session: Session,
) -> None:
    """Invalid retests should not mutate registry state or write memory."""
    experiment_id = _seed_experiment(session, status="reporting")
    memory = FakeMemoryService()

    with pytest.raises(ValueError, match="retest_justification is required"):
        apply_coordinator_final_decision(
            experiment_id=experiment_id,
            evidence=CoordinatorFinalDecisionEvidence(
                critic_status="approved",
                critic_objections=(),
                hypothesis_status="retest",
                retest_justification=None,
            ),
            policy=_final_decision_policy(),
            actor="coordinator_agent",
            session=session,
            memory_service=memory,
        )

    stored = session.query(Experiment).one()
    assert stored.status == "reporting"
    assert stored.final_decision is None
    assert stored.completed_at is None
    assert memory.requests == []


def test_coordinator_final_decision_integration_requires_memory_service(
    session: Session,
) -> None:
    """Coordinator final decisions must not bypass the Memory Agent policy boundary."""
    experiment_id = _seed_experiment(session, status="reporting")

    with pytest.raises(TypeError):
        apply_coordinator_final_decision(  # type: ignore[call-arg]
            experiment_id=experiment_id,
            evidence=CoordinatorFinalDecisionEvidence(
                critic_status="approved",
                critic_objections=(),
                hypothesis_status="testing",
                retest_justification=None,
            ),
            policy=_final_decision_policy(),
            actor="coordinator_agent",
            session=session,
        )


def test_coordinator_agent_tool_permission_allows_explicit_scope() -> None:
    """Agents should be allowed only when policy grants the requested tool scope."""
    result = enforce_agent_tool_permission(
        AgentToolPermissionRequest(
            agent_name="data_agent",
            scope=AgentToolPermissionScope.DATA_ARTIFACTS_WRITE,
            reason="Persist validated OHLCV parquet artifact.",
        ),
        policy=_tool_permission_policy(),
    )

    assert result.allowed is True
    assert result.agent_name == "data_agent"
    assert result.scope == AgentToolPermissionScope.DATA_ARTIFACTS_WRITE
    assert "allowed" in result.reason


def test_coordinator_agent_tool_permission_denies_missing_scope() -> None:
    """Agents must fail closed when the requested scope is absent from policy."""
    with pytest.raises(PermissionError, match="not allowed"):
        enforce_agent_tool_permission(
            AgentToolPermissionRequest(
                agent_name="report_agent",
                scope=AgentToolPermissionScope.SECRETS_READ,
                reason="Reports must not access secrets.",
            ),
            policy=_tool_permission_policy(),
        )


def test_coordinator_agent_tool_permission_denies_unknown_agent() -> None:
    """Unknown agents must not inherit any default permissions."""
    with pytest.raises(PermissionError, match="no permissions configured"):
        enforce_agent_tool_permission(
            AgentToolPermissionRequest(
                agent_name="unknown_agent",
                scope=AgentToolPermissionScope.REGISTRY_READ,
                reason="Unknown agent should fail closed.",
            ),
            policy=_tool_permission_policy(),
        )


def test_coordinator_agent_tool_permission_request_requires_reason() -> None:
    """Tool access should leave an operator-readable reason for audit trails."""
    with pytest.raises(ValueError, match="reason is required"):
        AgentToolPermissionRequest(
            agent_name="data_agent",
            scope=AgentToolPermissionScope.REGISTRY_READ,
            reason=" ",
        )


def test_coordinator_agent_tool_permission_policy_rejects_empty_agent_scopes() -> None:
    """Permission policies must not hide implicit default access."""
    with pytest.raises(ValueError, match="must have at least one scope"):
        AgentToolPermissionPolicy(agent_scopes={"data_agent": frozenset()})


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


def _resource_policy(**per_agent: int) -> CoordinatorResourcePolicy:
    return CoordinatorResourcePolicy(
        max_running_tasks=sum(per_agent.values()),
        max_running_tasks_per_agent=per_agent,
    )


def _final_decision_policy() -> CoordinatorFinalDecisionPolicy:
    return CoordinatorFinalDecisionPolicy(
        critic_status_to_decision={
            "rejected": ExperimentFinalDecision.REJECTED,
            "quarantined": ExperimentFinalDecision.QUARANTINED,
            "approved": ExperimentFinalDecision.APPROVED,
        },
        require_retest_justification=True,
    )


def _tool_permission_policy() -> AgentToolPermissionPolicy:
    return AgentToolPermissionPolicy(
        agent_scopes={
            "data_agent": frozenset(
                {
                    AgentToolPermissionScope.REGISTRY_READ,
                    AgentToolPermissionScope.REGISTRY_WRITE,
                    AgentToolPermissionScope.DATA_ARTIFACTS_READ,
                    AgentToolPermissionScope.DATA_ARTIFACTS_WRITE,
                    AgentToolPermissionScope.MEMORY_WRITE,
                    AgentToolPermissionScope.SECRETS_READ,
                }
            ),
            "statistical_testing_agent": frozenset(
                {
                    AgentToolPermissionScope.REGISTRY_READ,
                    AgentToolPermissionScope.REGISTRY_WRITE,
                    AgentToolPermissionScope.DATA_ARTIFACTS_READ,
                    AgentToolPermissionScope.MEMORY_WRITE,
                }
            ),
            "backtest_agent": frozenset(
                {
                    AgentToolPermissionScope.REGISTRY_READ,
                    AgentToolPermissionScope.REGISTRY_WRITE,
                    AgentToolPermissionScope.DATA_ARTIFACTS_READ,
                    AgentToolPermissionScope.REPORTS_WRITE,
                    AgentToolPermissionScope.MEMORY_WRITE,
                }
            ),
            "critic_agent": frozenset(
                {
                    AgentToolPermissionScope.REGISTRY_READ,
                    AgentToolPermissionScope.REGISTRY_WRITE,
                    AgentToolPermissionScope.MEMORY_READ,
                    AgentToolPermissionScope.MEMORY_WRITE,
                }
            ),
            "report_agent": frozenset(
                {
                    AgentToolPermissionScope.REGISTRY_READ,
                    AgentToolPermissionScope.REGISTRY_WRITE,
                    AgentToolPermissionScope.REPORTS_READ,
                    AgentToolPermissionScope.REPORTS_WRITE,
                    AgentToolPermissionScope.MEMORY_WRITE,
                }
            ),
            "coordinator_agent": frozenset(
                {
                    AgentToolPermissionScope.REGISTRY_READ,
                    AgentToolPermissionScope.REGISTRY_WRITE,
                    AgentToolPermissionScope.MEMORY_READ,
                    AgentToolPermissionScope.MEMORY_WRITE,
                }
            ),
        }
    )
