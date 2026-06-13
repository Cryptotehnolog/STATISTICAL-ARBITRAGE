"""Coordinator Agent lifecycle boundary.

This module owns explicit experiment state transitions. It does not run the full
multi-agent workflow yet; task queues and tool permissions remain separate Task 13 work.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from math import isfinite
from typing import Protocol

from sqlalchemy.orm import Session

from stat_arb.memory import MemoryRecordType, MemoryWriteRequest
from stat_arb.storage.models import CoordinatorTask, Experiment


class MemoryWriter(Protocol):
    """Minimal Memory Agent service protocol used by this boundary."""

    def write(self, request: MemoryWriteRequest) -> object:
        """Write a policy-approved memory record."""


class ExperimentLifecycleStatus(StrEnum):
    """Allowed experiment lifecycle states."""

    NEW = "new"
    DATA_VALIDATION = "data_validation"
    STATISTICAL_TESTING = "statistical_testing"
    BACKTESTING = "backtesting"
    CRITIC_REVIEW = "critic_review"
    REPORTING = "reporting"
    FINAL_DECISION = "final_decision"


class ExperimentFinalDecision(StrEnum):
    """Allowed final Coordinator decisions."""

    REJECTED = "rejected"
    QUARANTINED = "quarantined"
    APPROVED = "approved"
    ELIGIBLE_FOR_DEMO = "eligible_for_demo"


class CoordinatorTaskStatus(StrEnum):
    """Allowed durable task queue statuses."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentToolPermissionScope(StrEnum):
    """Tool scopes controlled by Coordinator before agent execution."""

    REGISTRY_READ = "registry_read"
    REGISTRY_WRITE = "registry_write"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    DATA_ARTIFACTS_READ = "data_artifacts_read"
    DATA_ARTIFACTS_WRITE = "data_artifacts_write"
    REPORTS_READ = "reports_read"
    REPORTS_WRITE = "reports_write"
    SECRETS_READ = "secrets_read"
    SECRETS_WRITE = "secrets_write"


@dataclass(frozen=True)
class CoordinatorTransitionRequest:
    """Request to move one experiment through the lifecycle state machine."""

    experiment_id: str
    target_status: ExperimentLifecycleStatus
    reason: str
    actor: str
    final_decision: ExperimentFinalDecision | None = None

    def __post_init__(self) -> None:
        if not str(self.experiment_id).strip():
            raise ValueError("experiment_id is required")
        if not self.actor.strip():
            raise ValueError("actor is required")


@dataclass(frozen=True)
class CoordinatorApprovalActionRequest:
    """Audited manual approve/reject action for dashboard or operator workflows."""

    experiment_id: str
    final_decision: ExperimentFinalDecision
    reason: str
    actor: str

    def __post_init__(self) -> None:
        if not str(self.experiment_id).strip():
            raise ValueError("experiment_id is required")
        if not isinstance(self.final_decision, ExperimentFinalDecision):
            raise TypeError("final_decision must be an ExperimentFinalDecision")
        if self.final_decision == ExperimentFinalDecision.ELIGIBLE_FOR_DEMO:
            raise ValueError("approval actions must approve, reject, or quarantine")
        if not self.reason.strip():
            raise ValueError("reason is required")
        if not self.actor.strip():
            raise ValueError("actor is required")


@dataclass(frozen=True)
class CoordinatorTaskRequest:
    """Request to enqueue one durable Coordinator task."""

    experiment_id: str
    task_type: str
    agent_name: str
    priority: int
    max_attempts: int
    payload: dict[str, object]

    def __post_init__(self) -> None:
        if not str(self.experiment_id).strip():
            raise ValueError("experiment_id is required")
        if not self.task_type.strip():
            raise ValueError("task_type is required")
        if not self.agent_name.strip():
            raise ValueError("agent_name is required")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError("priority must be an integer")
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise TypeError("max_attempts must be an integer")
        if self.priority < 0:
            raise ValueError("priority must be non-negative")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        _validate_json_like_payload(self.payload)


