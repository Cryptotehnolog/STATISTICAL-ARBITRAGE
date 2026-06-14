"""Unit tests for failure handling and recovery policy boundaries."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents.coordinator import ExperimentLifecycleStatus
from stat_arb.agents.failure_handling import (
    AbnormalConditionEvidence,
    DataFreshnessPolicy,
    FailureAction,
    FailureEventType,
    FailureHandlingPolicy,
    FailureSeverity,
    ResourceBudgetPolicy,
    ResourceUsageSnapshot,
    RetryPolicy,
    classify_abnormal_conditions,
    detect_data_outage,
    detect_stale_data,
    evaluate_resource_budget,
    handle_agent_or_backtest_failure,
    handle_runtime_dependency_failure,
    plan_api_retry,
)
from stat_arb.memory import MemoryWriteRequest
from stat_arb.storage import Base, CoordinatorTask, Experiment, Hypothesis


class FakeMemoryService:
    """Fake Memory Agent service that records policy-approved write requests."""

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
        engine.dispose()


def test_detect_data_outage_pauses_affected_experiment_without_hidden_threshold() -> None:
    """Data outage checks should use explicit age policy and return a pause action."""
    observed_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    event = detect_data_outage(
        symbol="BTC/USDT",
        source="ccxt",
        latest_observation_at=observed_at - timedelta(minutes=31),
        observed_at=observed_at,
        policy=DataFreshnessPolicy(
            max_outage_age=timedelta(minutes=30),
            max_stale_signal_age=timedelta(minutes=10),
        ),
    )

    assert event is not None
    assert event.event_type == FailureEventType.DATA_OUTAGE
    assert event.severity == FailureSeverity.ERROR
    assert event.action == FailureAction.PAUSE_EXPERIMENT
    assert "BTC/USDT" in event.summary


def test_detect_data_outage_returns_none_for_fresh_data() -> None:
    """Fresh data should not create false failure events."""
    observed_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    event = detect_data_outage(
        symbol="ETH/USDT",
        source="ccxt",
        latest_observation_at=observed_at - timedelta(minutes=5),
        observed_at=observed_at,
        policy=DataFreshnessPolicy(
            max_outage_age=timedelta(minutes=30),
            max_stale_signal_age=timedelta(minutes=10),
        ),
    )

    assert event is None


def test_plan_api_retry_uses_exponential_backoff_and_exhaustion_event() -> None:
    """Retry planning should be explicit and log every attempt-ready decision."""
    retry = plan_api_retry(
        error_summary="temporary 502 from exchange",
        attempt_number=2,
        policy=RetryPolicy(
            max_attempts=3,
            base_delay=timedelta(seconds=2),
            max_delay=timedelta(seconds=30),
            multiplier=2.0,
        ),
    )
    exhausted = plan_api_retry(
        error_summary="temporary 502 from exchange",
        attempt_number=3,
        policy=RetryPolicy(
            max_attempts=3,
            base_delay=timedelta(seconds=2),
            max_delay=timedelta(seconds=30),
            multiplier=2.0,
        ),
    )

    assert retry.should_retry is True
    assert retry.delay == timedelta(seconds=4)
    assert retry.event.action == FailureAction.RETRY
    assert retry.event.metadata["attempt_number"] == 2
    assert exhausted.should_retry is False
    assert exhausted.event.action == FailureAction.ALERT_OPERATOR


def test_detect_stale_data_rejects_signal_not_experiment() -> None:
    """Stale prices should reject only the current signal candidate."""
    observed_at = datetime(2026, 1, 2, 12, 0, tzinfo=UTC)

    event = detect_stale_data(
        symbol="SOL/USDT",
        source="ccxt",
        latest_price_at=observed_at - timedelta(minutes=11),
        observed_at=observed_at,
        policy=DataFreshnessPolicy(
            max_outage_age=timedelta(minutes=30),
            max_stale_signal_age=timedelta(minutes=10),
        ),
    )

    assert event is not None
    assert event.event_type == FailureEventType.STALE_DATA
    assert event.action == FailureAction.REJECT_SIGNAL


def test_classify_abnormal_conditions_pauses_strategy_for_spread_and_funding() -> None:
    """Abnormal spreads and missing funding should pause strategy execution."""
    events = classify_abnormal_conditions(
        AbnormalConditionEvidence(
            strategy_id="pair-btc-eth",
            spread_z_score=5.2,
            funding_rate_available=False,
            observed_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
        ),
        policy=FailureHandlingPolicy(
            abnormal_spread_z_score=4.0,
            require_funding_rate=True,
            safe_mode_components=frozenset({"database", "memory"}),
        ),
    )

    assert [event.event_type for event in events] == [
        FailureEventType.ABNORMAL_SPREAD,
        FailureEventType.MISSING_FUNDING_RATE,
    ]
    assert {event.action for event in events} == {FailureAction.PAUSE_STRATEGY}


def test_handle_backtest_failure_quarantines_experiment_and_writes_memory(
    session: Session,
) -> None:
    """Backtest failures should quarantine the experiment through Coordinator memory policy."""
    experiment_id = _seed_experiment(session, status="backtesting")
    memory = FakeMemoryService()

    result = handle_agent_or_backtest_failure(
        experiment_id=experiment_id,
        failed_stage=ExperimentLifecycleStatus.BACKTESTING,
        error_summary="PnL series contains non-finite value.",
        actor="backtest_agent",
        session=session,
        memory_service=memory,
    )

    stored = session.query(Experiment).one()
    assert result.event.event_type == FailureEventType.EXPERIMENT_FAILURE
    assert stored.status == "final_decision"
    assert stored.final_decision == "quarantined"
    assert "PnL series" in stored.rejection_reason
    assert len(memory.requests) == 1
    assert memory.requests[0].metadata["final_decision"] == "quarantined"


def test_handle_agent_failure_marks_task_failed_and_alerts_operator(session: Session) -> None:
    """Agent failures should leave a durable task failure and operator alert event."""
    experiment_id = _seed_experiment(session, status="statistical_testing")
    task = CoordinatorTask(
        experiment_id=experiment_id,
        task_type="run_statistical_tests",
        agent_name="statistical_testing_agent",
        priority=1,
        status="running",
        attempt_count=1,
        max_attempts=1,
        payload={},
    )
    session.add(task)
    session.commit()
    memory = FakeMemoryService()

    result = handle_agent_or_backtest_failure(
        experiment_id=experiment_id,
        failed_stage=ExperimentLifecycleStatus.STATISTICAL_TESTING,
        error_summary="ADF service returned invalid payload.",
        actor="statistical_testing_agent",
        session=session,
        memory_service=memory,
        coordinator_task_id=task.task_id,
    )

    stored_task = session.query(CoordinatorTask).one()
    assert stored_task.status == "failed"
    assert stored_task.last_error == "ADF service returned invalid payload."
    assert result.event.action == FailureAction.ALERT_OPERATOR


def test_runtime_dependency_failure_enters_safe_mode_and_queues_memory_replay() -> None:
    """Database and memory backend failures should fail closed into safe mode."""
    memory_event = handle_runtime_dependency_failure(
        component="memory",
        error_summary="ApeRAG write failed with transient 503.",
        policy=FailureHandlingPolicy(
            abnormal_spread_z_score=4.0,
            require_funding_rate=True,
            safe_mode_components=frozenset({"database", "memory"}),
        ),
    )

    assert memory_event.action == FailureAction.ENTER_SAFE_MODE
    assert memory_event.event_type == FailureEventType.MEMORY_BACKEND_FAILURE
    assert memory_event.requires_manual_approval is True
    assert memory_event.metadata["recovery"] == "queue_replay_after_operator_approval"


def test_evaluate_resource_budget_warns_without_precommit_side_effects() -> None:
    """Resource budget checks should warn from explicit runtime budget inputs."""
    events = evaluate_resource_budget(
        ResourceUsageSnapshot(
            observed_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
            ram_used_gb=8.1,
            ram_budget_gb=10.0,
            disk_used_gb=39.0,
            disk_budget_gb=50.0,
        ),
        policy=ResourceBudgetPolicy(warn_usage_ratio=0.8),
    )

    assert len(events) == 1
    assert events[0].event_type == FailureEventType.RESOURCE_BUDGET_WARNING
    assert events[0].action == FailureAction.ALERT_OPERATOR
    assert events[0].metadata["resource"] == "ram"


def test_failure_policies_reject_hidden_defaults() -> None:
    """Failure handling configs should require explicit thresholds and limits."""
    with pytest.raises(TypeError):
        RetryPolicy()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        DataFreshnessPolicy()  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        FailureHandlingPolicy()  # type: ignore[call-arg]


def _seed_experiment(session: Session, *, status: str) -> str:
    hypothesis_id = uuid4()
    experiment_id = uuid4()
    session.add(
        Hypothesis(
            hypothesis_id=str(hypothesis_id),
            asset_a="AAA",
            asset_b="BBB",
            rationale="Synthetic failure handling pair",
            source="unit-test",
            created_by="pytest",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
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
