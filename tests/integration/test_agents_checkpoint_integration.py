"""Integration smoke for Task 14: all implemented agent boundaries together."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents import (
    BacktestAgentInput,
    CoordinatorFinalDecisionEvidence,
    CoordinatorFinalDecisionPolicy,
    CriticAgentInput,
    CriticCostRealismAssessment,
    CriticDecisionAssessment,
    CriticDecisionStatus,
    CriticInsufficientTestingAssessment,
    CriticLookaheadAssessment,
    CriticOverfittingAssessment,
    CriticWeakAssumptionAssessment,
    ExperimentFinalDecision,
    HypothesisGenerationConfig,
    HypothesisUniverseAsset,
    ReportAgentInput,
    StatisticalTestingInput,
    apply_coordinator_final_decision,
    generate_rule_based_hypotheses,
    run_backtest_agent_persistence,
    run_critic_agent_persistence,
    run_report_agent,
    run_statistical_testing,
)
from stat_arb.backtest import (
    BacktestCostConfig,
    BaselineAsset,
    BaselineSide,
    BuyAndHoldBaselineConfig,
    CostAssumptionStatus,
    CostSensitivityScenario,
    PerformanceMetricConfig,
    calculate_performance_metrics,
    compare_to_buy_and_hold_baseline,
    create_reproducibility_manifest,
    run_cost_sensitivity_analysis,
    run_pair_backtest_core,
)
from stat_arb.memory import MemoryWriteRequest
from stat_arb.statistical import MultipleTestingMethod
from stat_arb.storage import Base, DataQualityReportRecord, Dataset, Experiment, ReportArtifact


class FakeMemoryService:
    """Fake Memory Agent service that records all agent summaries."""

    def __init__(self) -> None:
        self.requests: list[MemoryWriteRequest] = []

    def write(self, request: MemoryWriteRequest) -> object:
        self.requests.append(request)
        return object()


def test_task_14_agents_share_registry_and_memory_boundaries(
    tmp_path: Path,
) -> None:
    """Implemented agents should compose through registry rows and policy-safe memory."""
    session = _create_session()
    memory = FakeMemoryService()
    try:
        hypothesis = generate_rule_based_hypotheses(
            assets=(
                HypothesisUniverseAsset(symbol="AAA", sector="tech", market_cap=10_000),
                HypothesisUniverseAsset(symbol="BBB", sector="tech", market_cap=9_000),
            ),
            correlations={("AAA", "BBB"): 0.96},
            candidate_p_values={("AAA", "BBB"): 0.01},
            config=HypothesisGenerationConfig(
                require_same_sector=True,
                min_abs_correlation=0.9,
                min_market_cap=1_000,
                max_market_cap=None,
                max_pairs=1,
                multiple_testing_method=MultipleTestingMethod.NONE,
                candidate_alpha=0.05,
                initial_novelty_score=1.0,
                initial_status="testing",
                source="task-14-checkpoint",
                created_by="hypothesis_agent",
            ),
            session=session,
            memory_service=memory,
        ).hypotheses[0]
        dataset_a_id, dataset_b_id, prices_a, prices_b, timestamps = _seed_dataset_quality(
            session,
        )
        experiment_id = _seed_experiment(session, UUID(hypothesis.hypothesis_id))

        statistical = run_statistical_testing(
            StatisticalTestingInput(
                hypothesis_id=UUID(hypothesis.hypothesis_id),
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
                prices_a=prices_a,
                prices_b=prices_b,
                aligned_timestamps=timestamps,
                train_fraction=0.7,
                alpha=0.05,
                adf_regression="c",
                adf_autolag="AIC",
                periods_per_day=96.0,
                regime_window=60,
                regime_mean_shift_threshold=3.0,
                regime_volatility_ratio_threshold=2.5,
            ),
            session=session,
            memory_service=memory,
        )
        backtest = run_backtest_agent_persistence(
            _backtest_input(
                tmp_path,
                hypothesis_id=UUID(hypothesis.hypothesis_id),
                test_id=UUID(statistical.stored_result.test_id),
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
            ),
            session=session,
            memory_service=memory,
        )
        critic = run_critic_agent_persistence(
            _critic_input(UUID(backtest.stored_result.backtest_id)),
            session=session,
            memory_service=memory,
        )
        report = run_report_agent(
            ReportAgentInput(
                experiment_id=experiment_id,
                backtest_id=UUID(backtest.stored_result.backtest_id),
                output_dir=tmp_path / "reports",
            ),
            session=session,
            memory_service=memory,
        )
        coordinator = apply_coordinator_final_decision(
            experiment_id=str(experiment_id),
            evidence=CoordinatorFinalDecisionEvidence(
                critic_status=critic.stored_review.status,
                critic_objections=(),
                hypothesis_status=hypothesis.status,
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

        stored_experiment = session.get(Experiment, str(experiment_id))
        assert stored_experiment is not None
        assert statistical.stored_result.hypothesis_id == hypothesis.hypothesis_id
        assert backtest.stored_result.test_id == statistical.stored_result.test_id
        assert critic.stored_review.backtest_id == backtest.stored_result.backtest_id
        assert len(report.artifacts) == 4
        assert session.query(ReportArtifact).count() == 4
        assert coordinator.current_status == "final_decision"
        assert stored_experiment.final_decision == "approved"
        assert len(memory.requests) == 6
        assert all(request.registry_reference for request in memory.requests)
        assert not any("api_key" in request.body.lower() for request in memory.requests)
    finally:
        session.close()


def _create_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _seed_dataset_quality(
    session: Session,
) -> tuple[UUID, UUID, np.ndarray, np.ndarray, tuple[datetime, ...]]:
    dataset_a_id = uuid4()
    dataset_b_id = uuid4()
    prices_a, prices_b, timestamps = _cointegrated_pair()
    start = timestamps[0]
    end = timestamps[-1]
    session.add_all(
        [
            Dataset(
                dataset_id=str(dataset_a_id),
                symbol="AAA",
                source="task-14-checkpoint",
                timeframe="15m",
                start_date=start,
                end_date=end,
                bar_count=len(timestamps),
                adjustment_mode="none",
                file_path="/tmp/task14-aaa.parquet",
            ),
            Dataset(
                dataset_id=str(dataset_b_id),
                symbol="BBB",
                source="task-14-checkpoint",
                timeframe="15m",
                start_date=start,
                end_date=end,
                bar_count=len(timestamps),
                adjustment_mode="none",
                file_path="/tmp/task14-bbb.parquet",
            ),
            _quality_report(dataset_a_id, "AAA", start, end, len(timestamps)),
            _quality_report(dataset_b_id, "BBB", start, end, len(timestamps)),
        ]
    )
    session.commit()
    return dataset_a_id, dataset_b_id, prices_a, prices_b, timestamps


def _seed_experiment(session: Session, hypothesis_id: UUID) -> UUID:
    experiment_id = uuid4()
    session.add(
        Experiment(
            experiment_id=str(experiment_id),
            hypothesis_id=str(hypothesis_id),
            status="reporting",
            current_agent="report_agent",
            data_quality_passed=True,
            statistical_tests_passed=True,
            backtest_completed=True,
            critic_approved=True,
        )
    )
    session.commit()
    return experiment_id


def _quality_report(
    dataset_id: UUID,
    symbol: str,
    start: datetime,
    end: datetime,
    bar_count: int,
) -> DataQualityReportRecord:
    return DataQualityReportRecord(
        report_id=str(uuid4()),
        dataset_id=str(dataset_id),
        symbol=symbol,
        source="task-14-checkpoint",
        timeframe="15m",
        start_date=start,
        end_date=end,
        bar_count=bar_count,
        expected_bar_count=bar_count,
        missing_bars=0,
        duplicate_timestamps=0,
        outlier_count=0,
        zero_price_count=0,
        impossible_candle_count=0,
        abnormal_volume_count=0,
        timezone_normalized=True,
        alignment_score=1.0,
        quality_score=1.0,
        passed=True,
        issues=[],
        report_path=f"/tmp/task14-{symbol.lower()}-quality.json",
        generated_at=start,
    )


def _cointegrated_pair() -> tuple[np.ndarray, np.ndarray, tuple[datetime, ...]]:
    rng = np.random.default_rng(42)
    observations = 240
    asset_b = np.cumsum(rng.normal(size=observations)) + 100.0
    residuals = np.zeros(observations)
    shocks = rng.normal(scale=0.2, size=observations)
    for index in range(1, observations):
        residuals[index] = 0.65 * residuals[index - 1] + shocks[index]
    asset_a = 1.4 * asset_b + residuals
    start = datetime(2024, 1, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=15 * index) for index in range(observations))
    return asset_a, asset_b, timestamps


def _backtest_input(
    tmp_path: Path,
    *,
    hypothesis_id: UUID,
    test_id: UUID,
    dataset_a_id: UUID,
    dataset_b_id: UUID,
) -> BacktestAgentInput:
    timestamps = tuple(
        datetime(2024, 1, 1, tzinfo=UTC) + timedelta(minutes=15 * index)
        for index in range(5)
    )
    prices_a = np.asarray([100.0, 103.0, 101.0, 100.0, 99.0])
    prices_b = np.asarray([100.0, 100.0, 100.0, 100.0, 100.0])
    core = run_pair_backtest_core(
        prices_a=prices_a,
        prices_b=prices_b,
        z_scores=[2.2, 1.2, 0.2, -2.1, 0.0],
        aligned_timestamps=timestamps,
        hedge_ratio=1.0,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )
    cost_config = _verified_cost_config()
    sensitivity = run_cost_sensitivity_analysis(
        core,
        base_cost_config=cost_config,
        periods_per_day=96.0,
        average_portfolio_value=10_000.0,
        scenarios=(
            CostSensitivityScenario(name="double_costs", cost_multiplier=2.0),
            CostSensitivityScenario(name="half_costs", cost_multiplier=0.5),
        ),
    )
    returns = np.asarray([0.02, -0.01, 0.015, 0.005])
    metric_config = _metric_config()
    baseline_config = BuyAndHoldBaselineConfig(
        name="long_asset_a_one_unit",
        asset=BaselineAsset.ASSET_A,
        side=BaselineSide.LONG,
        units=1.0,
        initial_capital=100.0,
    )
    metrics = calculate_performance_metrics(
        equity_curve=[100.0, 102.0, 100.98, 102.49, 103.0],
        period_returns=returns,
        trade_pnls=[5.0, -2.0],
        core_result=core,
        config=metric_config,
    )
    baseline = compare_to_buy_and_hold_baseline(
        strategy_period_returns=returns,
        prices_a=prices_a,
        prices_b=prices_b,
        aligned_timestamps=timestamps,
        baseline_config=baseline_config,
        metric_config=metric_config,
    )
    lock_file = tmp_path / "uv.lock"
    lock_file.write_text("package==1.0\n", encoding="utf-8")
    reproducibility = create_reproducibility_manifest(
        git_commit_hash="abcdef1",
        config_components={
            "cost_config": cost_config,
            "metric_config": metric_config,
            "baseline_config": baseline_config,
            "sensitivity_scenarios": sensitivity.scenarios,
        },
        dataset_ids=(str(dataset_a_id), str(dataset_b_id)),
        random_seed=None,
        execution_command=("stat-arb", "backtest"),
        run_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        lock_file_path=lock_file,
    )
    return BacktestAgentInput(
        hypothesis_id=hypothesis_id,
        test_id=test_id,
        dataset_a_id=dataset_a_id,
        dataset_b_id=dataset_b_id,
        core_result=core,
        pnl=sensitivity.base,
        metrics=metrics,
        baseline=baseline,
        sensitivity=sensitivity,
        reproducibility=reproducibility,
        train_window_days=21,
        test_window_days=7,
        num_windows=2,
    )


def _critic_input(backtest_id: UUID) -> CriticAgentInput:
    return CriticAgentInput(
        backtest_id=backtest_id,
        lookahead=CriticLookaheadAssessment(
            lookahead_bias_detected=False,
            issues=(),
            checked_rules=("strictly_past_signals",),
        ),
        overfitting=CriticOverfittingAssessment(
            overfitting_detected=False,
            indicators=(),
            checked_rules=("sharpe_degradation",),
        ),
        weak_assumptions=CriticWeakAssumptionAssessment(
            weak_assumptions_detected=False,
            indicators=(),
            checked_rules=("cointegration_p_value_proximity",),
        ),
        insufficient_testing=CriticInsufficientTestingAssessment(
            insufficient_testing_detected=False,
            indicators=(),
            checked_rules=("minimum_walk_forward_windows",),
        ),
        cost_realism=CriticCostRealismAssessment(
            cost_realism_concerns_detected=False,
            indicators=(),
            checked_rules=("negative_net_pnl_after_costs",),
        ),
        decision=CriticDecisionAssessment(
            status=CriticDecisionStatus.APPROVED,
            recommendation="Approve",
            objections=(),
        ),
    )


def _metric_config() -> PerformanceMetricConfig:
    return PerformanceMetricConfig(
        periods_per_year=365,
        risk_free_rate_per_period=0.0,
        var_confidence=0.95,
        cvar_confidence=0.95,
    )


def _verified_cost_config() -> BacktestCostConfig:
    return BacktestCostConfig(
        commission_rate=0.001,
        spread_cost_rate=0.0005,
        slippage_rate=0.0002,
        funding_rate_daily=0.0001,
        borrow_rate_annual=0.005,
        status=CostAssumptionStatus.VERIFIED,
        source="task-14-checkpoint",
        verified_at=datetime(2024, 1, 1, tzinfo=UTC),
        venue="test-exchange",
        market_type="perpetual",
    )