@dataclass(frozen=True)
class AgentToolPermissionRequest:
    """Request to validate one agent tool access."""

    agent_name: str
    scope: AgentToolPermissionScope
    reason: str

    def __post_init__(self) -> None:
        if not self.agent_name.strip():
            raise ValueError("agent_name is required")
        if not isinstance(self.scope, AgentToolPermissionScope):
            raise TypeError("scope must be an AgentToolPermissionScope")
        if not self.reason.strip():
            raise ValueError("reason is required")


@dataclass(frozen=True)
class AgentToolPermissionPolicy:
    """Explicit agent-to-tool-scope allow list."""

    agent_scopes: Mapping[str, frozenset[AgentToolPermissionScope]]

    def __post_init__(self) -> None:
        if not self.agent_scopes:
            raise ValueError("agent_scopes is required")
        for agent_name, scopes in self.agent_scopes.items():
            if not isinstance(agent_name, str) or not agent_name.strip():
                raise ValueError("agent names in permission policy must be non-empty strings")
            if not isinstance(scopes, frozenset):
                raise TypeError("agent permission scopes must be frozensets")
            if not scopes:
                raise ValueError(f"agent {agent_name} must have at least one scope")
            for scope in scopes:
                if not isinstance(scope, AgentToolPermissionScope):
                    raise TypeError("permission scopes must be AgentToolPermissionScope values")


@dataclass(frozen=True)
class AgentToolPermissionResult:
    """Result of one Coordinator tool permission check."""

    allowed: bool
    agent_name: str
    scope: AgentToolPermissionScope
    reason: str


@dataclass(frozen=True)
class CoordinatorResourcePolicy:
    """Explicit resource limits for claiming Coordinator queue work."""

    max_running_tasks: int
    max_running_tasks_per_agent: dict[str, int]

    def __post_init__(self) -> None:
        if isinstance(self.max_running_tasks, bool) or not isinstance(self.max_running_tasks, int):
            raise TypeError("max_running_tasks must be an integer")
        if self.max_running_tasks <= 0:
            raise ValueError("max_running_tasks must be positive")
        if not self.max_running_tasks_per_agent:
            raise ValueError("max_running_tasks_per_agent is required")
        for agent_name, limit in self.max_running_tasks_per_agent.items():
            if not isinstance(agent_name, str) or not agent_name.strip():
                raise ValueError("agent names in resource policy must be non-empty strings")
            if isinstance(limit, bool) or not isinstance(limit, int):
                raise TypeError("per-agent running task limits must be integers")
            if limit <= 0:
                raise ValueError("per-agent running task limits must be positive")


@dataclass(frozen=True)
class CoordinatorFinalDecisionPolicy:
    """Explicit policy for converting Critic status into Coordinator final decisions."""

    critic_status_to_decision: Mapping[str, ExperimentFinalDecision]
    require_retest_justification: bool

    def __post_init__(self) -> None:
        if not self.critic_status_to_decision:
            raise ValueError("critic_status_to_decision is required")
        if not isinstance(self.require_retest_justification, bool):
            raise TypeError("require_retest_justification must be a bool")
        for critic_status, final_decision in self.critic_status_to_decision.items():
            if not isinstance(critic_status, str) or not critic_status.strip():
                raise ValueError("critic status mappings must use non-empty strings")
            if not isinstance(final_decision, ExperimentFinalDecision):
                raise TypeError("critic status mappings must map to ExperimentFinalDecision")


@dataclass(frozen=True)
class CoordinatorFinalDecisionEvidence:
    """Evidence used by Coordinator to choose a final experiment decision."""

    critic_status: str
    critic_objections: tuple[str, ...]
    hypothesis_status: str
    retest_justification: str | None

    def __post_init__(self) -> None:
        if not self.critic_status.strip():
            raise ValueError("critic_status is required")
        if not self.hypothesis_status.strip():
            raise ValueError("hypothesis_status is required")
        _validate_non_empty_texts(self.critic_objections, label="critic_objections")
        if self.retest_justification is not None and not isinstance(self.retest_justification, str):
            raise TypeError("retest_justification must be a string or None")


@dataclass(frozen=True)
class CoordinatorFinalDecisionResult:
    """Coordinator final decision plan before persistence."""

    final_decision: ExperimentFinalDecision
    reason: str
    checked_rules: tuple[str, ...]


