"""
Unit tests for storage models.

Tests the SQLAlchemy ORM models for the Structured Registry.

Requirements: 9.1-9.11, 27.14
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from stat_arb.storage.models import (
    BacktestResult,
    Base,
    CriticReview,
    Dataset,
    Experiment,
    Hypothesis,
    ReportArtifact,
    StatisticalTestResult,
)


@pytest.fixture
def engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    
    # Manually enable foreign keys for this connection
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
    
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a database session for testing."""
    SessionFactory = sessionmaker(bind=engine)
    session = SessionFactory()
    yield session
    session.close()


def test_hypothesis_creation(session: Session):
    """Test creating a hypothesis record."""
    hypothesis = Hypothesis(
        hypothesis_id=str(uuid4()),
        asset_a="AAPL",
        asset_b="MSFT",
        rationale="Both are large-cap tech companies",
        source="rule_based",
        novelty_score=0.85,
        status="new",
        created_by="hypothesis_agent",
    )

    session.add(hypothesis)
    session.commit()

    # Query back
    result = session.query(Hypothesis).filter_by(asset_a="AAPL").first()
    assert result is not None
    assert result.asset_b == "MSFT"
    assert result.rationale == "Both are large-cap tech companies"
    assert result.novelty_score == 0.85


def test_dataset_creation(session: Session):
    """Test creating a dataset record."""
    dataset = Dataset(
        dataset_id=str(uuid4()),
        symbol="AAPL",
        source="ccxt",
        timeframe="15m",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        bar_count=10000,
        missing_bars=50,
        outlier_count=10,
        quality_score=0.95,
        adjustment_mode="split",
        file_path="/data/aapl_15m.parquet",
    )

    session.add(dataset)
    session.commit()

    # Query back
    result = session.query(Dataset).filter_by(symbol="AAPL").first()
    assert result is not None
    assert result.timeframe == "15m"
    assert result.bar_count == 10000
    assert result.quality_score == 0.95


def test_statistical_test_result_creation(session: Session):
    """Test creating a statistical test result record."""
    # Create hypothesis and datasets first
    hypothesis = Hypothesis(
        hypothesis_id=str(uuid4()),
        asset_a="AAPL",
        asset_b="MSFT",
        rationale="Test",
        source="test",
        created_by="test",
    )
    dataset_a = Dataset(
        dataset_id=str(uuid4()),
        symbol="AAPL",
        source="test",
        timeframe="15m",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        bar_count=1000,
        adjustment_mode="none",
        file_path="/test/a.parquet",
    )
    dataset_b = Dataset(
        dataset_id=str(uuid4()),
        symbol="MSFT",
        source="test",
        timeframe="15m",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        bar_count=1000,
        adjustment_mode="none",
        file_path="/test/b.parquet",
    )

    session.add_all([hypothesis, dataset_a, dataset_b])
    session.commit()

    # Create test result
    test_result = StatisticalTestResult(
        test_id=str(uuid4()),
        hypothesis_id=hypothesis.hypothesis_id,
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        train_start=datetime(2024, 1, 1),
        train_end=datetime(2024, 4, 30),
        test_start=datetime(2024, 5, 1),
        test_end=datetime(2024, 6, 30),
        cointegration_statistic=-3.45,
        cointegration_p_value=0.012,
        adf_statistic=-4.12,
        adf_p_value=0.008,
        hedge_ratio=1.5,
        hedge_ratio_r_squared=0.85,
        half_life_days=5.2,
        regime_changes_detected=False,
        passed=True,
    )

    session.add(test_result)
    session.commit()

    # Query back
    result = session.query(StatisticalTestResult).filter_by(passed=True).first()
    assert result is not None
    assert result.cointegration_p_value == 0.012
    assert result.hedge_ratio == 1.5
    assert result.passed is True


