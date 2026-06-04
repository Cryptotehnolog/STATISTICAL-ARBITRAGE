"""Pydantic domain models for research entities.

These models define runtime contracts for agents and services. SQLAlchemy models in
``stat_arb.storage.models`` remain the persistence layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HypothesisSource(StrEnum):
    """Source of a generated or user-provided hypothesis."""

    LLM_GENERATED = "llm_generated"
    RULE_BASED = "rule_based"
    USER_PROVIDED = "user_provided"
    TEST = "test"


class HypothesisStatus(StrEnum):
    """Lifecycle status for a hypothesis."""

    NEW = "new"
    TESTING = "testing"
    REJECTED = "rejected"
    APPROVED = "approved"
    QUARANTINED = "quarantined"


class DatasetSource(StrEnum):
    """Supported dataset source identifiers."""

    CCXT = "ccxt"
    YAHOO = "yahoo"
    ALPACA = "alpaca"
    POLYGON = "polygon"
    TEST = "test"


class AdjustmentMode(StrEnum):
    """Corporate action adjustment mode."""

    SPLIT = "split"
    DIVIDEND = "dividend"
    NONE = "none"


class DataQualitySeverity(StrEnum):
    """Severity for data quality findings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ReviewStatus(StrEnum):
    """Critic review decision status."""

    APPROVED = "approved"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


class ExperimentStatus(StrEnum):
    """Experiment lifecycle status."""

    NEW = "new"
    DATA_VALIDATION = "data_validation"
    STATISTICAL_TESTING = "statistical_testing"
    BACKTESTING = "backtesting"
    CRITIC_REVIEW = "critic_review"
    REPORTING = "reporting"
    COMPLETED = "completed"


class FinalDecision(StrEnum):
    """Final experiment decision."""

    REJECTED = "rejected"
    QUARANTINED = "quarantined"
    APPROVED = "approved"
    ELIGIBLE_FOR_DEMO = "eligible_for_demo"
    RETEST = "retest"
    PROMOTE = "promote"


class ArtifactType(StrEnum):
    """Report artifact type."""

    BACKTEST_REPORT = "backtest_report"
    DATA_QUALITY_REPORT = "data_quality_report"
    EQUITY_CURVE = "equity_curve"
    DRAWDOWN_CHART = "drawdown_chart"
    COST_ATTRIBUTION = "cost_attribution"
    JSON_SUMMARY = "json_summary"


class ArtifactFormat(StrEnum):
    """Report artifact file format."""

    HTML = "html"
    PDF = "pdf"
    PNG = "png"
    JSON = "json"


class DomainModel(BaseModel):
    """Base model for domain contracts."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        use_enum_values=True,
    )

    @field_validator("*", mode="before")
    @classmethod
    def normalize_datetime_values(cls, value: Any) -> Any:
        """Normalize datetimes to timezone-aware UTC values."""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=UTC)
            return value.astimezone(UTC)
        return value


def new_uuid() -> UUID:
    """Return a new UUID for domain entities."""
    return uuid4()


class Hypothesis(DomainModel):
    """Candidate trading pair hypothesis."""

    hypothesis_id: UUID = Field(default_factory=new_uuid)
    asset_a: str = Field(min_length=1, max_length=50)
    asset_b: str = Field(min_length=1, max_length=50)
    rationale: str = Field(min_length=1)
    source: HypothesisSource
    similar_hypotheses: list[UUID] = Field(default_factory=list)
    novelty_score: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = Field(min_length=1, max_length=100)
    status: HypothesisStatus = HypothesisStatus.NEW

    @field_validator("asset_a", "asset_b")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize asset symbols to uppercase compact strings."""
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_pair_is_not_identical(self) -> Hypothesis:
        """Reject self-pairs."""
        if self.asset_a == self.asset_b:
            raise ValueError("asset_a and asset_b must be different")
        return self