@dataclass(frozen=True)
class CoordinatorTransitionResult:
    """Result of a registry-backed Coordinator lifecycle transition."""

    experiment: Experiment
    previous_status: ExperimentLifecycleStatus
    current_status: ExperimentLifecycleStatus
    memory_written: bool


ALLOWED_TRANSITIONS: dict[ExperimentLifecycleStatus, frozenset[ExperimentLifecycleStatus]] = {
    ExperimentLifecycleStatus.NEW: frozenset({ExperimentLifecycleStatus.DATA_VALIDATION}),
    ExperimentLifecycleStatus.DATA_VALIDATION: frozenset(
        {
            ExperimentLifecycleStatus.STATISTICAL_TESTING,
            ExperimentLifecycleStatus.FINAL_DECISION,
        }
    ),
    ExperimentLifecycleStatus.STATISTICAL_TESTING: frozenset(
        {
            ExperimentLifecycleStatus.BACKTESTING,
            ExperimentLifecycleStatus.FINAL_DECISION,
        }
    ),
    ExperimentLifecycleStatus.BACKTESTING: frozenset(
        {
            ExperimentLifecycleStatus.CRITIC_REVIEW,
            ExperimentLifecycleStatus.FINAL_DECISION,
        }
    ),
    ExperimentLifecycleStatus.CRITIC_REVIEW: frozenset(
        {
            ExperimentLifecycleStatus.REPORTING,
            ExperimentLifecycleStatus.FINAL_DECISION,
        }
    ),
    ExperimentLifecycleStatus.REPORTING: frozenset({ExperimentLifecycleStatus.FINAL_DECISION}),
    ExperimentLifecycleStatus.FINAL_DECISION: frozenset(),
}

AGENT_BY_STATUS: dict[ExperimentLifecycleStatus, str | None] = {
    ExperimentLifecycleStatus.NEW: None,
    ExperimentLifecycleStatus.DATA_VALIDATION: "data_agent",
    ExperimentLifecycleStatus.STATISTICAL_TESTING: "statistical_testing_agent",
    ExperimentLifecycleStatus.BACKTESTING: "backtest_agent",
    ExperimentLifecycleStatus.CRITIC_REVIEW: "critic_agent",
    ExperimentLifecycleStatus.REPORTING: "report_agent",
    ExperimentLifecycleStatus.FINAL_DECISION: None,
}


def enqueue_coordinator_task(
    request: CoordinatorTaskRequest,
    *,
    session: Session,
) -> CoordinatorTask:
    """Persist one pending task for the Coordinator queue."""
    _require_experiment(session, experiment_id=request.experiment_id)
    task = CoordinatorTask(
        experiment_id=str(request.experiment_id),
        task_type=request.task_type.strip(),
        agent_name=request.agent_name.strip(),
        priority=request.priority,
        status=CoordinatorTaskStatus.PENDING.value,
        attempt_count=0,
        max_attempts=request.max_attempts,
        payload=request.payload,
        last_error=None,
    )
    session.add(task)
    session.flush()
    return task


def claim_next_coordinator_task(
    *,
    agent_name: str,
    policy: CoordinatorResourcePolicy,
    session: Session,
) -> CoordinatorTask | None:
    """Claim the highest-priority pending task for one agent."""
    if not agent_name.strip():
        raise ValueError("agent_name is required")
    normalized_agent = agent_name.strip()
    _validate_agent_has_resource_policy(normalized_agent, policy)
    if _running_task_count(session) >= policy.max_running_tasks:
        return None
    if (
        _running_task_count(session, agent_name=normalized_agent)
        >= policy.max_running_tasks_per_agent[normalized_agent]
    ):
        return None
    task = (
        session.query(CoordinatorTask)
        .filter(
            CoordinatorTask.agent_name == normalized_agent,
            CoordinatorTask.status == CoordinatorTaskStatus.PENDING.value,
        )
        .order_by(CoordinatorTask.priority.asc(), CoordinatorTask.created_at.asc())
        .first()
    )
    if task is None:
        return None
    task.status = CoordinatorTaskStatus.RUNNING.value
    task.attempt_count += 1
    task.started_at = _utc_now()
    task.completed_at = None
    session.flush()
    return task


