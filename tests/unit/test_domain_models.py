"""Unit tests for Pydantic domain models."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from stat_arb.domain import (
    AdjustmentMode,
    BacktestResult,
    CriticReview,
    Dataset,
    DatasetSource,
    Experiment,
    ExperimentStatus,
    FinalDecision,
    Hypothesis,
    HypothesisSource,
    HypothesisStatus,
    ReviewStatus,
    StatisticalTestResult,
)


def test_hypothesis_normalizes_symbols_and_defaults() -> None:
    """Hypothesis should normalize pair symbols and set safe defaults."""
    hypothesis = Hypothesis(
        asset_a=" btc/usdt ",
        asset_b="eth/usdt",
        rationale="Large liquid crypto pair.",
        source=HypothesisSource.RULE_BASED,
        created_by="test",
    )

    assert hypothesis.asset_a == "BTC/USDT"
    assert hypothesis.asset_b == "ETH/USDT"
    assert hypothesis.status == HypothesisStatus.NEW
    assert hypothesis.created_at.tzinfo == UTC


def test_hypothesis_rejects_self_pair() -> None:
    """A hypothesis cannot test an asset against itself."""
    with pytest.raises(ValidationError, match="asset_a and asset_b"):
        Hypothesis(
            asset_a="AAPL",
            asset_b="aapl",
            rationale="Invalid self pair.",
            source=HypothesisSource.USER_PROVIDED,
            created_by="test",
        )


def test_dataset_validates_range_and_score() -> None:
    """Dataset should validate date order and score bounds."""
    dataset = Dataset(
        symbol="msft",
        source=DatasetSource.POLYGON,
        timeframe="15m",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 2, 1, tzinfo=timezone(timedelta(hours=3))),
        bar_count=100,
        missing_bars=1,
        outlier_count=0,
        quality_score=0.99,
        adjustment_mode=AdjustmentMode.SPLIT,
        file_path="data/parquet/msft.parquet",
    )

    assert dataset.symbol == "MSFT"
    assert dataset.start_date.tzinfo == UTC
    assert dataset.end_date.tzinfo == UTC

    with pytest.raises(ValidationError, match="end_date must be after"):
        Dataset(
            symbol="MSFT",
            source=DatasetSource.POLYGON,
            timeframe="15m",
            start_date=datetime(2024, 2, 1),
            end_date=datetime(2024, 1, 1),
            bar_count=100,
            file_path="data/parquet/msft.parquet",
        )


def test_statistical_test_requires_ordered_windows_and_rejection_reason() -> None:
    """Statistical tests should protect train/test boundaries."""
    hypothesis_id = uuid4()
    dataset_a_id = uuid4()
    dataset_b_id = uuid4()

    result = StatisticalTestResult(
        hypothesis_id=hypothesis_id,
        dataset_a_id=dataset_a_id,
        dataset_b_id=dataset_b_id,
        train_start=datetime(2024, 1, 1),
        train_end=datetime(2024, 3, 1),
        test_start=datetime(2024, 3, 1),
        test_end=datetime(2024, 4, 1),
        cointegration_statistic=-3.1,
        cointegration_p_value=0.03,
        adf_statistic=-4.2,
        adf_p_value=0.01,
        hedge_ratio=1.2,
        hedge_ratio_r_squared=0.8,
        half_life_days=5.0,
        passed=True,
    )

    assert result.passed is True

    with pytest.raises(ValidationError, match="failed statistical tests"):
        StatisticalTestResult(
            hypothesis_id=hypothesis_id,
            dataset_a_id=dataset_a_id,
            dataset_b_id=dataset_b_id,
            train_start=datetime(2024, 1, 1),
            train_end=datetime(2024, 3, 1),
            test_start=datetime(2024, 3, 1),
            test_end=datetime(2024, 4, 1),
            cointegration_statistic=-1.0,
            cointegration_p_value=0.5,
            adf_statistic=-1.0,
            adf_p_value=0.5,
            hedge_ratio=1.0,
            hedge_ratio_r_squared=0.1,
            half_life_days=5.0,
            passed=False,
        )


def test_backtest_validates_cost_attribution() -> None:
    """Backtest net PnL should match gross PnL minus all costs."""
    common = {
        "hypothesis_id": uuid4(),
        "test_id": uuid4(),
        "dataset_a_id": uuid4(),
        "dataset_b_id": uuid4(),
        "git_commit_hash": "abcdef1",
        "config_hash": "config-hash",
        "train_window_days": 60,
        "test_window_days": 30,
        "num_windows": 3,
        "entry_threshold": 2.0,
        "exit_threshold": 0.5,
        "hedge_ratio": 1.2,
        "gross_pnl": 100.0,
        "commission_cost": 10.0,
        "spread_cost": 5.0,
        "slippage_cost": 3.0,
        "funding_cost": 1.0,
        "borrow_cost": 1.0,
        "num_trades": 4,
        "turnover": 0.8,
        "avg_holding_time_hours": 12.0,
        "median_holding_time_hours": 10.0,
        "sharpe_ratio": 1.1,
        "sortino_ratio": 1.3,
        "volatility": 0.2,
        "max_drawdown": 0.1,
        "win_rate": 0.6,
        "profit_factor": 1.4,
        "net_pnl_2x_costs": 60.0,
        "net_pnl_half_costs": 90.0,
        "baseline_sharpe": 0.2,
    }

    backtest = BacktestResult(net_pnl=80.0, **common)
    assert backtest.net_pnl == 80.0

    with pytest.raises(ValidationError, match="net_pnl must equal"):
        BacktestResult(net_pnl=81.0, **common)


def test_critic_review_rejects_approved_critical_issues() -> None:
    """Critical review findings cannot be approved."""
    with pytest.raises(ValidationError, match="critical issues"):
        CriticReview(
            backtest_id=uuid4(),
            lookahead_bias_detected=True,
            status=ReviewStatus.APPROVED,
            recommendation="Approve anyway",
            objections="Bias detected",
        )


def test_experiment_requires_final_decision_when_completed() -> None:
    """Completed experiments should include the final decision."""
    with pytest.raises(ValidationError, match="final_decision"):
        Experiment(
            hypothesis_id=uuid4(),
            status=ExperimentStatus.COMPLETED,
        )

    experiment = Experiment(
        hypothesis_id=uuid4(),
        status=ExperimentStatus.COMPLETED,
        final_decision=FinalDecision.REJECTED,
        rejection_reason="Negative net PnL after costs.",
    )
    assert experiment.final_decision == FinalDecision.REJECTED


def test_domain_models_forbid_extra_fields() -> None:
    """Domain contracts should reject undeclared payload fields."""
    with pytest.raises(ValidationError, match="Extra inputs"):
        Hypothesis(
            asset_a="AAPL",
            asset_b="MSFT",
            rationale="Test",
            source=HypothesisSource.TEST,
            created_by="test",
            unexpected=True,
        )