class Dataset(DomainModel):
    """OHLCV dataset metadata and quality metrics."""

    dataset_id: UUID = Field(default_factory=new_uuid)
    symbol: str = Field(min_length=1, max_length=50)
    source: DatasetSource
    timeframe: str = Field(pattern=r"^\d+[mhdw]$")
    start_date: datetime
    end_date: datetime
    bar_count: int = Field(ge=0)
    missing_bars: int = Field(default=0, ge=0)
    outlier_count: int = Field(default=0, ge=0)
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    adjustment_mode: AdjustmentMode = AdjustmentMode.NONE
    downloaded_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    file_path: Path
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize asset symbols to uppercase compact strings."""
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_time_range(self) -> Dataset:
        """Ensure dataset time range is ordered."""
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        return self


class OHLCVBar(DomainModel):
    """Single normalized OHLCV bar."""

    symbol: str = Field(min_length=1, max_length=50)
    source: DatasetSource
    timeframe: str = Field(pattern=r"^\d+[mhdw]$")
    timestamp: datetime
    open: float = Field(gt=0.0)
    high: float = Field(gt=0.0)
    low: float = Field(gt=0.0)
    close: float = Field(gt=0.0)
    volume: float = Field(ge=0.0)
    exchange: str | None = Field(default=None, min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize asset symbols to uppercase compact strings."""
        return value.strip().upper()

    @field_validator("exchange")
    @classmethod
    def normalize_exchange(cls, value: str | None) -> str | None:
        """Normalize exchange identifiers when provided."""
        if value is None:
            return None
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_candle_bounds(self) -> OHLCVBar:
        """Reject impossible candles."""
        if self.high < max(self.open, self.low, self.close):
            raise ValueError("high must be greater than or equal to open, low, and close")
        if self.low > min(self.open, self.high, self.close):
            raise ValueError("low must be less than or equal to open, high, and close")
        return self


class OHLCVBatch(DomainModel):
    """Ordered batch of normalized OHLCV bars for one symbol/timeframe/source."""

    dataset_id: UUID = Field(default_factory=new_uuid)
    symbol: str = Field(min_length=1, max_length=50)
    source: DatasetSource
    timeframe: str = Field(pattern=r"^\d+[mhdw]$")
    bars: list[OHLCVBar] = Field(min_length=1)
    exchange: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize asset symbols to uppercase compact strings."""
        return value.strip().upper()

    @field_validator("exchange")
    @classmethod
    def normalize_exchange(cls, value: str | None) -> str | None:
        """Normalize exchange identifiers when provided."""
        if value is None:
            return None
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_batch_consistency(self) -> OHLCVBatch:
        """Ensure bars belong to the batch contract and timestamps are unique and ordered."""
        previous_timestamp: datetime | None = None
        for bar in self.bars:
            if bar.symbol != self.symbol:
                raise ValueError("all bars must match batch symbol")
            if bar.source != self.source:
                raise ValueError("all bars must match batch source")
            if bar.timeframe != self.timeframe:
                raise ValueError("all bars must match batch timeframe")
            if self.exchange is not None and bar.exchange not in {None, self.exchange}:
                raise ValueError("bar exchange must match batch exchange")
            if previous_timestamp is not None and bar.timestamp <= previous_timestamp:
                raise ValueError("bar timestamps must be strictly increasing")
            previous_timestamp = bar.timestamp
        return self


class DataQualityIssue(DomainModel):
    """Single data quality finding."""

    code: str = Field(min_length=1, max_length=100)
    severity: DataQualitySeverity
    message: str = Field(min_length=1)
    count: int = Field(default=1, ge=1)
    first_timestamp: datetime | None = None
    last_timestamp: datetime | None = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        """Normalize finding codes for stable matching."""
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_timestamp_range(self) -> DataQualityIssue:
        """Ensure issue timestamp ranges are ordered."""
        if (
            self.first_timestamp is not None
            and self.last_timestamp is not None
            and self.last_timestamp < self.first_timestamp
        ):
            raise ValueError("last_timestamp must be on or after first_timestamp")
        return self


class DataQualityReport(DomainModel):
    """Validation summary for an OHLCV dataset."""

    report_id: UUID = Field(default_factory=new_uuid)
    dataset_id: UUID
    symbol: str = Field(min_length=1, max_length=50)
    source: DatasetSource
    timeframe: str = Field(pattern=r"^\d+[mhdw]$")
    start_date: datetime
    end_date: datetime
    bar_count: int = Field(ge=0)
    expected_bar_count: int = Field(ge=0)
    missing_bars: int = Field(default=0, ge=0)
    duplicate_timestamps: int = Field(default=0, ge=0)
    outlier_count: int = Field(default=0, ge=0)
    zero_price_count: int = Field(default=0, ge=0)
    impossible_candle_count: int = Field(default=0, ge=0)
    abnormal_volume_count: int = Field(default=0, ge=0)
    timezone_normalized: bool
    alignment_score: float = Field(default=1.0, ge=0.0, le=1.0)
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0)
    passed: bool
    issues: list[DataQualityIssue] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize asset symbols to uppercase compact strings."""
        return value.strip().upper()

    @model_validator(mode="after")
    def validate_report_consistency(self) -> DataQualityReport:
        """Validate report time range, counts, and pass/fail explanation."""
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if self.bar_count > self.expected_bar_count:
            raise ValueError("bar_count cannot exceed expected_bar_count")
        if self.missing_bars > self.expected_bar_count:
            raise ValueError("missing_bars cannot exceed expected_bar_count")
        if not self.passed and not self.issues:
            raise ValueError("failed data quality reports require issues")
        if self.passed and any(issue.severity == DataQualitySeverity.ERROR for issue in self.issues):
            raise ValueError("passed data quality reports cannot contain error issues")
        return self