def claim_coordinator_task_by_id(
    *,
    task_id: str,
    policy: CoordinatorResourcePolicy,
    session: Session,
) -> CoordinatorTask | None:
    """Claim one explicit pending Coordinator task while enforcing resource limits."""
    if not str(task_id).strip():
        raise ValueError("task_id is required")
    task = _require_task(session, task_id=task_id)
    if task.status != CoordinatorTaskStatus.PENDING.value:
        raise ValueError("only pending Coordinator tasks can be claimed")
    _validate_agent_has_resource_policy(task.agent_name, policy)
    if _running_task_count(session) >= policy.max_running_tasks:
        return None
    if (
        _running_task_count(session, agent_name=task.agent_name)
        >= policy.max_running_tasks_per_agent[task.agent_name]
    ):
        return None
    task.status = CoordinatorTaskStatus.RUNNING.value
    task.attempt_count += 1
    task.started_at = _utc_now()
    task.completed_at = None
    session.flush()
    return task


def fail_coordinator_task(
    *,
    task_id: str,
    error_summary: str,
    session: Session,
) -> CoordinatorTask:
    """Record a task failure and either retry or exhaust it."""
    task = _require_task(session, task_id=task_id)
    if task.status != CoordinatorTaskStatus.RUNNING.value:
        raise ValueError("only running Coordinator tasks can fail")
    if not error_summary.strip():
        raise ValueError("error_summary is required")
    task.last_error = error_summary.strip()
    task.started_at = None
    if task.attempt_count < task.max_attempts:
        task.status = CoordinatorTaskStatus.PENDING.value
        task.completed_at = None
    else:
        task.status = CoordinatorTaskStatus.FAILED.value
        task.completed_at = _utc_now()
    session.flush()
    return task


def complete_coordinator_task(
    *,
    task_id: str,
    session: Session,
) -> CoordinatorTask:
    """Mark one running Coordinator task as completed."""
    task = _require_task(session, task_id=task_id)
    if task.status != CoordinatorTaskStatus.RUNNING.value:
        raise ValueError("only running Coordinator tasks can complete")
    task.status = CoordinatorTaskStatus.COMPLETED.value
    task.completed_at = _utc_now()
    session.flush()
    return task


def list_recoverable_coordinator_tasks(*, session: Session) -> list[CoordinatorTask]:
    """Return unfinished running tasks that may need recovery after process restart."""
    return (
        session.query(CoordinatorTask)
        .filter(CoordinatorTask.status == CoordinatorTaskStatus.RUNNING.value)
        .order_by(CoordinatorTask.priority.asc(), CoordinatorTask.started_at.asc())
        .all()
    )


def enforce_agent_tool_permission(
    request: AgentToolPermissionRequest,
    *,
    policy: AgentToolPermissionPolicy,
) -> AgentToolPermissionResult:
    """Validate one agent tool access against an explicit allow list."""
    agent_name = request.agent_name.strip()
    allowed_scopes = policy.agent_scopes.get(agent_name)
    if allowed_scopes is None:
        raise PermissionError(f"no permissions configured for agent {agent_name}")
    if request.scope not in allowed_scopes:
        raise PermissionError(
            f"agent {agent_name} is not allowed to use scope {request.scope.value}"
        )
    return AgentToolPermissionResult(
        allowed=True,
        agent_name=agent_name,
        scope=request.scope,
        reason=f"allowed: {request.reason.strip()}",
    )


def decide_coordinator_final_decision(
    evidence: CoordinatorFinalDecisionEvidence,
    *,
    policy: CoordinatorFinalDecisionPolicy,
) -> CoordinatorFinalDecisionResult:
    """Choose a final Coordinator decision without writing registry or memory state."""
    checked_rules = ["critic_status_mapping"]
    normalized_status = evidence.critic_status.strip()
    final_decision = policy.critic_status_to_decision.get(normalized_status)
    if final_decision is None:
        raise ValueError(f"no final decision mapping for critic status {normalized_status}")

    if policy.require_retest_justification:
        checked_rules.append("retest_justification")
        if _is_retest(evidence.hypothesis_status) and not (
            evidence.retest_justification and evidence.retest_justification.strip()
        ):
            raise ValueError("retest_justification is required for retest hypotheses")

    reason = _final_decision_reason(evidence, final_decision)
    return CoordinatorFinalDecisionResult(
        final_decision=final_decision,
        reason=reason,
        checked_rules=tuple(checked_rules),
    )


