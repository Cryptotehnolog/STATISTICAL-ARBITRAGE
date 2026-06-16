"""Critic Agent lookahead-bias detection boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from stat_arb.memory import MemoryRecordType, MemoryWriteRequest
from stat_arb.statistical import WalkForwardWindow, assert_no_lookahead
from stat_arb.storage.models import BacktestResult as StoredBacktestResult
from stat_arb.storage.models import CriticReview as StoredCriticReview


class MemoryWriter(Protocol):
    """Minimal Memory Agent service protocol used by this boundary."""

    def write(self, request: MemoryWriteRequest) -> object:
        """Write a policy-approved memory record."""


@dataclass(frozen=True)
class CriticLookaheadPolicy:
    """Explicit policy contract for lookahead-bias detection."""

    require_strictly_past_signals: bool
    require_strictly_past_position_sizing: bool
    require_valid_walk_forward_windows: bool

    def __post_init__(self) -> None:
        if not any(
            (
                self.require_strictly_past_signals,
                self.require_strictly_past_position_sizing,
                self.require_valid_walk_forward_windows,
            )
        ):
            raise ValueError("at least one lookahead rule must be enabled")


@dataclass(frozen=True)
class CriticLookaheadEvidence:
    """Evidence required to detect future-information usage."""

    signal_decision_indices: tuple[int, ...]
    signal_data_through_indices: tuple[int, ...]
    position_decision_indices: tuple[int, ...]
    position_data_through_indices: tuple[int, ...]
    walk_forward_windows: tuple[WalkForwardWindow, ...]

    def __post_init__(self) -> None:
        _validate_index_pairs(
            self.signal_decision_indices,
            self.signal_data_through_indices,
            label="signal",
        )
        _validate_index_pairs(
            self.position_decision_indices,
            self.position_data_through_indices,
            label="position",
        )


@dataclass(frozen=True)
class CriticLookaheadAssessment:
    """Result of lookahead-bias detection."""

    lookahead_bias_detected: bool
    issues: tuple[str, ...]
    checked_rules: tuple[str, ...]


@dataclass(frozen=True)
class CriticOverfittingPolicy:
    """Explicit policy contract for overfitting detection."""

    max_sharpe_degradation: float | None
    max_parameter_to_data_ratio: float | None
    near_perfect_in_sample_sharpe: float | None
    near_perfect_min_trades: int | None

    def __post_init__(self) -> None:
        if not any(
            value is not None
            for value in (
                self.max_sharpe_degradation,
                self.max_parameter_to_data_ratio,
                self.near_perfect_in_sample_sharpe,
            )
        ):
            raise ValueError("at least one overfitting rule must be enabled")
        if self.max_sharpe_degradation is not None and self.max_sharpe_degradation < 0:
            raise ValueError("max_sharpe_degradation must be non-negative")
        if self.max_parameter_to_data_ratio is not None and self.max_parameter_to_data_ratio <= 0:
            raise ValueError("max_parameter_to_data_ratio must be positive")
        if self.near_perfect_in_sample_sharpe is not None:
            if self.near_perfect_in_sample_sharpe <= 0:
                raise ValueError("near_perfect_in_sample_sharpe must be positive")
            if self.near_perfect_min_trades is None or self.near_perfect_min_trades <= 0:
                raise ValueError("near_perfect_min_trades must be positive")


@dataclass(frozen=True)
class CriticOverfittingEvidence:
    """Evidence required to detect overfitting risk."""

    in_sample_sharpe: float
    out_of_sample_sharpe: float
    parameter_count: int
    data_point_count: int
    in_sample_trade_count: int | None = None

    def __post_init__(self) -> None:
        for label, value in (
            ("in_sample_sharpe", self.in_sample_sharpe),
            ("out_of_sample_sharpe", self.out_of_sample_sharpe),
        ):
            if not isfinite(value):
                raise ValueError(f"{label} must be finite")
        if isinstance(self.parameter_count, bool) or self.parameter_count < 0:
            raise ValueError("parameter_count must be non-negative")
        if isinstance(self.data_point_count, bool) or self.data_point_count <= 0:
            raise ValueError("data_point_count must be positive")
        if self.in_sample_trade_count is not None and (
            isinstance(self.in_sample_trade_count, bool) or self.in_sample_trade_count < 0
        ):
            raise ValueError("in_sample_trade_count must be non-negative")


@dataclass(frozen=True)
class CriticOverfittingAssessment:
    """Result of overfitting-risk detection."""

    overfitting_detected: bool
    indicators: tuple[str, ...]
    checked_rules: tuple[str, ...]


@dataclass(frozen=True)
class CriticWeakAssumptionPolicy:
    """Explicit policy contract for weak-assumption detection."""

    cointegration_alpha: float | None
    p_value_warning_margin: float | None
    min_half_life_days: float | None
    max_half_life_days: float | None
    flag_unaddressed_regime_changes: bool
    min_hedge_ratio_r_squared: float | None
    min_ljung_box_p_value: float | None
    min_jarque_bera_p_value: float | None
    max_abs_excess_kurtosis: float | None
    max_hedge_ratio_stability_std: float | None = None
    max_hedge_ratio_stability_max_abs_change: float | None = None
    min_cointegration_stability_pass_ratio: float | None = None

    def __post_init__(self) -> None:
        if not any(
            (
                self.cointegration_alpha is not None and self.p_value_warning_margin is not None,
                self.min_half_life_days is not None or self.max_half_life_days is not None,
                self.flag_unaddressed_regime_changes,
                self.min_hedge_ratio_r_squared is not None,
                self.min_ljung_box_p_value is not None,
                self.min_jarque_bera_p_value is not None,
                self.max_abs_excess_kurtosis is not None,
                self.max_hedge_ratio_stability_std is not None,
                self.max_hedge_ratio_stability_max_abs_change is not None,
                self.min_cointegration_stability_pass_ratio is not None,
            )
        ):
            raise ValueError("at least one weak-assumption rule must be enabled")
        if self.cointegration_alpha is not None:
            _validate_probability(self.cointegration_alpha, label="cointegration_alpha")
            if self.p_value_warning_margin is None:
                raise ValueError("p_value_warning_margin is required with cointegration_alpha")
        if self.p_value_warning_margin is not None:
            if self.p_value_warning_margin < 0.0 or not isfinite(self.p_value_warning_margin):
                raise ValueError("p_value_warning_margin must be finite and non-negative")
            if self.cointegration_alpha is None:
                raise ValueError("cointegration_alpha is required with p_value_warning_margin")
        if self.min_half_life_days is not None:
            _validate_positive_float(self.min_half_life_days, label="min_half_life_days")
        if self.max_half_life_days is not None:
            _validate_positive_float(self.max_half_life_days, label="max_half_life_days")
        if (
            self.min_half_life_days is not None
            and self.max_half_life_days is not None
            and self.min_half_life_days > self.max_half_life_days
        ):
            raise ValueError("min_half_life_days must be less than or equal to max_half_life_days")
        if self.min_hedge_ratio_r_squared is not None:
            _validate_probability(
                self.min_hedge_ratio_r_squared,
                label="min_hedge_ratio_r_squared",
            )
        if self.min_ljung_box_p_value is not None:
            _validate_probability(self.min_ljung_box_p_value, label="min_ljung_box_p_value")
        if self.min_jarque_bera_p_value is not None:
            _validate_probability(self.min_jarque_bera_p_value, label="min_jarque_bera_p_value")
        if self.max_abs_excess_kurtosis is not None:
            _validate_non_negative_float(
                self.max_abs_excess_kurtosis,
                label="max_abs_excess_kurtosis",
            )
        if self.max_hedge_ratio_stability_std is not None:
            _validate_non_negative_float(
                self.max_hedge_ratio_stability_std,
                label="max_hedge_ratio_stability_std",
            )
        if self.max_hedge_ratio_stability_max_abs_change is not None:
            _validate_non_negative_float(
                self.max_hedge_ratio_stability_max_abs_change,
                label="max_hedge_ratio_stability_max_abs_change",
            )
        if self.min_cointegration_stability_pass_ratio is not None:
            _validate_probability(
                self.min_cointegration_stability_pass_ratio,
                label="min_cointegration_stability_pass_ratio",
            )


@dataclass(frozen=True)
class CriticWeakAssumptionEvidence:
    """Evidence required to detect weak statistical assumptions."""

    cointegration_p_value: float
    half_life_days: float
    regime_changes_detected: bool
    hedge_ratio_r_squared: float
    residual_ljung_box_p_value: float | None
    residual_jarque_bera_p_value: float | None
    residual_excess_kurtosis: float | None
    hedge_ratio_stability_std: float | None = None
    hedge_ratio_stability_max_abs_change: float | None = None
    cointegration_stability_pass_ratio: float | None = None

    def __post_init__(self) -> None:
        _validate_probability(self.cointegration_p_value, label="cointegration_p_value")
        _validate_positive_float(self.half_life_days, label="half_life_days")
        if not isinstance(self.regime_changes_detected, bool):
            raise TypeError("regime_changes_detected must be a bool")
        _validate_probability(self.hedge_ratio_r_squared, label="hedge_ratio_r_squared")
        if self.residual_ljung_box_p_value is not None:
            _validate_probability(
                self.residual_ljung_box_p_value,
                label="residual_ljung_box_p_value",
            )
        if self.residual_jarque_bera_p_value is not None:
            _validate_probability(
                self.residual_jarque_bera_p_value,
                label="residual_jarque_bera_p_value",
            )
        if self.residual_excess_kurtosis is not None and not isfinite(
            self.residual_excess_kurtosis
        ):
            raise ValueError("residual_excess_kurtosis must be finite")
        if self.hedge_ratio_stability_std is not None:
            _validate_non_negative_float(
                self.hedge_ratio_stability_std,
                label="hedge_ratio_stability_std",
            )
        if self.hedge_ratio_stability_max_abs_change is not None:
            _validate_non_negative_float(
                self.hedge_ratio_stability_max_abs_change,
                label="hedge_ratio_stability_max_abs_change",
            )
        if self.cointegration_stability_pass_ratio is not None:
            _validate_probability(
                self.cointegration_stability_pass_ratio,
                label="cointegration_stability_pass_ratio",
            )


@dataclass(frozen=True)
class CriticWeakAssumptionAssessment:
    """Result of weak-assumption detection."""

    weak_assumptions_detected: bool
    indicators: tuple[str, ...]
    checked_rules: tuple[str, ...]


@dataclass(frozen=True)
class CriticInsufficientTestingPolicy:
    """Explicit policy contract for insufficient-testing detection."""

    min_walk_forward_windows: int | None
    min_test_period_days: float | None
    required_sensitivity_scenarios: tuple[str, ...]

    def __post_init__(self) -> None:
        if not any(
            (
                self.min_walk_forward_windows is not None,
                self.min_test_period_days is not None,
                bool(self.required_sensitivity_scenarios),
            )
        ):
            raise ValueError("at least one insufficient-testing rule must be enabled")
        if self.min_walk_forward_windows is not None:
            if isinstance(self.min_walk_forward_windows, bool) or not isinstance(
                self.min_walk_forward_windows,
                int,
            ):
                raise TypeError("min_walk_forward_windows must be an integer")
            if self.min_walk_forward_windows <= 0:
                raise ValueError("min_walk_forward_windows must be positive")
        if self.min_test_period_days is not None:
            _validate_positive_float(self.min_test_period_days, label="min_test_period_days")
        _validate_sensitivity_scenario_names(self.required_sensitivity_scenarios)


@dataclass(frozen=True)
class CriticInsufficientTestingEvidence:
    """Evidence required to detect insufficient strategy validation."""

    walk_forward_window_count: int
    test_period_days: float
    sensitivity_scenarios: tuple[str, ...]

    def __post_init__(self) -> None:
        if isinstance(self.walk_forward_window_count, bool) or not isinstance(
            self.walk_forward_window_count,
            int,
        ):
            raise TypeError("walk_forward_window_count must be an integer")
        if self.walk_forward_window_count < 0:
            raise ValueError("walk_forward_window_count must be non-negative")
        _validate_positive_float(self.test_period_days, label="test_period_days")
        _validate_sensitivity_scenario_names(self.sensitivity_scenarios)


@dataclass(frozen=True)
class CriticInsufficientTestingAssessment:
    """Result of insufficient-testing detection."""

    insufficient_testing_detected: bool
    indicators: tuple[str, ...]
    checked_rules: tuple[str, ...]


@dataclass(frozen=True)
class CriticCostRealismPolicy:
    """Explicit policy contract for cost-realism detection."""

    flag_negative_net_pnl: bool
    max_turnover: float | None
    max_slippage_rate_to_snapshot_ratio: float | None
    allowed_cost_snapshot_statuses: tuple[str, ...]

    def __post_init__(self) -> None:
        if not any(
            (
                self.flag_negative_net_pnl,
                self.max_turnover is not None,
                self.max_slippage_rate_to_snapshot_ratio is not None,
                bool(self.allowed_cost_snapshot_statuses),
            )
        ):
            raise ValueError("at least one cost-realism rule must be enabled")
        if not isinstance(self.flag_negative_net_pnl, bool):
            raise TypeError("flag_negative_net_pnl must be a bool")
        if self.max_turnover is not None:
            _validate_positive_float(self.max_turnover, label="max_turnover")
        if self.max_slippage_rate_to_snapshot_ratio is not None:
            _validate_positive_float(
                self.max_slippage_rate_to_snapshot_ratio,
                label="max_slippage_rate_to_snapshot_ratio",
            )
            if not self.allowed_cost_snapshot_statuses:
                raise ValueError(
                    "allowed_cost_snapshot_statuses is required with slippage realism"
                )
        _validate_status_names(self.allowed_cost_snapshot_statuses)


@dataclass(frozen=True)
class CriticCostRealismEvidence:
    """Evidence required to detect unrealistic cost assumptions."""

    gross_pnl: float
    net_pnl: float
    turnover: float
    assumed_slippage_rate: float
    snapshot_slippage_rate: float
    cost_snapshot_status: str
    cost_snapshot_source: str

    def __post_init__(self) -> None:
        for label, value in (
            ("gross_pnl", self.gross_pnl),
            ("net_pnl", self.net_pnl),
        ):
            if not isfinite(value):
                raise ValueError(f"{label} must be finite")
        _validate_non_negative_float(self.turnover, label="turnover")
        _validate_non_negative_float(
            self.assumed_slippage_rate,
            label="assumed_slippage_rate",
        )
        _validate_non_negative_float(
            self.snapshot_slippage_rate,
            label="snapshot_slippage_rate",
        )
        _validate_status_names((self.cost_snapshot_status,))
        if not isinstance(self.cost_snapshot_source, str) or not self.cost_snapshot_source.strip():
            raise ValueError("cost_snapshot_source is required")


@dataclass(frozen=True)
class CriticCostRealismAssessment:
    """Result of cost-realism detection."""

    cost_realism_concerns_detected: bool
    indicators: tuple[str, ...]
    checked_rules: tuple[str, ...]


class CriticDecisionStatus(StrEnum):
    """Final Critic review decision status."""

    APPROVED = "approved"
    REJECTED = "rejected"
    QUARANTINED = "quarantined"


@dataclass(frozen=True)
class CriticDecisionPolicy:
    """Explicit policy contract for Critic decision routing."""

    reject_issue_prefixes: tuple[str, ...]
    quarantine_issue_prefixes: tuple[str, ...]
    approve_when_no_issues: bool

    def __post_init__(self) -> None:
        if not any(
            (
                bool(self.reject_issue_prefixes),
                bool(self.quarantine_issue_prefixes),
                self.approve_when_no_issues,
            )
        ):
            raise ValueError("at least one critic decision rule must be enabled")
        if not isinstance(self.approve_when_no_issues, bool):
            raise TypeError("approve_when_no_issues must be a bool")
        _validate_issue_prefixes(self.reject_issue_prefixes, label="reject_issue_prefixes")
        _validate_issue_prefixes(
            self.quarantine_issue_prefixes,
            label="quarantine_issue_prefixes",
        )


@dataclass(frozen=True)
class CriticDecisionEvidence:
    """Aggregated Critic indicators used for final decision routing."""

    lookahead_issues: tuple[str, ...]
    overfitting_indicators: tuple[str, ...]
    weak_assumption_indicators: tuple[str, ...]
    insufficient_testing_indicators: tuple[str, ...]
    cost_realism_indicators: tuple[str, ...]
    operational_concerns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for label, values in (
            ("lookahead_issues", self.lookahead_issues),
            ("overfitting_indicators", self.overfitting_indicators),
            ("weak_assumption_indicators", self.weak_assumption_indicators),
            ("insufficient_testing_indicators", self.insufficient_testing_indicators),
            ("cost_realism_indicators", self.cost_realism_indicators),
            ("operational_concerns", self.operational_concerns),
        ):
            _validate_indicator_texts(values, label=label)

    @property
    def all_indicators(self) -> tuple[str, ...]:
        """Return all indicators in stable review order."""
        return (
            *self.lookahead_issues,
            *self.overfitting_indicators,
            *self.weak_assumption_indicators,
            *self.insufficient_testing_indicators,
            *self.cost_realism_indicators,
            *self.operational_concerns,
        )


@dataclass(frozen=True)
class CriticDecisionAssessment:
    """Final Critic decision result."""

    status: CriticDecisionStatus
    recommendation: str
    objections: tuple[str, ...]


@dataclass(frozen=True)
class CriticAgentInput:
    """Input contract for persisting one completed Critic review."""

    backtest_id: UUID
    lookahead: CriticLookaheadAssessment
    overfitting: CriticOverfittingAssessment
    weak_assumptions: CriticWeakAssumptionAssessment
    insufficient_testing: CriticInsufficientTestingAssessment
    cost_realism: CriticCostRealismAssessment
    decision: CriticDecisionAssessment
    operational_concerns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_indicator_texts(self.operational_concerns, label="operational_concerns")


@dataclass(frozen=True)
class CriticAgentRunResult:
    """Result of a registry-backed Critic Agent persistence step."""

    stored_review: StoredCriticReview
    memory_written: bool


def detect_lookahead_bias(
    evidence: CriticLookaheadEvidence,
    *,
    policy: CriticLookaheadPolicy,
) -> CriticLookaheadAssessment:
    """Detect lookahead bias from explicit decision/data evidence."""
    issues: list[str] = []
    checked_rules: list[str] = []

    if policy.require_strictly_past_signals:
        checked_rules.append("strictly_past_signals")
        issues.extend(
            _future_data_issues(
                evidence.signal_decision_indices,
                evidence.signal_data_through_indices,
                issue_prefix="signal_lookahead",
            )
        )

    if policy.require_strictly_past_position_sizing:
        checked_rules.append("strictly_past_position_sizing")
        issues.extend(
            _future_data_issues(
                evidence.position_decision_indices,
                evidence.position_data_through_indices,
                issue_prefix="position_sizing_lookahead",
            )
        )

    if policy.require_valid_walk_forward_windows:
        checked_rules.append("valid_walk_forward_windows")
        try:
            assert_no_lookahead(evidence.walk_forward_windows)
        except ValueError as exc:
            issues.append(f"walk_forward_lookahead: {exc}")

    return CriticLookaheadAssessment(
        lookahead_bias_detected=bool(issues),
        issues=tuple(issues),
        checked_rules=tuple(checked_rules),
    )


def detect_overfitting(
    evidence: CriticOverfittingEvidence,
    *,
    policy: CriticOverfittingPolicy,
) -> CriticOverfittingAssessment:
    """Detect overfitting indicators from explicit performance evidence."""
    indicators: list[str] = []
    checked_rules: list[str] = []

    if policy.max_sharpe_degradation is not None:
        checked_rules.append("sharpe_degradation")
        degradation = evidence.in_sample_sharpe - evidence.out_of_sample_sharpe
        if degradation > policy.max_sharpe_degradation:
            indicators.append(
                "sharpe_degradation: "
                f"in-sample Sharpe {evidence.in_sample_sharpe:.4f} vs "
                f"out-of-sample Sharpe {evidence.out_of_sample_sharpe:.4f} "
                f"exceeds {policy.max_sharpe_degradation:.4f}"
            )

    if policy.max_parameter_to_data_ratio is not None:
        checked_rules.append("parameter_to_data_ratio")
        ratio = evidence.parameter_count / evidence.data_point_count
        if ratio > policy.max_parameter_to_data_ratio:
            indicators.append(
                "parameter_to_data_ratio: "
                f"{evidence.parameter_count} parameters / {evidence.data_point_count} "
                f"data points = {ratio:.6f} exceeds {policy.max_parameter_to_data_ratio:.6f}"
            )

    if policy.near_perfect_in_sample_sharpe is not None:
        checked_rules.append("near_perfect_in_sample")
        trade_count = evidence.in_sample_trade_count
        assert policy.near_perfect_min_trades is not None
        if (
            trade_count is not None
            and trade_count >= policy.near_perfect_min_trades
            and evidence.in_sample_sharpe >= policy.near_perfect_in_sample_sharpe
        ):
            indicators.append(
                "near_perfect_in_sample: "
                f"in-sample Sharpe {evidence.in_sample_sharpe:.4f} with {trade_count} "
                f"trades reaches suspicious threshold {policy.near_perfect_in_sample_sharpe:.4f}"
            )

    return CriticOverfittingAssessment(
        overfitting_detected=bool(indicators),
        indicators=tuple(indicators),
        checked_rules=tuple(checked_rules),
    )


def detect_weak_assumptions(
    evidence: CriticWeakAssumptionEvidence,
    *,
    policy: CriticWeakAssumptionPolicy,
) -> CriticWeakAssumptionAssessment:
    """Detect weak statistical assumptions from explicit test evidence."""
    indicators: list[str] = []
    checked_rules: list[str] = []

    if policy.cointegration_alpha is not None and policy.p_value_warning_margin is not None:
        checked_rules.append("cointegration_p_value_proximity")
        distance = policy.cointegration_alpha - evidence.cointegration_p_value
        if 0.0 <= distance <= policy.p_value_warning_margin:
            indicators.append(
                "cointegration_p_value_proximity: "
                f"p-value {evidence.cointegration_p_value:.6f} is within "
                f"{policy.p_value_warning_margin:.6f} of alpha {policy.cointegration_alpha:.6f}"
            )

    if policy.min_half_life_days is not None or policy.max_half_life_days is not None:
        checked_rules.append("half_life_bounds")
        min_bound = policy.min_half_life_days
        max_bound = policy.max_half_life_days
        below_min = min_bound is not None and evidence.half_life_days < min_bound
        above_max = max_bound is not None and evidence.half_life_days > max_bound
        if below_min or above_max:
            indicators.append(_half_life_indicator(evidence.half_life_days, min_bound, max_bound))

    if policy.flag_unaddressed_regime_changes:
        checked_rules.append("unaddressed_regime_changes")
        if evidence.regime_changes_detected:
            indicators.append("unaddressed_regime_change: statistical test detected a regime change")

    if policy.min_hedge_ratio_r_squared is not None:
        checked_rules.append("hedge_ratio_r_squared")
        if evidence.hedge_ratio_r_squared < policy.min_hedge_ratio_r_squared:
            indicators.append(
                "hedge_ratio_r_squared: "
                f"R2 {evidence.hedge_ratio_r_squared:.6f} is below required "
                f"{policy.min_hedge_ratio_r_squared:.6f}"
            )

    if policy.min_ljung_box_p_value is not None:
        checked_rules.append("residual_autocorrelation")
        if evidence.residual_ljung_box_p_value is None:
            indicators.append("residual_autocorrelation: Ljung-Box p-value is missing")
        elif evidence.residual_ljung_box_p_value < policy.min_ljung_box_p_value:
            indicators.append(
                "residual_autocorrelation: "
                f"Ljung-Box p-value {evidence.residual_ljung_box_p_value:.6f} "
                f"is below required {policy.min_ljung_box_p_value:.6f}"
            )

    if policy.min_jarque_bera_p_value is not None:
        checked_rules.append("residual_normality")
        if evidence.residual_jarque_bera_p_value is None:
            indicators.append("residual_normality: Jarque-Bera p-value is missing")
        elif evidence.residual_jarque_bera_p_value < policy.min_jarque_bera_p_value:
            indicators.append(
                "residual_normality: "
                f"Jarque-Bera p-value {evidence.residual_jarque_bera_p_value:.6f} "
                f"is below required {policy.min_jarque_bera_p_value:.6f}"
            )

    if policy.max_abs_excess_kurtosis is not None:
        checked_rules.append("residual_excess_kurtosis")
        if evidence.residual_excess_kurtosis is None:
            indicators.append("residual_excess_kurtosis: excess kurtosis is missing")
        elif abs(evidence.residual_excess_kurtosis) > policy.max_abs_excess_kurtosis:
            indicators.append(
                "residual_excess_kurtosis: "
                f"absolute excess kurtosis {abs(evidence.residual_excess_kurtosis):.6f} "
                f"exceeds {policy.max_abs_excess_kurtosis:.6f}"
            )

    if policy.max_hedge_ratio_stability_std is not None:
        checked_rules.append("hedge_ratio_stability_std")
        if evidence.hedge_ratio_stability_std is None:
            indicators.append("hedge_ratio_stability_std: rolling hedge-ratio std is missing")
        elif evidence.hedge_ratio_stability_std > policy.max_hedge_ratio_stability_std:
            indicators.append(
                "hedge_ratio_stability_std: "
                f"rolling hedge-ratio std {evidence.hedge_ratio_stability_std:.6f} "
                f"exceeds {policy.max_hedge_ratio_stability_std:.6f}"
            )

    if policy.max_hedge_ratio_stability_max_abs_change is not None:
        checked_rules.append("hedge_ratio_stability_max_abs_change")
        if evidence.hedge_ratio_stability_max_abs_change is None:
            indicators.append(
                "hedge_ratio_stability_max_abs_change: rolling hedge-ratio max change is missing"
            )
        elif (
            evidence.hedge_ratio_stability_max_abs_change
            > policy.max_hedge_ratio_stability_max_abs_change
        ):
            indicators.append(
                "hedge_ratio_stability_max_abs_change: "
                "rolling hedge-ratio max change "
                f"{evidence.hedge_ratio_stability_max_abs_change:.6f} "
                f"exceeds {policy.max_hedge_ratio_stability_max_abs_change:.6f}"
            )

    if policy.min_cointegration_stability_pass_ratio is not None:
        checked_rules.append("cointegration_stability_pass_ratio")
        if evidence.cointegration_stability_pass_ratio is None:
            indicators.append(
                "cointegration_stability_pass_ratio: rolling cointegration pass ratio is missing"
            )
        elif (
            evidence.cointegration_stability_pass_ratio
            < policy.min_cointegration_stability_pass_ratio
        ):
            indicators.append(
                "cointegration_stability_pass_ratio: "
                f"rolling pass ratio {evidence.cointegration_stability_pass_ratio:.6f} "
                f"is below required {policy.min_cointegration_stability_pass_ratio:.6f}"
            )

    return CriticWeakAssumptionAssessment(
        weak_assumptions_detected=bool(indicators),
        indicators=tuple(indicators),
        checked_rules=tuple(checked_rules),
    )


def detect_insufficient_testing(
    evidence: CriticInsufficientTestingEvidence,
    *,
    policy: CriticInsufficientTestingPolicy,
) -> CriticInsufficientTestingAssessment:
    """Detect insufficient validation coverage from explicit test evidence."""
    indicators: list[str] = []
    checked_rules: list[str] = []

    if policy.min_walk_forward_windows is not None:
        checked_rules.append("minimum_walk_forward_windows")
        if evidence.walk_forward_window_count < policy.min_walk_forward_windows:
            indicators.append(
                "minimum_walk_forward_windows: "
                f"{evidence.walk_forward_window_count} windows is below required "
                f"{policy.min_walk_forward_windows}"
            )

    if policy.min_test_period_days is not None:
        checked_rules.append("minimum_test_period_length")
        if evidence.test_period_days < policy.min_test_period_days:
            indicators.append(
                "minimum_test_period_length: "
                f"{evidence.test_period_days:.4f} days is below required "
                f"{policy.min_test_period_days:.4f}"
            )

    if policy.required_sensitivity_scenarios:
        checked_rules.append("required_sensitivity_analysis")
        observed = set(_normalized_sensitivity_scenarios(evidence.sensitivity_scenarios))
        missing = tuple(
            scenario
            for scenario in _normalized_sensitivity_scenarios(policy.required_sensitivity_scenarios)
            if scenario not in observed
        )
        if missing:
            indicators.append(
                "required_sensitivity_analysis: missing scenarios " + ", ".join(missing)
            )

    return CriticInsufficientTestingAssessment(
        insufficient_testing_detected=bool(indicators),
        indicators=tuple(indicators),
        checked_rules=tuple(checked_rules),
    )


def detect_cost_realism(
    evidence: CriticCostRealismEvidence,
    *,
    policy: CriticCostRealismPolicy,
) -> CriticCostRealismAssessment:
    """Detect cost-realism concerns from explicit cost evidence."""
    indicators: list[str] = []
    checked_rules: list[str] = []

    if policy.flag_negative_net_pnl:
        checked_rules.append("negative_net_pnl_after_costs")
        if evidence.net_pnl < 0.0:
            indicators.append(
                "negative_net_pnl_after_costs: "
                f"net PnL {evidence.net_pnl:.4f} is below 0.0000 after costs"
            )

    if policy.max_turnover is not None:
        checked_rules.append("excessive_turnover")
        if evidence.turnover > policy.max_turnover:
            indicators.append(
                "excessive_turnover: "
                f"turnover {evidence.turnover:.4f} exceeds policy maximum "
                f"{policy.max_turnover:.4f}"
            )

    if policy.allowed_cost_snapshot_statuses:
        checked_rules.append("verified_cost_snapshot")
        allowed_statuses = _normalized_statuses(policy.allowed_cost_snapshot_statuses)
        status = _normalized_status(evidence.cost_snapshot_status)
        if status not in allowed_statuses:
            indicators.append(
                "verified_cost_snapshot: "
                f"status {status} is not allowed; allowed statuses are "
                + ", ".join(allowed_statuses)
            )

    if policy.max_slippage_rate_to_snapshot_ratio is not None:
        checked_rules.append("slippage_assumption_realism")
        ratio = _slippage_difference_ratio(
            evidence.assumed_slippage_rate,
            evidence.snapshot_slippage_rate,
        )
        if ratio > policy.max_slippage_rate_to_snapshot_ratio:
            indicators.append(
                "slippage_assumption_realism: "
                f"assumed slippage {evidence.assumed_slippage_rate:.6f} differs from "
                f"snapshot {evidence.snapshot_slippage_rate:.6f} by ratio {ratio:.4f}, "
                f"above allowed {policy.max_slippage_rate_to_snapshot_ratio:.4f}"
            )

    return CriticCostRealismAssessment(
        cost_realism_concerns_detected=bool(indicators),
        indicators=tuple(indicators),
        checked_rules=tuple(checked_rules),
    )


def decide_critic_review(
    evidence: CriticDecisionEvidence,
    *,
    policy: CriticDecisionPolicy,
) -> CriticDecisionAssessment:
    """Route Critic indicators into an explicit review decision."""
    indicators = evidence.all_indicators
    reject_objections = tuple(
        indicator
        for indicator in indicators
        if _matches_any_prefix(indicator, policy.reject_issue_prefixes)
    )
    if reject_objections:
        return CriticDecisionAssessment(
            status=CriticDecisionStatus.REJECTED,
            recommendation="Reject",
            objections=reject_objections,
        )

    quarantine_objections = tuple(
        indicator
        for indicator in indicators
        if _matches_any_prefix(indicator, policy.quarantine_issue_prefixes)
    )
    if quarantine_objections:
        return CriticDecisionAssessment(
            status=CriticDecisionStatus.QUARANTINED,
            recommendation="Quarantine",
            objections=quarantine_objections,
        )

    if not indicators and policy.approve_when_no_issues:
        return CriticDecisionAssessment(
            status=CriticDecisionStatus.APPROVED,
            recommendation="Approve",
            objections=(),
        )

    return CriticDecisionAssessment(
        status=CriticDecisionStatus.QUARANTINED,
        recommendation="Quarantine",
        objections=indicators,
    )


def run_critic_agent_persistence(
    request: CriticAgentInput,
    *,
    session: Session,
    memory_service: MemoryWriter | None = None,
) -> CriticAgentRunResult:
    """Persist structured Critic review results and write a concise memory summary."""
    _require_backtest_result(session, backtest_id=request.backtest_id)
    stored = _persist_critic_review(session, request)
    memory_written = False
    if memory_service is not None:
        memory_service.write(_memory_request_for(stored))
        memory_written = True
    return CriticAgentRunResult(stored_review=stored, memory_written=memory_written)


def _persist_critic_review(
    session: Session,
    request: CriticAgentInput,
) -> StoredCriticReview:
    stored = StoredCriticReview(
        backtest_id=str(request.backtest_id),
        lookahead_bias_detected=request.lookahead.lookahead_bias_detected,
        overfitting_indicators=list(request.overfitting.indicators),
        weak_assumptions=list(request.weak_assumptions.indicators),
        insufficient_testing=list(request.insufficient_testing.indicators),
        cost_concerns=list(request.cost_realism.indicators),
        operational_concerns=list(request.operational_concerns),
        status=request.decision.status.value,
        recommendation=request.decision.recommendation,
        objections="\n".join(request.decision.objections) if request.decision.objections else "None",
    )
    session.add(stored)
    session.flush()
    return stored


def _memory_request_for(review: StoredCriticReview) -> MemoryWriteRequest:
    return MemoryWriteRequest(
        record_type=MemoryRecordType.CRITIC_REVIEW,
        title="Critic review completed",
        body=(
            "Critic review completed. Structured objections, review status, and "
            "recommendation are stored in the registry."
        ),
        source_id=review.review_id,
        registry_reference=f"registry:critic_reviews/{review.review_id}",
        tags=["critic", "review", review.status],
        metadata={
            "backtest_id": review.backtest_id,
            "status": review.status,
        },
    )


def _require_backtest_result(session: Session, *, backtest_id: UUID) -> None:
    result = (
        session.query(StoredBacktestResult)
        .filter(StoredBacktestResult.backtest_id == str(backtest_id))
        .first()
    )
    if result is None:
        raise ValueError(f"backtest result is required for critic review {backtest_id}")


def _validate_index_pairs(
    decision_indices: tuple[int, ...],
    data_through_indices: tuple[int, ...],
    *,
    label: str,
) -> None:
    if len(decision_indices) != len(data_through_indices):
        raise ValueError(f"{label} evidence lengths must match")
    for value in (*decision_indices, *data_through_indices):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{label} evidence indices must be integers")
        if value < 0:
            raise ValueError(f"{label} evidence indices must be non-negative")


def _future_data_issues(
    decision_indices: tuple[int, ...],
    data_through_indices: tuple[int, ...],
    *,
    issue_prefix: str,
) -> tuple[str, ...]:
    issues: list[str] = []
    for decision_index, data_through_index in zip(
        decision_indices,
        data_through_indices,
        strict=True,
    ):
        if data_through_index >= decision_index:
            issues.append(
                f"{issue_prefix}: decision index {decision_index} "
                f"uses data through index {data_through_index}"
            )
    return tuple(issues)


def _validate_probability(value: float, *, label: str) -> None:
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be finite and between 0 and 1")


def _validate_positive_float(value: float, *, label: str) -> None:
    if not isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be finite and positive")


def _validate_non_negative_float(value: float, *, label: str) -> None:
    if not isfinite(value) or value < 0.0:
        raise ValueError(f"{label} must be finite and non-negative")


def _validate_sensitivity_scenario_names(scenarios: tuple[str, ...]) -> None:
    for scenario in scenarios:
        if not isinstance(scenario, str) or not scenario.strip():
            raise ValueError("sensitivity scenario names must be non-empty strings")


def _validate_status_names(statuses: tuple[str, ...]) -> None:
    for status in statuses:
        if not isinstance(status, str) or not status.strip():
            raise ValueError("cost snapshot statuses must be non-empty strings")


def _validate_issue_prefixes(prefixes: tuple[str, ...], *, label: str) -> None:
    for prefix in prefixes:
        if not isinstance(prefix, str) or not prefix.strip():
            raise ValueError(f"{label} must contain non-empty strings")


def _validate_indicator_texts(indicators: tuple[str, ...], *, label: str) -> None:
    for indicator in indicators:
        if not isinstance(indicator, str) or not indicator.strip():
            raise ValueError(f"{label} must contain non-empty strings")


def _normalized_sensitivity_scenarios(scenarios: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(scenario.strip().lower() for scenario in scenarios))


def _normalized_statuses(statuses: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_normalized_status(status) for status in statuses))


def _normalized_status(status: str) -> str:
    return status.strip().lower()


def _matches_any_prefix(indicator: str, prefixes: tuple[str, ...]) -> bool:
    normalized = indicator.strip().lower()
    return any(normalized.startswith(prefix.strip().lower()) for prefix in prefixes)


def _slippage_difference_ratio(assumed_rate: float, snapshot_rate: float) -> float:
    if assumed_rate == snapshot_rate:
        return 1.0
    if assumed_rate == 0.0 or snapshot_rate == 0.0:
        return float("inf")
    return max(assumed_rate, snapshot_rate) / min(assumed_rate, snapshot_rate)


def _half_life_indicator(
    half_life_days: float,
    min_bound: float | None,
    max_bound: float | None,
) -> str:
    if min_bound is not None and max_bound is not None:
        return (
            "half_life_bounds: "
            f"half-life {half_life_days:.4f} days is outside "
            f"[{min_bound:.4f}, {max_bound:.4f}]"
        )
    if min_bound is not None:
        return (
            "half_life_bounds: "
            f"half-life {half_life_days:.4f} days is below minimum {min_bound:.4f}"
        )
    if max_bound is not None:
        return (
            "half_life_bounds: "
            f"half-life {half_life_days:.4f} days is above maximum {max_bound:.4f}"
        )
    raise AssertionError("half-life bounds indicator requires at least one bound")