class DataQualityFailureSummary(DomainModel):
    """Concise memory-safe summary of a failed data quality report."""

    report_id: UUID
    dataset_id: UUID
    symbol: str = Field(min_length=1, max_length=50)
    source: DatasetSource
    timeframe: str = Field(pattern=r"^\d+[mhdw]$")
    quality_score: float = Field(ge=0.0, le=1.0)
    issue_codes: list[str] = Field(min_length=1)
    summary: str = Field(min_length=1)
    registry_reference: str = Field(min_length=1)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        """Normalize asset symbols to uppercase compact strings."""
        return value.strip().upper()

    @field_validator("issue_codes")
    @classmethod
    def normalize_issue_codes(cls, value: list[str]) -> list[str]:
        """Normalize issue codes for stable Memory Agent matching."""
        normalized = [code.strip().lower() for code in value if code.strip()]
        if not normalized:
            raise ValueError("issue_codes must include at least one non-empty code")
        return sorted(dict.fromkeys(normalized))


class StatisticalTestResult(DomainModel):
    """Statistical validation result for a pair."""

    test_id: UUID = Field(default_factory=new_uuid)
    hypothesis_id: UUID
    dataset_a_id: UUID
    dataset_b_id: UUID
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    cointegration_statistic: float
    cointegration_p_value: float = Field(ge=0.0, le=1.0)
    adf_statistic: float
    adf_p_value: float = Field(ge=0.0, le=1.0)
    hedge_ratio: float
    hedge_ratio_r_squared: float = Field(ge=0.0, le=1.0)
    half_life_days: float = Field(gt=0.0)
    regime_changes_detected: bool = False
    passed: bool
    rejection_reason: str | None = None
    tested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_windows_and_decision(self) -> StatisticalTestResult:
        """Ensure train/test windows are ordered and failed tests explain why."""
        if self.dataset_a_id == self.dataset_b_id:
            raise ValueError("dataset_a_id and dataset_b_id must be different")
        if self.train_end <= self.train_start:
            raise ValueError("train_end must be after train_start")
        if self.test_start < self.train_end:
            raise ValueError("test_start must be on or after train_end")
        if self.test_end <= self.test_start:
            raise ValueError("test_end must be after test_start")
        if not self.passed and not self.rejection_reason:
            raise ValueError("failed statistical tests require rejection_reason")
        return self