def apply_coordinator_final_decision(
    *,
    experiment_id: str,
    evidence: CoordinatorFinalDecisionEvidence,
    policy: CoordinatorFinalDecisionPolicy,
    actor: str,
    session: Session,
    memory_service: MemoryWriter,
) -> CoordinatorTransitionResult:
    """Persist one final decision through lifecycle transition and Memory Agent policy."""
    decision = decide_coordinator_final_decision(evidence, policy=policy)
    return transition_experiment_lifecycle(
        CoordinatorTransitionRequest(
            experiment_id=experiment_id,
            target_status=ExperimentLifecycleStatus.FINAL_DECISION,
            reason=decision.reason,
            actor=actor,
            final_decision=decision.final_decision,
        ),
        session=session,
        memory_service=memory_service,
    )


def apply_coordinator_approval_action(
    request: CoordinatorApprovalActionRequest,
    *,
    session: Session,
    memory_service: MemoryWriter,
) -> CoordinatorTransitionResult:
    """Apply one audited human approval action through Coordinator lifecycle boundary."""
    return transition_experiment_lifecycle(
        CoordinatorTransitionRequest(
            experiment_id=request.experiment_id,
            target_status=ExperimentLifecycleStatus.FINAL_DECISION,
            reason=request.reason,
            actor=request.actor,
            final_decision=request.final_decision,
        ),
        session=session,
        memory_service=memory_service,
    )


def _running_task_count(session: Session, *, agent_name: str | None = None) -> int:
    query = session.query(CoordinatorTask).filter(
        CoordinatorTask.status == CoordinatorTaskStatus.RUNNING.value
    )
    if agent_name is not None:
        query = query.filter(CoordinatorTask.agent_name == agent_name)
    return int(query.count())


def _validate_agent_has_resource_policy(
    agent_name: str,
    policy: CoordinatorResourcePolicy,
) -> None:
    if agent_name not in policy.max_running_tasks_per_agent:
        raise ValueError(f"resource policy is required for agent {agent_name}")


def _is_retest(hypothesis_status: str) -> bool:
    return hypothesis_status.strip().casefold() == "retest"


def _final_decision_reason(
    evidence: CoordinatorFinalDecisionEvidence,
    final_decision: ExperimentFinalDecision,
) -> str:
    reason_parts = [
        f"Critic status {evidence.critic_status.strip()} mapped to {final_decision.value}."
    ]
    if evidence.critic_objections:
        reason_parts.append("Critic objections: " + "; ".join(evidence.critic_objections))
    if evidence.retest_justification and evidence.retest_justification.strip():
        reason_parts.append(f"Retest justification: {evidence.retest_justification.strip()}")
    return " ".join(reason_parts)


def transition_experiment_lifecycle(
    request: CoordinatorTransitionRequest,
    *,
    session: Session,
    memory_service: MemoryWriter | None = None,
) -> CoordinatorTransitionResult:
    """Persist one allowed lifecycle transition and write a policy-safe memory event."""
    experiment = _require_experiment(session, experiment_id=request.experiment_id)
    previous_status = _parse_status(experiment.status)
    _validate_transition(previous_status, request)

    experiment.status = request.target_status.value
    experiment.current_agent = AGENT_BY_STATUS[request.target_status]
    if request.target_status == ExperimentLifecycleStatus.FINAL_DECISION:
        _apply_final_decision(experiment, request)

    session.flush()

    memory_written = False
    if memory_service is not None:
        memory_service.write(_memory_request_for(experiment, previous_status, request))
        memory_written = True

    return CoordinatorTransitionResult(
        experiment=experiment,
        previous_status=previous_status,
        current_status=request.target_status,
        memory_written=memory_written,
    )


