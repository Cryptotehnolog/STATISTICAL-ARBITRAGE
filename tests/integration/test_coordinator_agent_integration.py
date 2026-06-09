"""Integration tests for the Coordinator Agent boundary."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents.coordinator import (
    AgentToolPermissionPolicy,
    AgentToolPermissionRequest,
    AgentToolPermissionScope,
    CoordinatorFinalDecisionEvidence,
    CoordinatorFinalDecisionPolicy,
    CoordinatorResourcePolicy,
    CoordinatorTaskRequest,
    ExperimentFinalDecision,
    apply_coordinator_final_decision,
    claim_next_coordinator_task,
    complete_coordinator_task,
    enforce_agent_tool_permission,
    enqueue_coordinator_task,
)
from stat_arb.memory import MemoryWriteRequest
from stat_arb.storage import Base, CoordinatorTask, Experiment, Hypothesis


class FakeMemoryService:
    """Fake Memory Agent service used to verify policy-boundary writes."""

    def __init__(self) -> None:
        self.requests: list[MemoryWriteRequest] = []

    def write(self, request: MemoryWriteRequest) -> object:
        self.requests.append(request)
        return object()


def test_coordinator_agent_boundary_runs_lifecycle_queue_permissions_and_memory() -> None:
    """Coordinator should coordinate queue, permissions, registry decision, and memory summary."""
    session = _create_session()
    memory = FakeMemoryService()
    try:
        experiment_id = _seed_experiment(session)
        task = enqueue_coordinator_task(
            CoordinatorTaskRequest(
                experiment_id=experiment_id,
                task_type="run_backtest",
                agent_name="backtest_agent",
                priority=1,
                max_attempts=2,
                payload={"artifact": "registry:artifacts/backtest/synthetic"},
            ),
            session=session,
        )

        permission = enforce_agent_tool_permission(
            AgentToolPermissionRequest(
                agent_name="backtest_agent",
                scope=AgentToolPermissionScope.REPORTS_WRITE,
                reason="Persist backtest report artifact summary.",
            ),
            policy=_tool_permission_policy(),
        )
        claimed = claim_next_coordinator_task(
            agent_name="backtest_agent",
            policy=CoordinatorResourcePolicy(
                max_running_tasks=1,
                max_running_tasks_per_agent={"backtest_agent": 1},
            ),
            session=session,
        )
        completed = complete_coordinator_task(task_id=task.task_id, session=session)
        result = apply_coordinator_final_decision(
            experiment_id=experiment_id,
            evidence=CoordinatorFinalDecisionEvidence(
                critic_status="approved",
                critic_objections=(),
                hypothesis_status="testing",
                retest_justification=None,
            ),
            policy=CoordinatorFinalDecisionPolicy(
                critic_status_to_decision={"approved": ExperimentFinalDecision.APPROVED},
                require_retest_justification=True,
            ),
            actor="coordinator_agent",
            session=session,
            memory_service=memory,
        )

        stored_experiment = session.query(Experiment).one()
        stored_task = session.query(CoordinatorTask).one()
        assert permission.allowed is True
        assert claimed is not None
        assert claimed.task_id == task.task_id
        assert completed.status == "completed"
        assert stored_task.status == "completed"
        assert result.current_status == "final_decision"
        assert stored_experiment.status == "final_decision"
        assert stored_experiment.final_decision == "approved"
        assert stored_experiment.completed_at is not None
        assert len(memory.requests) == 1
        assert memory.requests[0].registry_reference == f"registry:experiments/{experiment_id}"
        assert memory.requests[0].metadata["final_decision"] == "approved"
    finally:
        session.close()


def _create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_experiment(session: Session) -> str:
    hypothesis_id = str(uuid4())
    experiment_id = str(uuid4())
    session.add(
        Hypothesis(
            hypothesis_id=hypothesis_id,
            asset_a="AAA",
            asset_b="BBB",
            rationale="Synthetic integration pair",
            source="integration-test",
            created_by="pytest",
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
    )
    session.flush()
    session.add(
        Experiment(
            experiment_id=experiment_id,
            hypothesis_id=hypothesis_id,
            status="reporting",
            current_agent="report_agent",
        )
    )
    session.commit()
    return experiment_id


def _tool_permission_policy() -> AgentToolPermissionPolicy:
    return AgentToolPermissionPolicy(
        agent_scopes={
            "backtest_agent": frozenset(
                {
                    AgentToolPermissionScope.REGISTRY_READ,
                    AgentToolPermissionScope.REGISTRY_WRITE,
                    AgentToolPermissionScope.DATA_ARTIFACTS_READ,
                    AgentToolPermissionScope.REPORTS_WRITE,
                    AgentToolPermissionScope.MEMORY_WRITE,
                }
            ),
        }
    )
