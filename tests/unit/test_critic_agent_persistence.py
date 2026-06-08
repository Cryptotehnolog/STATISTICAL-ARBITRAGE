"""Unit tests for Critic Agent registry and memory boundary."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents import (
    CriticAgentInput,
    CriticCostRealismAssessment,
    CriticDecisionAssessment,
    CriticDecisionStatus,
    CriticInsufficientTestingAssessment,
    CriticLookaheadAssessment,
    CriticOverfittingAssessment,
    CriticWeakAssumptionAssessment,
    run_critic_agent_persistence,
)
from stat_arb.memory import MemoryWriteRequest
from stat_arb.storage import (
    BacktestResult,
    Base,
    CriticReview,
    Dataset,
    Hypothesis,
    StatisticalTestResult,
)


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


def test_critic_agent_persists_registry_review_and_memory_summary(session: Session) -> None:
    """Critic Agent should write structured registry data and concise memory summary."""
    backtest_id = _seed_backtest(session)
    memory = FakeMemoryService()

    result = run_critic_agent_persistence(
        _critic_input(backtest_id),
        session=session,
        memory_service=memory,
    )

    stored = session.query(CriticReview).one()
    assert result.stored_review.review_id == stored.review_id
    assert stored.backtest_id == str(backtest_id)
    assert stored.status == "rejected"
    assert stored.lookahead_bias_detected is True
    assert stored.overfitting_indicators == ["sharpe_degradation: unstable"]
    assert stored.weak_assumptions == ["cointegration_p_value_proximity: near alpha"]
    assert stored.insufficient_testing == ["minimum_walk_forward_windows: too few"]
    assert stored.cost_concerns == ["negative_net_pnl_after_costs: loss"]
    assert stored.operational_concerns == ["manual review required"]
    assert "signal_lookahead" in stored.objections
    assert result.memory_written is True
    assert len(memory.requests) == 1
    assert memory.requests[0].registry_reference == f"registry:critic_reviews/{stored.review_id}"
    assert memory.requests[0].source_id == stored.review_id
    assert "Critic review completed" in memory.requests[0].body
    assert "sharpe_degradation" not in memory.requests[0].body


def test_critic_agent_requires_existing_backtest(session: Session) -> None:
    """Critic review persistence should not create orphan registry rows."""
    with pytest.raises(ValueError, match="backtest result is required"):
        run_critic_agent_persistence(_critic_input(uuid4()), session=session)

    assert session.query(CriticReview).count() == 0


def test_critic_agent_boundary_guard_is_in_pre_commit_and_ci() -> None:
    """Guard should prevent direct ApeRAG writes and registry bypass regressions."""
    script = Path("scripts/check_critic_agent_boundaries.ps1").read_text(encoding="utf-8")
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "ApeRAGMemoryClient" in script
    assert "StoredCriticReview" in script
    assert "memory_service\\.write" in script
    assert "check_critic_agent_boundaries.ps1" in pre_commit
    assert "& $criticAgentBoundaryCheckScript" in pre_commit
    assert "Check Critic Agent boundaries" in ci
    assert "./scripts/check_critic_agent_boundaries.ps1" in ci


def _critic_input(backtest_id: UUID) -> CriticAgentInput:
    return CriticAgentInput(
        backtest_id=backtest_id,
        lookahead=CriticLookaheadAssessment(
            lookahead_bias_detected=True,
            issues=("signal_lookahead: future bar used",),
            checked_rules=("strictly_past_signals",),
        ),
        overfitting=CriticOverfittingAssessment(
            overfitting_detected=True,
            indicators=("sharpe_degradation: unstable",),
            checked_rules=("sharpe_degradation",),
        ),
        weak_assumptions=CriticWeakAssumptionAssessment(
            weak_assumptions_detected=True,
            indicators=("cointegration_p_value_proximity: near alpha",),
            checked_rules=("cointegration_p_value_proximity",),
        ),
        insufficient_testing=CriticInsufficientTestingAssessment(
            insufficient_testing_detected=True,
            indicators=("minimum_walk_forward_windows: too few",),
            checked_rules=("minimum_walk_forward_windows",),
        ),
        cost_realism=CriticCostRealismAssessment(
            cost_realism_concerns_detected=True,
            indicators=("negative_net_pnl_after_costs: loss",),
            checked_rules=("negative_net_pnl_after_costs",),
        ),
        decision=CriticDecisionAssessment(
            status=CriticDecisionStatus.REJECTED,
            recommendation="Reject",
            objections=("signal_lookahead: future bar used",),
        ),
        operational_concerns=("manual review required",),
    )


def _seed_backtest(session: Session) -> UUID:
    hypothesis_id = uuid4()
    test_id = uuid4()
    dataset_a_id = uuid4()
    dataset_b_id = uuid4()
    backtest_id = uuid4()
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=2)

    session.add_all(
        [
            Hypothesis(
                hypothesis_id=str(hypothesis_id),
                asset_a="AAA",
                asset_b="BBB",
                rationale="Synthetic pair",
                source="unit-test",
                created_by="pytest",
            ),
            Dataset(
                dataset_id=str(dataset_a_id),
                symbol="AAA",
                source="unit-test",
                timeframe="15m",
                start_date=start,
                end_date=end,
                bar_count=240,
                adjustment_mode="none",
                file_path="/tmp/a.parquet",
            ),
            Dataset(
                dataset_id=str(dataset_b_id),
                symbol="BBB",
                source="unit-test",
                timeframe="15m",
                start_date=start,
                end_date=end,
                bar_count=240,
                adjustment_mode="none",
                file_path="/tmp/b.parquet",
            ),
        ],
    )
    session.flush()
    session.add(
        StatisticalTestResult(
            test_id=str(test_id),
            hypothesis_id=str(hypothesis_id),
            dataset_a_id=str(dataset_a_id),
            dataset_b_id=str(dataset_b_id),
            train_start=start,
            train_end=start + timedelta(days=1),
            test_start=start + timedelta(days=1),
            test_end=end,
            cointegration_statistic=-3.0,
            cointegration_p_value=0.01,
            adf_statistic=-4.0,
            adf_p_value=0.01,
            hedge_ratio=1.0,
            hedge_ratio_r_squared=0.9,
            half_life_days=2.0,
            regime_changes_detected=False,
            passed=True,
            rejection_reason=None,
        ),
    )
    session.flush()
    session.add(
        BacktestResult(
            backtest_id=str(backtest_id),
            hypothesis_id=str(hypothesis_id),
            test_id=str(test_id),
            dataset_a_id=str(dataset_a_id),
            dataset_b_id=str(dataset_b_id),
            git_commit_hash="abcdef1",
            config_hash="a" * 64,
            train_window_days=60,
            test_window_days=30,
            num_windows=2,
            entry_threshold=2.0,
            exit_threshold=0.5,
            hedge_ratio=1.0,
            gross_pnl=100.0,
            net_pnl=80.0,
            commission_cost=5.0,
            spread_cost=3.0,
            slippage_cost=2.0,
            funding_cost=1.0,
            borrow_cost=1.0,
            num_trades=4,
            turnover=1.2,
            avg_holding_time_hours=12.0,
            median_holding_time_hours=10.0,
            sharpe_ratio=1.1,
            sortino_ratio=1.3,
            volatility=0.2,
            max_drawdown=0.1,
            win_rate=0.6,
            profit_factor=1.5,
            net_pnl_2x_costs=60.0,
            net_pnl_half_costs=90.0,
            baseline_sharpe=0.5,
            tested_at=start,
        ),
    )
    session.commit()
    return backtest_id
