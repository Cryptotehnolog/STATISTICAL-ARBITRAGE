"""Failure handling and recovery policy boundary.

This module classifies operational failures and routes registry mutations through
existing Coordinator and Memory Agent boundaries. It intentionally avoids running
background schedulers or talking to ApeRAG directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from math import isfinite

from sqlalchemy.orm import Session

from stat_arb.agents.coordinator import (
    CoordinatorTransitionRequest,
    ExperimentFinalDecision,
    ExperimentLifecycleStatus,
    MemoryWriter,
    fail_coordinator_task,
    transition_experiment_lifecycle,
)


class FailureEventType(StrEnum):
    """Failure classes recognized by the runtime policy boundary."""

    DATA_OUTAGE = "data_outage"
    API_ERROR = "api_error"
    STALE_DATA = "stale_data"
    ABNORMAL_SPREAD = "abnormal_spread"
    MISSING_FUNDING_RATE = "missing_funding_rate"
    EXPERIMENT_FAILURE = "experiment_failure"
    AGENT_FAILURE = "agent_failure"
    DATABASE_FAILURE = "database_failure"
    MEMORY_BACKEND_FAILURE = "memory_backend_failure"
    RESOURCE_BUDGET_WARNING = "resource_budget_warning"


class FailureSeverity(StrEnum):
    """Failure severity used for operator-facing alerts."""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FailureAction(StrEnum):
    """Explicit action chosen for one failure event."""

    RETRY = "retry"
    PAUSE_EXPERIMENT = "pause_experiment"
    PAUSE_STRATEGY = "pause_strategy"
    REJECT_SIGNAL = "reject_signal"
    QUARANTINE_EXPERIMENT = "quarantine_experiment"
    ENTER_SAFE_MODE = "enter_safe_mode"
    ALERT_OPERATOR = "alert_operator"


@dataclass(frozen=True)
class DataFreshnessPolicy:
    """Explicit data freshness thresholds for outage and stale-signal checks."""

    max_outage_age: timedelta
    max_stale_signal_age: timedelta

    def __post_init__(self) -> None:
        _require_positive_timedelta(self.max_outage_age, label="max_outage_age")
        _require_positive_timedelta(self.max_stale_signal_age, label="max_stale_signal_age")
        if self.max_stale_signal_age > self.max_outage_age:
            raise ValueError("max_stale_signal_age must be less than or equal to max_outage_age")


@dataclass(frozen=True)
class RetryPolicy:
    """Explicit exponential backoff policy for API failures."""

    max_attempts: int
    base_delay: timedelta
    max_delay: timedelta
    multiplier: float

    def __post_init__(self) -> None:
        if isinstance(self.max_attempts, bool) or not isinstance(self.max_attempts, int):
            raise TypeError("max_attempts must be an integer")
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        _require_positive_timedelta(self.base_delay, label="base_delay")
        _require_positive_timedelta(self.max_delay, label="max_delay")
        if self.base_delay > self.max_delay:
            raise ValueError("base_delay must be less than or equal to max_delay")
        if isinstance(self.multiplier, bool) or not isinstance(self.multiplier, int | float):
            raise TypeError("multiplier must be numeric")
        if not isfinite(float(self.multiplier)) or self.multiplier < 1.0:
            raise ValueError("multiplier must be finite and at least 1.0")


@dataclass(frozen=True)
class FailureHandlingPolicy:
    """Explicit policy for abnormal market conditions and runtime safe mode."""

    abnormal_spread_z_score: float
    require_funding_rate: bool
    safe_mode_components: frozenset[str]

    def __post_init__(self) -> None:
        if isinstance(self.abnormal_spread_z_score, bool) or not isinstance(
            self.abnormal_spread_z_score, int | float
        ):
            raise TypeError("abnormal_spread_z_score must be numeric")
        if not isfinite(float(self.abnormal_spread_z_score)) or self.abnormal_spread_z_score <= 0:
            raise ValueError("abnormal_spread_z_score must be finite and positive")
        if not isinstance(self.require_funding_rate, bool):
            raise TypeError("require_funding_rate must be a bool")
        if not isinstance(self.safe_mode_components, frozenset) or not self.safe_mode_components:
            raise ValueError("safe_mode_components must be a non-empty frozenset")
        for component in self.safe_mode_components:
            if not isinstance(component, str) or not component.strip():
                raise ValueError("safe_mode_components must contain non-empty strings")


@dataclass(frozen=True)
class ResourceBudgetPolicy:
    """Explicit runtime resource warning threshold."""

    warn_usage_ratio: float

    def __post_init__(self) -> None:
        if isinstance(self.warn_usage_ratio, bool) or not isinstance(
            self.warn_usage_ratio, int | float
        ):
            raise TypeError("warn_usage_ratio must be numeric")
        if not isfinite(float(self.warn_usage_ratio)) or not 0 < self.warn_usage_ratio <= 1:
            raise ValueError("warn_usage_ratio must be in (0, 1]")


@dataclass(frozen=True)
class FailureEvent:
    """Operator-readable failure event with safe metadata."""

    event_type: FailureEventType
    severity: FailureSeverity
    action: FailureAction
    summary: str
    observed_at: datetime
    metadata: dict[str, object] = field(default_factory=dict)
    requires_manual_approval: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, FailureEventType):
            raise TypeError("event_type must be a FailureEventType")
        if not isinstance(self.severity, FailureSeverity):
            raise TypeError("severity must be a FailureSeverity")
        if not isinstance(self.action, FailureAction):
            raise TypeError("action must be a FailureAction")
        if not self.summary.strip():
            raise ValueError("summary is required")
        _require_aware_datetime(self.observed_at, label="observed_at")
        if not isinstance(self.requires_manual_approval, bool):
            raise TypeError("requires_manual_approval must be a bool")


@dataclass(frozen=True)
class RetryDecision:
    """Decision for one API retry attempt."""

    should_retry: bool
    delay: timedelta | None
    event: FailureEvent


@dataclass(frozen=True)
class AbnormalConditionEvidence:
    """Market condition evidence checked before strategy execution."""

    strategy_id: str
    spread_z_score: float
    funding_rate_available: bool
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.strategy_id.strip():
            raise ValueError("strategy_id is required")
        if isinstance(self.spread_z_score, bool) or not isinstance(self.spread_z_score, int | float):
            raise TypeError("spread_z_score must be numeric")
        if not isfinite(float(self.spread_z_score)):
            raise ValueError("spread_z_score must be finite")
        if not isinstance(self.funding_rate_available, bool):
            raise TypeError("funding_rate_available must be a bool")
        _require_aware_datetime(self.observed_at, label="observed_at")


@dataclass(frozen=True)
class ResourceUsageSnapshot:
    """Point-in-time runtime resource usage against explicit budgets."""

    observed_at: datetime
    ram_used_gb: float
    ram_budget_gb: float
    disk_used_gb: float
    disk_budget_gb: float

    def __post_init__(self) -> None:
        _require_aware_datetime(self.observed_at, label="observed_at")
        _require_non_negative_number(self.ram_used_gb, label="ram_used_gb")
        _require_positive_number(self.ram_budget_gb, label="ram_budget_gb")
        _require_non_negative_number(self.disk_used_gb, label="disk_used_gb")
        _require_positive_number(self.disk_budget_gb, label="disk_budget_gb")


@dataclass(frozen=True)
class FailureHandlingResult:
    """Registry/memory side effects performed for one handled failure."""

    event: FailureEvent
    registry_mutated: bool
    memory_written: bool


def detect_data_outage(
    *,
    symbol: str,
    source: str,
    latest_observation_at: datetime,
    observed_at: datetime,
    policy: DataFreshnessPolicy,
) -> FailureEvent | None:
    """Detect missing data beyond the explicit outage policy."""
    normalized_symbol = _require_text(symbol, label="symbol")
    normalized_source = _require_text(source, label="source")
    _require_aware_datetime(latest_observation_at, label="latest_observation_at")
    _require_aware_datetime(observed_at, label="observed_at")
    age = observed_at - latest_observation_at
    if age <= policy.max_outage_age:
        return None
    return FailureEvent(
        event_type=FailureEventType.DATA_OUTAGE,
        severity=FailureSeverity.ERROR,
        action=FailureAction.PAUSE_EXPERIMENT,
        summary=(
            f"Data outage detected for {normalized_symbol} from {normalized_source}: "
            f"latest observation age {age} exceeds {policy.max_outage_age}."
        ),
        observed_at=observed_at,
        metadata={
            "symbol": normalized_symbol,
            "source": normalized_source,
            "latest_observation_at": latest_observation_at.isoformat(),
            "age_seconds": age.total_seconds(),
            "threshold_seconds": policy.max_outage_age.total_seconds(),
        },
    )


def detect_stale_data(
    *,
    symbol: str,
    source: str,
    latest_price_at: datetime,
    observed_at: datetime,
    policy: DataFreshnessPolicy,
) -> FailureEvent | None:
    """Detect stale prices that should reject a signal candidate."""
    normalized_symbol = _require_text(symbol, label="symbol")
    normalized_source = _require_text(source, label="source")
    _require_aware_datetime(latest_price_at, label="latest_price_at")
    _require_aware_datetime(observed_at, label="observed_at")
    age = observed_at - latest_price_at
    if age <= policy.max_stale_signal_age:
        return None
    return FailureEvent(
        event_type=FailureEventType.STALE_DATA,
        severity=FailureSeverity.WARNING,
        action=FailureAction.REJECT_SIGNAL,
        summary=(
            f"Stale price detected for {normalized_symbol} from {normalized_source}: "
            f"price age {age} exceeds {policy.max_stale_signal_age}."
        ),
        observed_at=observed_at,
        metadata={
            "symbol": normalized_symbol,
            "source": normalized_source,
            "latest_price_at": latest_price_at.isoformat(),
            "age_seconds": age.total_seconds(),
            "threshold_seconds": policy.max_stale_signal_age.total_seconds(),
        },
    )


def plan_api_retry(
    *,
    error_summary: str,
    attempt_number: int,
    policy: RetryPolicy,
    observed_at: datetime | None = None,
) -> RetryDecision:
    """Plan one API retry using exponential backoff and explicit exhaustion behavior."""
    normalized_error = _require_text(error_summary, label="error_summary")
    if isinstance(attempt_number, bool) or not isinstance(attempt_number, int):
        raise TypeError("attempt_number must be an integer")
    if attempt_number <= 0:
        raise ValueError("attempt_number must be positive")
    event_time = observed_at or datetime.now(UTC)
    _require_aware_datetime(event_time, label="observed_at")

    if attempt_number >= policy.max_attempts:
        return RetryDecision(
            should_retry=False,
            delay=None,
            event=FailureEvent(
                event_type=FailureEventType.API_ERROR,
                severity=FailureSeverity.ERROR,
                action=FailureAction.ALERT_OPERATOR,
                summary=f"API retry budget exhausted after attempt {attempt_number}: {normalized_error}",
                observed_at=event_time,
                metadata={
                    "attempt_number": attempt_number,
                    "max_attempts": policy.max_attempts,
                    "error_summary": normalized_error,
                },
            ),
        )

    delay_seconds = min(
        policy.base_delay.total_seconds() * (policy.multiplier ** (attempt_number - 1)),
        policy.max_delay.total_seconds(),
    )
    delay = timedelta(seconds=delay_seconds)
    return RetryDecision(
        should_retry=True,
        delay=delay,
        event=FailureEvent(
            event_type=FailureEventType.API_ERROR,
            severity=FailureSeverity.WARNING,
            action=FailureAction.RETRY,
            summary=f"API failure will be retried after {delay}: {normalized_error}",
            observed_at=event_time,
            metadata={
                "attempt_number": attempt_number,
                "max_attempts": policy.max_attempts,
                "delay_seconds": delay.total_seconds(),
                "error_summary": normalized_error,
            },
        ),
    )


def classify_abnormal_conditions(
    evidence: AbnormalConditionEvidence,
    *,
    policy: FailureHandlingPolicy,
) -> list[FailureEvent]:
    """Classify market conditions that should pause strategy execution."""
    events: list[FailureEvent] = []
    if abs(evidence.spread_z_score) >= policy.abnormal_spread_z_score:
        events.append(
            FailureEvent(
                event_type=FailureEventType.ABNORMAL_SPREAD,
                severity=FailureSeverity.ERROR,
                action=FailureAction.PAUSE_STRATEGY,
                summary=(
                    f"Strategy {evidence.strategy_id} has abnormal spread z-score "
                    f"{evidence.spread_z_score}."
                ),
                observed_at=evidence.observed_at,
                metadata={
                    "strategy_id": evidence.strategy_id,
                    "spread_z_score": evidence.spread_z_score,
                    "threshold": policy.abnormal_spread_z_score,
                },
            )
        )
    if policy.require_funding_rate and not evidence.funding_rate_available:
        events.append(
            FailureEvent(
                event_type=FailureEventType.MISSING_FUNDING_RATE,
                severity=FailureSeverity.ERROR,
                action=FailureAction.PAUSE_STRATEGY,
                summary=f"Strategy {evidence.strategy_id} is missing required funding rate data.",
                observed_at=evidence.observed_at,
                metadata={
                    "strategy_id": evidence.strategy_id,
                    "require_funding_rate": policy.require_funding_rate,
                },
            )
        )
    return events


def handle_agent_or_backtest_failure(
    *,
    experiment_id: str,
    failed_stage: ExperimentLifecycleStatus,
    error_summary: str,
    actor: str,
    session: Session,
    memory_service: MemoryWriter,
    coordinator_task_id: str | None = None,
) -> FailureHandlingResult:
    """Persist an agent/backtest failure through Coordinator and Memory boundaries."""
    normalized_error = _require_text(error_summary, label="error_summary")
    normalized_actor = _require_text(actor, label="actor")
    event_type = (
        FailureEventType.EXPERIMENT_FAILURE
        if failed_stage == ExperimentLifecycleStatus.BACKTESTING
        else FailureEventType.AGENT_FAILURE
    )
    action = (
        FailureAction.QUARANTINE_EXPERIMENT
        if failed_stage == ExperimentLifecycleStatus.BACKTESTING
        else FailureAction.ALERT_OPERATOR
    )
    if coordinator_task_id is not None:
        fail_coordinator_task(
            task_id=coordinator_task_id,
            error_summary=normalized_error,
            session=session,
        )
    registry_mutated = coordinator_task_id is not None
    memory_written = False
    if action == FailureAction.QUARANTINE_EXPERIMENT:
        result = transition_experiment_lifecycle(
            CoordinatorTransitionRequest(
                experiment_id=experiment_id,
                target_status=ExperimentLifecycleStatus.FINAL_DECISION,
                reason=f"{failed_stage.value} failed: {normalized_error}",
                actor=normalized_actor,
                final_decision=ExperimentFinalDecision.QUARANTINED,
            ),
            session=session,
            memory_service=memory_service,
        )
        registry_mutated = True
        memory_written = result.memory_written

    return FailureHandlingResult(
        event=FailureEvent(
            event_type=event_type,
            severity=FailureSeverity.ERROR,
            action=action,
            summary=f"{failed_stage.value} failure handled: {normalized_error}",
            observed_at=datetime.now(UTC),
            metadata={
                "experiment_id": str(experiment_id),
                "failed_stage": failed_stage.value,
                "actor": normalized_actor,
                "coordinator_task_id": coordinator_task_id,
            },
        ),
        registry_mutated=registry_mutated,
        memory_written=memory_written,
    )


def handle_runtime_dependency_failure(
    *,
    component: str,
    error_summary: str,
    policy: FailureHandlingPolicy,
    observed_at: datetime | None = None,
) -> FailureEvent:
    """Classify database or memory failure and enter safe mode when policy requires it."""
    normalized_component = _require_text(component, label="component").casefold()
    normalized_error = _require_text(error_summary, label="error_summary")
    event_time = observed_at or datetime.now(UTC)
    _require_aware_datetime(event_time, label="observed_at")
    if normalized_component not in policy.safe_mode_components:
        return FailureEvent(
            event_type=_dependency_event_type(normalized_component),
            severity=FailureSeverity.ERROR,
            action=FailureAction.ALERT_OPERATOR,
            summary=f"{normalized_component} failure requires operator attention: {normalized_error}",
            observed_at=event_time,
            metadata={
                "component": normalized_component,
                "error_summary": normalized_error,
            },
        )
    return FailureEvent(
        event_type=_dependency_event_type(normalized_component),
        severity=FailureSeverity.CRITICAL,
        action=FailureAction.ENTER_SAFE_MODE,
        summary=f"{normalized_component} failure triggered safe mode: {normalized_error}",
        observed_at=event_time,
        metadata={
            "component": normalized_component,
            "error_summary": normalized_error,
            "recovery": "queue_replay_after_operator_approval",
        },
        requires_manual_approval=True,
    )


def evaluate_resource_budget(
    snapshot: ResourceUsageSnapshot,
    *,
    policy: ResourceBudgetPolicy,
) -> list[FailureEvent]:
    """Warn when local runtime resources exceed explicit budgets."""
    checks = (
        ("ram", snapshot.ram_used_gb, snapshot.ram_budget_gb),
        ("disk", snapshot.disk_used_gb, snapshot.disk_budget_gb),
    )
    events: list[FailureEvent] = []
    for resource, used, budget in checks:
        usage_ratio = used / budget
        if usage_ratio >= policy.warn_usage_ratio:
            events.append(
                FailureEvent(
                    event_type=FailureEventType.RESOURCE_BUDGET_WARNING,
                    severity=FailureSeverity.WARNING,
                    action=FailureAction.ALERT_OPERATOR,
                    summary=(
                        f"Runtime {resource} usage {usage_ratio:.2%} exceeds configured "
                        f"warning ratio {policy.warn_usage_ratio:.2%}."
                    ),
                    observed_at=snapshot.observed_at,
                    metadata={
                        "resource": resource,
                        "used_gb": used,
                        "budget_gb": budget,
                        "usage_ratio": usage_ratio,
                        "warn_usage_ratio": policy.warn_usage_ratio,
                    },
                )
            )
    return events


def _dependency_event_type(component: str) -> FailureEventType:
    if component == "database":
        return FailureEventType.DATABASE_FAILURE
    if component == "memory":
        return FailureEventType.MEMORY_BACKEND_FAILURE
    raise ValueError("component must be database or memory")


def _require_text(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")
    return value.strip()


def _require_aware_datetime(value: datetime, *, label: str) -> None:
    if not isinstance(value, datetime):
        raise TypeError(f"{label} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware")


def _require_positive_timedelta(value: timedelta, *, label: str) -> None:
    if not isinstance(value, timedelta):
        raise TypeError(f"{label} must be a timedelta")
    if value <= timedelta(0):
        raise ValueError(f"{label} must be positive")


def _require_non_negative_number(value: float, *, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{label} must be numeric")
    if not isfinite(float(value)) or value < 0:
        raise ValueError(f"{label} must be finite and non-negative")


def _require_positive_number(value: float, *, label: str) -> None:
    _require_non_negative_number(value, label=label)
    if value <= 0:
        raise ValueError(f"{label} must be positive")
