"""
Data models for the Structured Registry.

This module defines SQLAlchemy ORM models for all entities in the system:
- Hypotheses: Trading pair candidates with rationale
- Datasets: OHLCV data with quality metrics
- Data Quality Reports: Validation reports linked to datasets
- Statistical Test Results: Cointegration and ADF test results
- Backtest Results: Performance metrics and cost attribution
- Critic Reviews: Validation and objection tracking
- Experiments: Full lifecycle tracking from hypothesis to decision

Requirements: 9.1-9.11, 27.14
"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utc_now() -> datetime:
    """Return a naive UTC timestamp for the current SQLite schema."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Hypothesis(Base):
    """
    Hypothesis record for candidate trading pairs.

    Stores generated hypotheses with rationale, novelty scores, and status tracking.
    Requirements: 9.2, 3.1-3.7
    """

    __tablename__ = "hypotheses"

    # Primary key
    hypothesis_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Asset pair
    asset_a: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    asset_b: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Rationale and source
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "llm_generated", "rule_based", "user_provided"

    # Novelty tracking
    similar_hypotheses: Mapped[str | None] = mapped_column(JSON, nullable=True)  # List of UUIDs
    novelty_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="new", index=True
    )  # "new", "testing", "rejected", "approved", "quarantined"

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # "hypothesis_agent" or user ID

    # Relationships
    experiments: Mapped[list["Experiment"]] = relationship(
        "Experiment", back_populates="hypothesis"
    )


class Dataset(Base):
    """
    Dataset record for OHLCV data with quality metrics.

    Stores dataset metadata, provenance, and quality validation results.
    Requirements: 9.3, 2.10
    """

    __tablename__ = "datasets"

    # Primary key
    dataset_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Asset and source
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "yahoo", "alpaca", "polygon", "ccxt"
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)  # "15m", "5m", "1m"

    # Time range
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Quality metrics
    bar_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outlier_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)  # 0.0-1.0

    # Provenance
    adjustment_mode: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "split", "dividend", "none"
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    extra_metadata: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )  # Timezone, exchange, etc.

    # Relationships
    quality_reports: Mapped[list["DataQualityReportRecord"]] = relationship(
        "DataQualityReportRecord", back_populates="dataset"
    )


class DataQualityReportRecord(Base):
    """
    Durable data quality report linked to one dataset.

    Stores validation metrics and issue details generated before statistical tests or backtests.
    Requirements: 2.7-2.10, 9.3
    """

    __tablename__ = "data_quality_reports"

    report_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id"), nullable=False, index=True
    )

    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False)

    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    bar_count: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_bar_count: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_bars: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_timestamps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outlier_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    zero_price_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    impossible_candle_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    abnormal_volume_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    timezone_normalized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    alignment_score: Mapped[float] = mapped_column(Float, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    issues: Mapped[list | None] = mapped_column(JSON, nullable=True)
    report_path: Mapped[str] = mapped_column(String(500), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)

    dataset: Mapped["Dataset"] = relationship("Dataset", back_populates="quality_reports")


class StatisticalTestResult(Base):
    """
    Statistical test results for pair validation.

    Stores cointegration tests, ADF tests, hedge ratios, and half-life estimates.
    Requirements: 9.6, 4.1-4.12
    """

    __tablename__ = "statistical_test_results"

    # Primary key
    test_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Foreign keys
    hypothesis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hypotheses.hypothesis_id"), nullable=False, index=True
    )
    dataset_a_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id"), nullable=False
    )
    dataset_b_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id"), nullable=False
    )

    # Time windows
    train_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    train_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    test_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    test_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Cointegration test
    cointegration_statistic: Mapped[float] = mapped_column(Float, nullable=False)
    cointegration_p_value: Mapped[float] = mapped_column(Float, nullable=False)

    # ADF test
    adf_statistic: Mapped[float] = mapped_column(Float, nullable=False)
    adf_p_value: Mapped[float] = mapped_column(Float, nullable=False)

    # Hedge ratio
    hedge_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    hedge_ratio_r_squared: Mapped[float] = mapped_column(Float, nullable=False)

    # Mean reversion
    half_life_days: Mapped[float] = mapped_column(Float, nullable=False)

    # Regime detection
    regime_changes_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Pass/fail
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    tested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)