def test_backtest_result_creation(session: Session):
    """Test creating a backtest result record."""
    # Create prerequisite records
    hypothesis = Hypothesis(
        hypothesis_id=str(uuid4()),
        asset_a="AAPL",
        asset_b="MSFT",
        rationale="Test",
        source="test",
        created_by="test",
    )
    dataset_a = Dataset(
        dataset_id=str(uuid4()),
        symbol="AAPL",
        source="test",
        timeframe="15m",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        bar_count=1000,
        adjustment_mode="none",
        file_path="/test/a.parquet",
    )
    dataset_b = Dataset(
        dataset_id=str(uuid4()),
        symbol="MSFT",
        source="test",
        timeframe="15m",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        bar_count=1000,
        adjustment_mode="none",
        file_path="/test/b.parquet",
    )
    test_result = StatisticalTestResult(
        test_id=str(uuid4()),
        hypothesis_id=hypothesis.hypothesis_id,
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        train_start=datetime(2024, 1, 1),
        train_end=datetime(2024, 4, 30),
        test_start=datetime(2024, 5, 1),
        test_end=datetime(2024, 6, 30),
        cointegration_statistic=-3.45,
        cointegration_p_value=0.012,
        adf_statistic=-4.12,
        adf_p_value=0.008,
        hedge_ratio=1.5,
        hedge_ratio_r_squared=0.85,
        half_life_days=5.2,
        passed=True,
    )

    session.add_all([hypothesis, dataset_a, dataset_b, test_result])
    session.commit()

    # Create backtest result
    backtest = BacktestResult(
        backtest_id=str(uuid4()),
        hypothesis_id=hypothesis.hypothesis_id,
        test_id=test_result.test_id,
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        git_commit_hash="abc123def456",
        config_hash="config123",
        train_window_days=60,
        test_window_days=30,
        num_windows=3,
        entry_threshold=2.0,
        exit_threshold=0.5,
        hedge_ratio=1.5,
        gross_pnl=15234.56,
        net_pnl=12456.78,
        commission_cost=1234.56,
        spread_cost=789.12,
        slippage_cost=456.78,
        funding_cost=123.45,
        borrow_cost=173.87,
        num_trades=45,
        turnover=2.5,
        avg_holding_time_hours=48.5,
        median_holding_time_hours=36.0,
        sharpe_ratio=1.85,
        sortino_ratio=2.15,
        volatility=0.12,
        max_drawdown=0.08,
        win_rate=0.62,
        profit_factor=1.75,
        net_pnl_2x_costs=9123.45,
        net_pnl_half_costs=13890.12,
        baseline_sharpe=0.45,
    )

    session.add(backtest)
    session.commit()

    # Query back
    result = session.query(BacktestResult).first()
    assert result is not None
    assert result.gross_pnl == 15234.56
    assert result.net_pnl == 12456.78
    assert result.sharpe_ratio == 1.85


