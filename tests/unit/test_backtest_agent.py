"""Unit tests for Backtest Agent registry and memory boundary."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.agents import BacktestAgentInput, run_backtest_agent_persistence
from stat_arb.backtest import (
    BacktestCostConfig,
    BaselineAsset,
    BaselineSide,
    BuyAndHoldBaselineConfig,
    CostAssumptionStatus,
    CostSensitivityAnalysisResult,
    CostSensitivityScenario,
    PerformanceMetricConfig,
    calculate_performance_metrics,
    compare_to_buy_and_hold_baseline,
    create_reproducibility_manifest,
    run_cost_sensitivity_analysis,
    run_pair_backtest_core,
)
from stat_arb.memory import MemoryWriteRequest
from stat_arb.storage import BacktestResult, Base, DataQualityReportRecord, Dataset, Hypothesis
from stat_arb.storage.models import StatisticalTestResult as StoredStatisticalTestResult


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


def test_backtest_agent_persists_registry_result_and_memory_summary(
    session: Session,
    tmp_path: Path,
) -> None:
    """Backtest Agent should write structured registry data and concise memory summary."""
    hypothesis_id, test_id, dataset_a_id, dataset_b_id = _seed_prerequisites(
        session,
        with_quality=True,
        passed_test=True,
    )
    memory = FakeMemoryService()

    result = run_backtest_agent_persistence(
        _agent_input(tmp_path, hypothesis_id, test_id, dataset_a_id, dataset_b_id),
        session=session,
        memory_service=memory,
    )

    stored = session.query(BacktestResult).one()
    assert result.stored_result.backtest_id == stored.backtest_id
    assert stored.hypothesis_id == str(hypothesis_id)
    assert stored.test_id == str(test_id)
    assert stored.git_commit_hash == "abcdef1"
    assert len(stored.config_hash) == 64
    assert stored.gross_pnl == pytest.approx(result.stored_result.gross_pnl)
    assert stored.net_pnl + stored.commission_cost + stored.spread_cost + stored.slippage_cost + stored.funding_cost + stored.borrow_cost == pytest.approx(stored.gross_pnl)
    assert stored.net_pnl_2x_costs < stored.net_pnl_half_costs
    assert result.memory_written is True
    assert len(memory.requests) == 1
    assert memory.requests[0].registry_reference == f"registry:backtest_results/{stored.backtest_id}"
    assert "Structured performance metrics" in memory.requests[0].body
    assert "net_pnl" not in memory.requests[0].body


def test_backtest_agent_requires_passed_data_quality(session: Session, tmp_path: Path) -> None:
    """Backtest persistence should not bypass data-quality prerequisites."""
    hypothesis_id, test_id, dataset_a_id, dataset_b_id = _seed_prerequisites(
        session,
        with_quality=False,
        passed_test=True,
    )

    with pytest.raises(ValueError, match="passed data quality report"):
        run_backtest_agent_persistence(
            _agent_input(tmp_path, hypothesis_id, test_id, dataset_a_id, dataset_b_id),
            session=session,
        )

    assert session.query(BacktestResult).count() == 0


def test_backtest_agent_requires_passed_statistical_test(session: Session, tmp_path: Path) -> None:
    """Backtest persistence should not bypass the statistical validation boundary."""
    hypothesis_id, test_id, dataset_a_id, dataset_b_id = _seed_prerequisites(
        session,
        with_quality=True,
        passed_test=False,
    )

    with pytest.raises(ValueError, match="passed statistical test"):
        run_backtest_agent_persistence(
            _agent_input(tmp_path, hypothesis_id, test_id, dataset_a_id, dataset_b_id),
            session=session,
        )

    assert session.query(BacktestResult).count() == 0


def test_backtest_agent_rejects_missing_required_sensitivity_scenarios(
    session: Session,
    tmp_path: Path,
) -> None:
    """Registry persistence requires the explicit MVP cost sensitivity scenarios."""
    hypothesis_id, test_id, dataset_a_id, dataset_b_id = _seed_prerequisites(
        session,
        with_quality=True,
        passed_test=True,
    )
    request = _agent_input(tmp_path, hypothesis_id, test_id, dataset_a_id, dataset_b_id)
    incomplete_request = BacktestAgentInput(
        hypothesis_id=request.hypothesis_id,
        test_id=request.test_id,
        dataset_a_id=request.dataset_a_id,
        dataset_b_id=request.dataset_b_id,
        core_result=request.core_result,
        pnl=request.pnl,
        metrics=request.metrics,
        baseline=request.baseline,
        sensitivity=CostSensitivityAnalysisResult(base=request.pnl, scenarios=()),
        reproducibility=request.reproducibility,
        train_window_days=request.train_window_days,
        test_window_days=request.test_window_days,
        num_windows=request.num_windows,
    )

    with pytest.raises(ValueError, match="double_costs and half_costs"):
        run_backtest_agent_persistence(incomplete_request, session=session)

    assert session.query(BacktestResult).count() == 0


def test_backtest_agent_boundary_guard_is_in_pre_commit_and_ci() -> None:
    """Guard should prevent direct ApeRAG writes and registry bypass regressions."""
    script = Path("scripts/check_backtest_agent_boundaries.ps1").read_text(encoding="utf-8")
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "ApeRAGMemoryClient" in script
    assert "StoredBacktestResult" in script
    assert "DataQualityReportRecord" in script
    assert "check_backtest_agent_boundaries.ps1" in pre_commit
    assert "& $backtestAgentBoundaryCheckScript" in pre_commit
    assert "Check Backtest Agent boundaries" in ci
    assert "./scripts/check_backtest_agent_boundaries.ps1" in ci


def _agent_input(
    tmp_path: Path,
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
    metrics = calculate_performance_metrics(
        equity_curve=[100.0, 102.0, 100.98, 102.49, 103.0],
        period_returns=returns,
        trade_pnls=[5.0, -2.0],
        core_result=core,
        config=_metric_config(),
    )
    baseline = compare_to_buy_and_hold_baseline(
        strategy_period_returns=returns,
        prices_a=prices_a,
        prices_b=prices_b,
        aligned_timestamps=timestamps,
        baseline_config=BuyAndHoldBaselineConfig(
            name="long_asset_a_one_unit",
            asset=BaselineAsset.ASSET_A,
            side=BaselineSide.LONG,
            units=1.0,
            initial_capital=100.0,
        ),
        metric_config=_metric_config(),
    )
    lock_file = tmp_path / "uv.lock"
    lock_file.write_text("package==1.0\n", encoding="utf-8")
    reproducibility = create_reproducibility_manifest(
        git_commit_hash="abcdef1",
        config_components={
            "cost_config": cost_config,
            "metric_config": _metric_config(),
            "baseline_config": BuyAndHoldBaselineConfig(
                name="long_asset_a_one_unit",
                asset=BaselineAsset.ASSET_A,
                side=BaselineSide.LONG,
                units=1.0,
                initial_capital=100.0,
            ),
            "sensitivity_scenarios": (
                CostSensitivityScenario(name="double_costs", cost_multiplier=2.0),
                CostSensitivityScenario(name="half_costs", cost_multiplier=0.5),
            ),
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
        train_window_days=60,
        test_window_days=30,
        num_windows=2,
    )


def _seed_prerequisites(
    session: Session,
    *,
    with_quality: bool,
    passed_test: bool,
) -> tuple[UUID, UUID, UUID, UUID]:
    hypothesis_id = uuid4()
    test_id = uuid4()
    dataset_a_id = uuid4()
    dataset_b_id = uuid4()
    start = datetime(2024, 1, 1, tzinfo=UTC)
    end = datetime(2024, 1, 3, tzinfo=UTC)
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
            StoredStatisticalTestResult(
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
                passed=passed_test,
                rejection_reason=None if passed_test else "failed unit-test prerequisite",
            ),
        ]
    )
    if with_quality:
        session.add_all(
            [
                _quality_report(dataset_a_id, "AAA", start, end),
                _quality_report(dataset_b_id, "BBB", start, end),
            ]
        )
    session.commit()
    return hypothesis_id, test_id, dataset_a_id, dataset_b_id


def _quality_report(dataset_id: UUID, symbol: str, start: datetime, end: datetime) -> DataQualityReportRecord:
    return DataQualityReportRecord(
        report_id=str(uuid4()),
        dataset_id=str(dataset_id),
        symbol=symbol,
        source="unit-test",
        timeframe="15m",
        start_date=start,
        end_date=end,
        bar_count=240,
        expected_bar_count=240,
        timezone_normalized=True,
        alignment_score=1.0,
        quality_score=1.0,
        passed=True,
        issues=[],
        report_path=f"/tmp/{symbol}-quality.json",
        generated_at=start,
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
        source="unit-test",
        verified_at=datetime(2024, 1, 1, tzinfo=UTC),
        venue="test-exchange",
        market_type="perpetual",
    )