class BacktestResult(Base):
    """
    Backtest results with performance metrics and cost attribution.

    Stores comprehensive backtest results including PnL, costs, risk metrics, and sensitivity.
    Requirements: 9.7, 5.1-5.14, 6.1-6.12
    """

    __tablename__ = "backtest_results"

    # Primary key
    backtest_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign keys
    hypothesis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hypotheses.hypothesis_id"), nullable=False, index=True
    )
    test_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("statistical_test_results.test_id"), nullable=False
    )
    dataset_a_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id"), nullable=False
    )
    dataset_b_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("datasets.dataset_id"), nullable=False
    )

    # Reproducibility tracking
    git_commit_hash: Mapped[str] = mapped_column(String(40), nullable=False)
    config_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dataset_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_command: Mapped[list] = mapped_column(JSON, nullable=False)
    run_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    lock_file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_time_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Walk-forward configuration
    train_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    test_window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    num_windows: Mapped[int] = mapped_column(Integer, nullable=False)

    # Strategy parameters
    entry_threshold: Mapped[float] = mapped_column(Float, nullable=False)  # Z-score
    exit_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    hedge_ratio: Mapped[float] = mapped_column(Float, nullable=False)

    # Performance metrics - PnL
    gross_pnl: Mapped[float] = mapped_column(Float, nullable=False)
    net_pnl: Mapped[float] = mapped_column(Float, nullable=False)

    # Cost attribution
    commission_cost: Mapped[float] = mapped_column(Float, nullable=False)
    spread_cost: Mapped[float] = mapped_column(Float, nullable=False)
    slippage_cost: Mapped[float] = mapped_column(Float, nullable=False)
    funding_cost: Mapped[float] = mapped_column(Float, nullable=False)
    borrow_cost: Mapped[float] = mapped_column(Float, nullable=False)

    # Trade statistics
    num_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    turnover: Mapped[float] = mapped_column(Float, nullable=False)  # Portfolio value traded per day
    avg_holding_time_hours: Mapped[float] = mapped_column(Float, nullable=False)
    median_holding_time_hours: Mapped[float] = mapped_column(Float, nullable=False)

    # Risk metrics
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    sortino_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    volatility: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=False)

    # Sensitivity analysis
    net_pnl_2x_costs: Mapped[float] = mapped_column(Float, nullable=False)
    net_pnl_half_costs: Mapped[float] = mapped_column(Float, nullable=False)

    # Baseline comparison
    baseline_sharpe: Mapped[float] = mapped_column(Float, nullable=False)

    # Metadata
    tested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)


class CriticReview(Base):
    """
    Critic review results with detected issues and recommendations.

    Stores validation results, objections, and final approval status.
    Requirements: 9.8, 7.1-7.10
    """

    __tablename__ = "critic_reviews"

    # Primary key
    review_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign key
    backtest_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("backtest_results.backtest_id"), nullable=False, index=True
    )

    # Detected issues
    lookahead_bias_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    overfitting_indicators: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # List of strings
    weak_assumptions: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of strings
    insufficient_testing: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # List of strings
    cost_concerns: Mapped[list | None] = mapped_column(JSON, nullable=True)  # List of strings
    operational_concerns: Mapped[list | None] = mapped_column(
        JSON, nullable=True
    )  # List of strings

    # Decision
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "approved", "rejected", "quarantined"
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    objections: Mapped[str] = mapped_column(Text, nullable=False)  # Human-readable summary

    # Metadata
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)


class Experiment(Base):
    """
    Experiment record tracking full lifecycle from hypothesis to decision.

    Coordinates all stages of the research workflow and stores final decisions.
    Requirements: 9.9, 12.1-12.10
    """

    __tablename__ = "experiments"

    # Primary key
    experiment_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign key
    hypothesis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hypotheses.hypothesis_id"), nullable=False, index=True
    )

    # Lifecycle tracking
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="new", index=True
    )  # "new", "data_validation", "statistical_testing", "backtesting", "critic_review", "reporting", "completed"
    current_agent: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Stage completion flags
    data_quality_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    statistical_tests_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    backtest_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    critic_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Final decision
    final_decision: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )  # "rejected", "quarantined", "approved", "eligible_for_demo"
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    hypothesis: Mapped["Hypothesis"] = relationship("Hypothesis", back_populates="experiments")


class ReportArtifact(Base):
    """
    Report artifact links for generated reports.

    Stores links to HTML/PDF reports and visualizations.
    Requirements: 9.10, 11.10
    """

    __tablename__ = "report_artifacts"

    # Primary key
    artifact_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )

    # Foreign key
    experiment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiments.experiment_id"), nullable=False, index=True
    )

    # Artifact details
    artifact_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "backtest_report", "data_quality_report", "equity_curve", etc.
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    format: Mapped[str] = mapped_column(String(20), nullable=False)  # "html", "pdf", "png", "json"

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utc_now)


# Export all models
__all__ = [
    "Base",
    "Hypothesis",
    "Dataset",
    "DataQualityReportRecord",
    "StatisticalTestResult",
    "BacktestResult",
    "CriticReview",
    "Experiment",
    "ReportArtifact",
]
