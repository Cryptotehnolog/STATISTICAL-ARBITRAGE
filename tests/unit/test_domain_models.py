"""Unit tests for Pydantic domain models."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from stat_arb.domain import (
    AdjustmentMode,
    ArtifactFormat,
    ArtifactType,
    BacktestResult,
    CriticReview,
    DataQualityFailureSummary,
    DataQualityIssue,
    DataQualityReport,
    DataQualitySeverity,
    Dataset,
    DatasetSource,
    Experiment,
    ExperimentStatus,
    FinalDecision,
    Hypothesis,
    HypothesisSource,
    HypothesisStatus,
    OHLCVBar,
    OHLCVBatch,
    ReportArtifact,
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


def test_ohlcv_bar_normalizes_symbols_and_validates_candle_bounds() -> None:
    """OHLCV bars should normalize metadata and reject impossible candles."""
    bar = OHLCVBar(
        symbol=" btc/usdt ",
        source=DatasetSource.CCXT,
        timeframe="5m",
        timestamp=datetime(2024, 1, 1),
        open=100.0,
        high=105.0,
        low=99.0,
        close=101.0,
        volume=10.5,
        exchange="BINANCE",
    )

    assert bar.symbol == "BTC/USDT"
    assert bar.exchange == "binance"
    assert bar.timestamp.tzinfo == UTC

    with pytest.raises(ValidationError, match="high must be"):
        OHLCVBar(
            symbol="BTC/USDT",
            source=DatasetSource.CCXT,
            timeframe="5m",
            timestamp=datetime(2024, 1, 1),
            open=100.0,
            high=99.0,
            low=98.0,
            close=101.0,
            volume=10.0,
        )


def test_ohlcv_batch_requires_consistent_contract_and_ordered_timestamps() -> None:
    """OHLCV batches should contain one ordered symbol/source/timeframe series."""
    first = OHLCVBar(
        symbol="ETH/USDT",
        source=DatasetSource.CCXT,
        timeframe="15m",
        timestamp=datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
        open=2000.0,
        high=2010.0,
        low=1990.0,
        close=2005.0,
        volume=100.0,
        exchange="kraken",
    )
    second = first.model_copy(update={"timestamp": datetime(2024, 1, 1, 0, 15, tzinfo=UTC)})

    batch = OHLCVBatch(
        symbol=" eth/usdt ",
        source=DatasetSource.CCXT,
        timeframe="15m",
        bars=[first, second],
        exchange="KRAKEN",
    )

    assert batch.symbol == "ETH/USDT"
    assert batch.exchange == "kraken"

    duplicate_timestamp = first.model_copy()
    with pytest.raises(ValidationError, match="strictly increasing"):
        OHLCVBatch(
            symbol="ETH/USDT",
            source=DatasetSource.CCXT,
            timeframe="15m",
            bars=[first, duplicate_timestamp],
        )

    wrong_symbol = second.model_copy(update={"symbol": "BTC/USDT"})
    with pytest.raises(ValidationError, match="batch symbol"):
        OHLCVBatch(
            symbol="ETH/USDT",
            source=DatasetSource.CCXT,
            timeframe="15m",
            bars=[first, wrong_symbol],
        )


def test_data_quality_report_requires_issues_for_failures() -> None:
    """Failed data quality reports should explain the rejected dataset."""
    dataset_id = uuid4()
    issue = DataQualityIssue(
        code="missing_bars",
        severity=DataQualitySeverity.ERROR,
        message="Missing bars exceed the configured threshold.",
        count=12,
        first_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        last_timestamp=datetime(2024, 1, 2, tzinfo=UTC),
    )

    report = DataQualityReport(
        dataset_id=dataset_id,
        symbol="btc/usdt",
        source=DatasetSource.CCXT,
        timeframe="5m",
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 1, 2, tzinfo=UTC),
        bar_count=276,
        expected_bar_count=288,
        missing_bars=12,
        timezone_normalized=True,
        quality_score=0.91,
        passed=False,
        issues=[issue],
    )

    restored = DataQualityReport.model_validate_json(report.model_dump_json())

    assert restored == report
    assert restored.symbol == "BTC/USDT"
    assert restored.issues[0].code == "missing_bars"

    with pytest.raises(ValidationError, match="failed data quality reports"):
        DataQualityReport(
            dataset_id=dataset_id,
            symbol="BTC/USDT",
            source=DatasetSource.CCXT,
            timeframe="5m",
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 2, tzinfo=UTC),
            bar_count=276,
            expected_bar_count=288,
            missing_bars=12,
            timezone_normalized=True,
            passed=False,
        )


def test_data_quality_report_rejects_inconsistent_counts_and_passed_errors() -> None:
    """Quality reports should guard impossible counts and successful error states."""
    dataset_id = uuid4()
    issue = DataQualityIssue(
        code="impossible_candle",
        severity=DataQualitySeverity.ERROR,
        message="High is lower than close.",
    )

    with pytest.raises(ValidationError, match="bar_count cannot exceed"):
        DataQualityReport(
            dataset_id=dataset_id,
            symbol="ETH/USDT",
            source=DatasetSource.CCXT,
            timeframe="15m",
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 2, tzinfo=UTC),
            bar_count=97,
            expected_bar_count=96,
            timezone_normalized=True,
            passed=True,
        )

    with pytest.raises(ValidationError, match="cannot contain error issues"):
        DataQualityReport(
            dataset_id=dataset_id,
            symbol="ETH/USDT",
            source=DatasetSource.CCXT,
            timeframe="15m",
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 2, tzinfo=UTC),
            bar_count=96,
            expected_bar_count=96,
            timezone_normalized=True,
            passed=True,
            issues=[issue],
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
    dataset_a_id = uuid4()
    dataset_b_id = uuid4()
    common = {
        "hypothesis_id": uuid4(),
        "test_id": uuid4(),
        "dataset_a_id": dataset_a_id,
        "dataset_b_id": dataset_b_id,
        "git_commit_hash": "abcdef1",
        "config_hash": "config-hash",
        "dataset_ids": [dataset_a_id, dataset_b_id],
        "random_seed": 12345,
        "execution_command": ["uv", "run", "stat-arb", "backtest"],
        "run_timestamp": datetime(2024, 7, 1, 12, 0, tzinfo=UTC),
        "lock_file_hash": "f" * 64,
        "execution_time_seconds": 12.5,
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


def test_hypothesis_json_round_trip_preserves_core_types() -> None:
    """JSON round-trip should preserve UUID, datetime, enum values, and lists."""
    similar_id = uuid4()
    hypothesis = Hypothesis(
        asset_a="AAPL",
        asset_b="MSFT",
        rationale="Large-cap technology pair.",
        source=HypothesisSource.LLM_GENERATED,
        similar_hypotheses=[similar_id],
        created_by="hypothesis_agent",
        status=HypothesisStatus.TESTING,
        created_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )

    restored = Hypothesis.model_validate_json(hypothesis.model_dump_json())

    assert restored == hypothesis
    assert restored.hypothesis_id == hypothesis.hypothesis_id
    assert restored.similar_hypotheses == [similar_id]
    assert restored.created_at.tzinfo == UTC
    assert restored.model_dump(mode="json")["status"] == "testing"


def test_dataset_json_round_trip_serializes_paths_and_metadata() -> None:
    """Dataset JSON serialization should preserve paths and metadata."""
    dataset = Dataset(
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="5m",
        start_date=datetime(2024, 1, 1, tzinfo=UTC),
        end_date=datetime(2024, 1, 2, tzinfo=UTC),
        bar_count=288,
        file_path="data/parquet/btc_usdt.parquet",
        metadata={"exchange": "binance", "timezone": "UTC"},
    )

    restored = Dataset.model_validate_json(dataset.model_dump_json())

    assert restored == dataset
    assert restored.file_path == dataset.file_path
    assert restored.metadata["exchange"] == "binance"


def test_assignment_validation_rechecks_model_invariants() -> None:
    """Assignment validation should keep existing objects inside contract bounds."""
    hypothesis = Hypothesis(
        asset_a="AAPL",
        asset_b="MSFT",
        rationale="Technology pair.",
        source=HypothesisSource.TEST,
        created_by="test",
    )

    with pytest.raises(ValidationError, match="less than or equal"):
        hypothesis.novelty_score = 1.5

    with pytest.raises(ValidationError, match="asset_a and asset_b"):
        hypothesis.asset_b = "AAPL"


def test_mutable_defaults_are_not_shared_between_instances() -> None:
    """List and dict defaults should not leak across model instances."""
    first_review = CriticReview(
        backtest_id=uuid4(),
        status=ReviewStatus.QUARANTINED,
        recommendation="Retest",
        objections="Weak assumptions",
    )
    second_review = CriticReview(
        backtest_id=uuid4(),
        status=ReviewStatus.QUARANTINED,
        recommendation="Retest",
        objections="Weak assumptions",
    )

    first_review.weak_assumptions.append("Short sample")

    assert second_review.weak_assumptions == []


def test_report_artifact_round_trip_preserves_format_and_type() -> None:
    """Report artifacts should round-trip through JSON for report workflows."""
    artifact = ReportArtifact(
        experiment_id=uuid4(),
        artifact_type=ArtifactType.BACKTEST_REPORT,
        file_path="reports/backtest.html",
        format=ArtifactFormat.HTML,
        created_at=datetime(2024, 1, 3, tzinfo=UTC),
    )

    restored = ReportArtifact.model_validate_json(artifact.model_dump_json())

    assert restored == artifact
    assert restored.model_dump(mode="json")["artifact_type"] == "backtest_report"
    assert restored.model_dump(mode="json")["format"] == "html"


def test_all_domain_models_round_trip_through_json() -> None:
    """Every domain entity contract should survive JSON serialization."""
    dataset_a_id = uuid4()
    dataset_b_id = uuid4()
    hypothesis_id = uuid4()
    test_id = uuid4()
    backtest_id = uuid4()
    issue = DataQualityIssue(
        code="missing_bars",
        severity=DataQualitySeverity.ERROR,
        message="Missing OHLCV bars.",
        count=2,
        first_timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        last_timestamp=datetime(2024, 1, 1, 0, 10, tzinfo=UTC),
    )
    bar = OHLCVBar(
        symbol="BTC/USDT",
        source=DatasetSource.CCXT,
        timeframe="5m",
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        open=100.0,
        high=102.0,
        low=99.0,
        close=101.0,
        volume=10.0,
        exchange="binance",
    )
    models = [
        Hypothesis(
            hypothesis_id=hypothesis_id,
            asset_a="BTC/USDT",
            asset_b="ETH/USDT",
            rationale="Liquid crypto pair.",
            source=HypothesisSource.RULE_BASED,
            created_by="test",
        ),
        Dataset(
            dataset_id=dataset_a_id,
            symbol="BTC/USDT",
            source=DatasetSource.CCXT,
            timeframe="5m",
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 2, tzinfo=UTC),
            bar_count=288,
            file_path="data/parquet/btc.parquet",
        ),
        bar,
        OHLCVBatch(
            dataset_id=dataset_a_id,
            symbol="BTC/USDT",
            source=DatasetSource.CCXT,
            timeframe="5m",
            bars=[
                bar,
                bar.model_copy(update={"timestamp": datetime(2024, 1, 1, 0, 5, tzinfo=UTC)}),
            ],
            exchange="binance",
        ),
        issue,
        DataQualityReport(
            dataset_id=dataset_a_id,
            symbol="BTC/USDT",
            source=DatasetSource.CCXT,
            timeframe="5m",
            start_date=datetime(2024, 1, 1, tzinfo=UTC),
            end_date=datetime(2024, 1, 2, tzinfo=UTC),
            bar_count=286,
            expected_bar_count=288,
            missing_bars=2,
            timezone_normalized=True,
            passed=False,
            issues=[issue],
        ),
        DataQualityFailureSummary(
            report_id=uuid4(),
            dataset_id=dataset_a_id,
            symbol="BTC/USDT",
            source=DatasetSource.CCXT,
            timeframe="5m",
            quality_score=0.98,
            issue_codes=["missing_bars"],
            summary="Dataset failed quality validation.",
            registry_reference="data_quality_reports/report-1",
        ),
        StatisticalTestResult(
            test_id=test_id,
            hypothesis_id=hypothesis_id,
            dataset_a_id=dataset_a_id,
            dataset_b_id=dataset_b_id,
            train_start=datetime(2024, 1, 1, tzinfo=UTC),
            train_end=datetime(2024, 2, 1, tzinfo=UTC),
            test_start=datetime(2024, 2, 1, tzinfo=UTC),
            test_end=datetime(2024, 3, 1, tzinfo=UTC),
            cointegration_statistic=-3.2,
            cointegration_p_value=0.02,
            adf_statistic=-4.1,
            adf_p_value=0.01,
            hedge_ratio=1.4,
            hedge_ratio_r_squared=0.82,
            half_life_days=4.5,
            passed=True,
        ),
        BacktestResult(
            backtest_id=backtest_id,
            hypothesis_id=hypothesis_id,
            test_id=test_id,
            dataset_a_id=dataset_a_id,
            dataset_b_id=dataset_b_id,
            git_commit_hash="abcdef1",
            config_hash="cfg",
            dataset_ids=[dataset_a_id, dataset_b_id],
            random_seed=12345,
            execution_command=["uv", "run", "stat-arb", "backtest"],
            run_timestamp=datetime(2024, 7, 1, 12, 0, tzinfo=UTC),
            lock_file_hash="f" * 64,
            execution_time_seconds=12.5,
            train_window_days=60,
            test_window_days=30,
            num_windows=2,
            entry_threshold=2.0,
            exit_threshold=0.5,
            hedge_ratio=1.4,
            gross_pnl=100.0,
            net_pnl=80.0,
            commission_cost=10.0,
            spread_cost=5.0,
            slippage_cost=3.0,
            funding_cost=1.0,
            borrow_cost=1.0,
            num_trades=8,
            turnover=1.2,
            avg_holding_time_hours=12.0,
            median_holding_time_hours=10.0,
            sharpe_ratio=1.1,
            sortino_ratio=1.3,
            volatility=0.2,
            max_drawdown=0.1,
            win_rate=0.6,
            profit_factor=1.4,
            net_pnl_2x_costs=60.0,
            net_pnl_half_costs=90.0,
            baseline_sharpe=0.2,
        ),
        CriticReview(
            review_id=uuid4(),
            backtest_id=backtest_id,
            status=ReviewStatus.QUARANTINED,
            recommendation="Retest on more data.",
            objections="Short sample.",
        ),
        Experiment(
            experiment_id=uuid4(),
            hypothesis_id=hypothesis_id,
            status=ExperimentStatus.COMPLETED,
            final_decision=FinalDecision.APPROVED,
            created_at=datetime(2024, 1, 1, tzinfo=UTC),
            completed_at=datetime(2024, 1, 2, tzinfo=UTC),
            test_id=test_id,
            backtest_id=backtest_id,
            report_path="reports/experiment.html",
        ),
        ReportArtifact(
            experiment_id=uuid4(),
            artifact_type=ArtifactType.JSON_SUMMARY,
            file_path="reports/summary.json",
            format=ArtifactFormat.JSON,
        ),
    ]

    for model in models:
        restored = model.__class__.model_validate_json(model.model_dump_json())
        assert restored == model
