"""Unit tests for Report Agent registry and memory boundary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents import ReportAgentInput, run_report_agent
from stat_arb.memory import MemoryWriteRequest
from stat_arb.storage import Base, Hypothesis, ReportArtifact
from stat_arb.storage.models import (
    BacktestResult,
    CriticReview,
    Dataset,
    Experiment,
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


def test_report_agent_generates_artifacts_registry_rows_and_memory_summary(
    session: Session,
    tmp_path: Path,
) -> None:
    """Report Agent should persist artifacts and write only a concise memory summary."""
    experiment_id, backtest_id = _seed_report_prerequisites(session)
    memory = FakeMemoryService()

    result = run_report_agent(
        ReportAgentInput(
            experiment_id=experiment_id,
            backtest_id=backtest_id,
            output_dir=tmp_path,
        ),
        session=session,
        memory_service=memory,
    )

    stored = session.query(ReportArtifact).order_by(ReportArtifact.artifact_type).all()
    assert len(stored) == 2
    assert {row.artifact_type for row in stored} == {"backtest_report", "json_summary"}
    assert all(Path(row.file_path).exists() for row in stored)
    assert len(result.artifacts) == 2
    assert result.memory_written is True
    assert len(memory.requests) == 1
    assert memory.requests[0].record_type == "report_summary"
    assert memory.requests[0].registry_reference.startswith("registry:report_artifacts/")
    assert "Report artifacts were generated" in memory.requests[0].body
    assert "net_pnl" not in memory.requests[0].body


def test_report_agent_requires_matching_experiment_and_backtest(session: Session, tmp_path: Path) -> None:
    """Report artifacts must not connect an experiment to an unrelated backtest."""
    _experiment_id, backtest_id = _seed_report_prerequisites(session)
    other_hypothesis_id = uuid4()
    session.add(
        Hypothesis(
            hypothesis_id=str(other_hypothesis_id),
            asset_a="CCC",
            asset_b="DDD",
            rationale="Different report chain",
            source="unit-test",
            created_by="pytest",
        )
    )
    session.flush()
    other_experiment = Experiment(
        experiment_id=str(uuid4()),
        hypothesis_id=str(other_hypothesis_id),
        status="reporting",
    )
    session.add(other_experiment)
    session.commit()

    with pytest.raises(ValueError, match="experiment/backtest hypothesis mismatch"):
        run_report_agent(
            ReportAgentInput(
                experiment_id=UUID(other_experiment.experiment_id),
                backtest_id=backtest_id,
                output_dir=tmp_path,
            ),
            session=session,
        )

    assert session.query(ReportArtifact).count() == 0


def _seed_report_prerequisites(session: Session) -> tuple[UUID, UUID]:
    hypothesis_id = uuid4()
    test_id = uuid4()
    dataset_a_id = uuid4()
    dataset_b_id = uuid4()
    backtest_id = uuid4()
    experiment_id = uuid4()
    review_id = uuid4()
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = start + timedelta(days=2)

    session.add(
        Hypothesis(
            hypothesis_id=str(hypothesis_id),
            asset_a="AAA",
            asset_b="BBB",
            rationale="Synthetic report pair",
            source="unit-test",
            created_by="pytest",
        )
    )
    session.add_all(
        [
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
        ]
    )
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
        )
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
            dataset_ids=[str(dataset_a_id), str(dataset_b_id)],
            random_seed=12345,
            execution_command=["uv", "run", "stat-arb", "backtest"],
            run_timestamp=start,
            lock_file_hash="f" * 64,
            execution_time_seconds=12.5,
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
        )
    )
    session.add(
        CriticReview(
            review_id=str(review_id),
            backtest_id=str(backtest_id),
            lookahead_bias_detected=False,
            overfitting_indicators=[],
            weak_assumptions=["residual_autocorrelation: weak"],
            insufficient_testing=[],
            cost_concerns=[],
            operational_concerns=[],
            status="quarantined",
            recommendation="Quarantine",
            objections="residual_autocorrelation: weak",
        )
    )
    session.add(
        Experiment(
            experiment_id=str(experiment_id),
            hypothesis_id=str(hypothesis_id),
            status="reporting",
            data_quality_passed=True,
            statistical_tests_passed=True,
            backtest_completed=True,
            critic_approved=False,
        )
    )
    session.commit()
    return experiment_id, backtest_id
