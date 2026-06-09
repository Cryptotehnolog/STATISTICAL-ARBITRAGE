"""Coordinator Agent lifecycle boundary.

This module owns explicit experiment state transitions. It does not run the full
multi-agent workflow yet; task queues and tool permissions remain separate Task 13 work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from sqlalchemy.orm import Session

from stat_arb.memory import MemoryRecordType, MemoryWriteRequest
from stat_arb.storage.models import Experiment


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
        session.query(Experiment)
        .filter(Experiment.experiment_id == str(experiment_id))
        .first()
    )
    if experiment is None:
        raise ValueError(f"experiment is required for Coordinator transition {experiment_id}")
    return experiment


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