def _require_experiment(session: Session, *, experiment_id: str) -> Experiment:
    experiment = (
        session.query(Experiment).filter(Experiment.experiment_id == str(experiment_id)).first()
    )
    if experiment is None:
        raise ValueError(f"experiment is required for Coordinator transition {experiment_id}")
    return experiment


def _require_task(session: Session, *, task_id: str) -> CoordinatorTask:
    task = session.query(CoordinatorTask).filter(CoordinatorTask.task_id == str(task_id)).first()
    if task is None:
        raise ValueError(f"Coordinator task is required: {task_id}")
    return task


def _parse_status(status: str) -> ExperimentLifecycleStatus:
    try:
        return ExperimentLifecycleStatus(status)
    except ValueError as exc:
        raise ValueError(f"Unknown experiment lifecycle status: {status}") from exc


def _validate_transition(
    previous_status: ExperimentLifecycleStatus,
    request: CoordinatorTransitionRequest,
) -> None:
    allowed = ALLOWED_TRANSITIONS[previous_status]
    if request.target_status not in allowed:
        allowed_text = ", ".join(status.value for status in sorted(allowed, key=str))
        raise ValueError(
            "Invalid lifecycle transition: "
            f"{previous_status.value} -> {request.target_status.value}. "
            f"Allowed next states: {allowed_text or 'none'}"
        )
    if request.target_status == ExperimentLifecycleStatus.FINAL_DECISION:
        if request.final_decision is None:
            raise ValueError("final_decision is required for final lifecycle transition")
        if (
            request.final_decision
            in {ExperimentFinalDecision.REJECTED, ExperimentFinalDecision.QUARANTINED}
            and not request.reason.strip()
        ):
            raise ValueError("reason is required for rejected or quarantined final decisions")
    elif request.final_decision is not None:
        raise ValueError("final_decision is only allowed for final lifecycle transition")


def _apply_final_decision(
    experiment: Experiment,
    request: CoordinatorTransitionRequest,
) -> None:
    if request.final_decision is None:
        raise ValueError("final_decision is required for final lifecycle transition")
    experiment.final_decision = request.final_decision.value
    if request.final_decision in {
        ExperimentFinalDecision.REJECTED,
        ExperimentFinalDecision.QUARANTINED,
    }:
        experiment.rejection_reason = request.reason.strip()
    else:
        experiment.rejection_reason = None
    experiment.completed_at = datetime.now(UTC).replace(tzinfo=None)


def _memory_request_for(
    experiment: Experiment,
    previous_status: ExperimentLifecycleStatus,
    request: CoordinatorTransitionRequest,
) -> MemoryWriteRequest:
    body = (
        "Lifecycle transition recorded. The structured experiment state is stored in the "
        "registry; this memory event only keeps the high-level status change and reason."
    )
    metadata = {
        "previous_status": previous_status.value,
        "current_status": request.target_status.value,
        "actor": request.actor,
    }
    if request.final_decision is not None:
        metadata["final_decision"] = request.final_decision.value
    return MemoryWriteRequest(
        record_type=MemoryRecordType.AGENT_DECISION,
        title="Coordinator lifecycle transition",
        body=f"{body}\n\nReason: {request.reason.strip()}",
        source_id=experiment.experiment_id,
        registry_reference=f"registry:experiments/{experiment.experiment_id}",
        tags=["coordinator", "experiment-lifecycle", request.target_status.value],
        metadata=metadata,
    )


def _utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _validate_json_like_payload(payload: object) -> None:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dictionary")
    for key, value in payload.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("payload keys must be non-empty strings")
        _validate_json_like_value(value)


def _validate_json_like_value(value: object) -> None:
    if value is None or isinstance(value, str | bool | int):
        return
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("payload floats must be finite")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_like_value(item)
        return
    if isinstance(value, dict):
        _validate_json_like_payload(value)
        return
    raise TypeError("payload values must be JSON-like")


def _validate_non_empty_texts(values: tuple[str, ...], *, label: str) -> None:
    if not isinstance(values, tuple):
        raise TypeError(f"{label} must be a tuple")
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{label} must contain only non-empty strings")