def test_critic_review_creation(session: Session):
    """Test creating a critic review record."""
    # Create prerequisite records (simplified)
    hypothesis = Hypothesis(
        hypothesis_id=str(uuid4()),
        asset_a="AAPL",
        asset_b="MSFT",
        rationale="Test",
        source="test",
        created_by="test",
    )
    dataset_a = Dataset(
        dataset_id=str(uuid4()),
        symbol="AAPL",
        source="test",
        timeframe="15m",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        bar_count=1000,
        adjustment_mode="none",
        file_path="/test/a.parquet",
    )
    dataset_b = Dataset(
        dataset_id=str(uuid4()),
        symbol="MSFT",
        source="test",
        timeframe="15m",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 6, 30),
        bar_count=1000,
        adjustment_mode="none",
        file_path="/test/b.parquet",
    )
    test_result = StatisticalTestResult(
        test_id=str(uuid4()),
        hypothesis_id=hypothesis.hypothesis_id,
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        train_start=datetime(2024, 1, 1),
        train_end=datetime(2024, 4, 30),
        test_start=datetime(2024, 5, 1),
        test_end=datetime(2024, 6, 30),
        cointegration_statistic=-3.45,
        cointegration_p_value=0.012,
        adf_statistic=-4.12,
        adf_p_value=0.008,
        hedge_ratio=1.5,
        hedge_ratio_r_squared=0.85,
        half_life_days=5.2,
        passed=True,
    )
    backtest = BacktestResult(
        backtest_id=str(uuid4()),
        hypothesis_id=hypothesis.hypothesis_id,
        test_id=test_result.test_id,
        dataset_a_id=dataset_a.dataset_id,
        dataset_b_id=dataset_b.dataset_id,
        git_commit_hash="abc123",
        config_hash="config123",
        train_window_days=60,
        test_window_days=30,
        num_windows=3,
        entry_threshold=2.0,
        exit_threshold=0.5,
        hedge_ratio=1.5,
        gross_pnl=15234.56,
        net_pnl=12456.78,
        commission_cost=1234.56,
        spread_cost=789.12,
        slippage_cost=456.78,
        funding_cost=123.45,
        borrow_cost=173.87,
        num_trades=45,
        turnover=2.5,
        avg_holding_time_hours=48.5,
        median_holding_time_hours=36.0,
        sharpe_ratio=1.85,
        sortino_ratio=2.15,
        volatility=0.12,
        max_drawdown=0.08,
        win_rate=0.62,
        profit_factor=1.75,
        net_pnl_2x_costs=9123.45,
        net_pnl_half_costs=13890.12,
        baseline_sharpe=0.45,
    )

    session.add_all([hypothesis, dataset_a, dataset_b])
    session.flush()  # Flush to ensure these are inserted first
    
    session.add(test_result)
    session.flush()  # Flush to ensure test_result is inserted before backtest
    
    session.add(backtest)
    session.commit()

    # Create critic review
    review = CriticReview(
        review_id=str(uuid4()),
        backtest_id=backtest.backtest_id,
        lookahead_bias_detected=False,
        overfitting_indicators=["High in-sample Sharpe"],
        weak_assumptions=["Short half-life"],
        insufficient_testing=[],
        cost_concerns=[],
        operational_concerns=[],
        status="quarantined",
        recommendation="Retest with longer data period",
        objections="Half-life is below 1 day threshold",
    )

    session.add(review)
    session.commit()

    # Query back
    result = session.query(CriticReview).first()
    assert result is not None
    assert result.status == "quarantined"
    assert result.lookahead_bias_detected is False


def test_experiment_lifecycle(session: Session):
    """Test experiment lifecycle tracking."""
    # Create hypothesis
    hypothesis = Hypothesis(
        hypothesis_id=str(uuid4()),
        asset_a="AAPL",
        asset_b="MSFT",
        rationale="Test",
        source="test",
        created_by="test",
    )

    session.add(hypothesis)
    session.commit()

    # Create experiment
    experiment = Experiment(
        experiment_id=str(uuid4()),
        hypothesis_id=hypothesis.hypothesis_id,
        status="new",
    )

    session.add(experiment)
    session.commit()

    # Update experiment status
    experiment.status = "data_validation"
    experiment.current_agent = "data_agent"
    experiment.data_quality_passed = True
    session.commit()

    # Query back
    result = session.query(Experiment).first()
    assert result is not None
    assert result.status == "data_validation"
    assert result.data_quality_passed is True
    assert result.hypothesis.asset_a == "AAPL"


def test_report_artifact_creation(session: Session):
    """Test creating a report artifact record."""
    # Create prerequisite records
    hypothesis = Hypothesis(
        hypothesis_id=str(uuid4()),
        asset_a="AAPL",
        asset_b="MSFT",
        rationale="Test",
        source="test",
        created_by="test",
    )
    experiment = Experiment(
        experiment_id=str(uuid4()),
        hypothesis_id=hypothesis.hypothesis_id,
        status="completed",
    )

    session.add_all([hypothesis, experiment])
    session.commit()

    # Create report artifact
    artifact = ReportArtifact(
        artifact_id=str(uuid4()),
        experiment_id=experiment.experiment_id,
        artifact_type="backtest_report",
        file_path="/reports/backtest_123.html",
        format="html",
    )

    session.add(artifact)
    session.commit()

    # Query back
    result = session.query(ReportArtifact).first()
    assert result is not None
    assert result.artifact_type == "backtest_report"
    assert result.format == "html"