class BacktestResult(DomainModel):
    """Backtest metrics with cost attribution."""

    backtest_id: UUID = Field(default_factory=new_uuid)
    hypothesis_id: UUID
    test_id: UUID
    dataset_a_id: UUID
    dataset_b_id: UUID
    git_commit_hash: str = Field(min_length=7, max_length=40)
    config_hash: str = Field(min_length=1, max_length=64)
    train_window_days: int = Field(gt=0)
    test_window_days: int = Field(gt=0)
    num_windows: int = Field(gt=0)
    entry_threshold: float = Field(gt=0.0)
    exit_threshold: float = Field(ge=0.0)
    hedge_ratio: float
    gross_pnl: float
    net_pnl: float
    commission_cost: float = Field(ge=0.0)
    spread_cost: float = Field(ge=0.0)
    slippage_cost: float = Field(ge=0.0)
    funding_cost: float = Field(ge=0.0)
    borrow_cost: float = Field(ge=0.0)
    num_trades: int = Field(ge=0)
    turnover: float = Field(ge=0.0)
    avg_holding_time_hours: float = Field(ge=0.0)
    median_holding_time_hours: float = Field(ge=0.0)
    sharpe_ratio: float
    sortino_ratio: float
    volatility: float = Field(ge=0.0)
    max_drawdown: float = Field(ge=0.0)
    win_rate: float = Field(ge=0.0, le=1.0)
    profit_factor: float = Field(ge=0.0)
    net_pnl_2x_costs: float
    net_pnl_half_costs: float
    baseline_sharpe: float
    tested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_backtest_consistency(self) -> BacktestResult:
        """Validate backtest references, thresholds, and cost attribution."""
        if self.dataset_a_id == self.dataset_b_id:
            raise ValueError("dataset_a_id and dataset_b_id must be different")
        if self.exit_threshold >= self.entry_threshold:
            raise ValueError("exit_threshold must be lower than entry_threshold")

        total_cost = (
            self.commission_cost
            + self.spread_cost
            + self.slippage_cost
            + self.funding_cost
            + self.borrow_cost
        )
        expected_net_pnl = self.gross_pnl - total_cost
        if abs(self.net_pnl - expected_net_pnl) > 1e-6:
            raise ValueError("net_pnl must equal gross_pnl minus all costs")
        return self


class CriticReview(DomainModel):
    """Automated critic review of a backtest."""

    review_id: UUID = Field(default_factory=new_uuid)
    backtest_id: UUID
    lookahead_bias_detected: bool = False
    overfitting_indicators: list[str] = Field(default_factory=list)
    weak_assumptions: list[str] = Field(default_factory=list)
    insufficient_testing: list[str] = Field(default_factory=list)
    cost_concerns: list[str] = Field(default_factory=list)
    operational_concerns: list[str] = Field(default_factory=list)
    status: ReviewStatus
    recommendation: str = Field(min_length=1)
    objections: str = Field(min_length=1)
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_critical_status(self) -> CriticReview:
        """Critical issues should not be marked approved."""
        critical_issues = self.lookahead_bias_detected or bool(self.insufficient_testing)
        if critical_issues and self.status == ReviewStatus.APPROVED:
            raise ValueError("critical issues cannot be approved")
        return self


class Experiment(DomainModel):
    """Research experiment lifecycle record."""

    experiment_id: UUID = Field(default_factory=new_uuid)
    hypothesis_id: UUID
    status: ExperimentStatus = ExperimentStatus.NEW
    current_agent: str | None = Field(default=None, max_length=100)
    data_quality_passed: bool = False
    statistical_tests_passed: bool = False
    backtest_completed: bool = False
    critic_approved: bool = False
    final_decision: FinalDecision | None = None
    rejection_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    test_id: UUID | None = None
    backtest_id: UUID | None = None
    review_id: UUID | None = None
    report_path: Path | None = None

    @model_validator(mode="after")
    def validate_lifecycle(self) -> Experiment:
        """Ensure completed experiments carry a final decision and timestamps are ordered."""
        if self.completed_at and self.completed_at < self.created_at:
            raise ValueError("completed_at must be after created_at")
        if self.status == ExperimentStatus.COMPLETED and not self.final_decision:
            raise ValueError("completed experiments require final_decision")
        if self.final_decision == FinalDecision.REJECTED and not self.rejection_reason:
            raise ValueError("rejected experiments require rejection_reason")
        return self


class ReportArtifact(DomainModel):
    """Generated report or visualization artifact."""

    artifact_id: UUID = Field(default_factory=new_uuid)
    experiment_id: UUID
    artifact_type: ArtifactType
    file_path: Path
    format: ArtifactFormat
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
