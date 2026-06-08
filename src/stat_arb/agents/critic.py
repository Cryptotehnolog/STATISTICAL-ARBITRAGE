"""Critic Agent lookahead-bias detection boundary."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from stat_arb.statistical import WalkForwardWindow, assert_no_lookahead


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

    def __post_init__(self) -> None:
        if not any(
            (
                self.cointegration_alpha is not None and self.p_value_warning_margin is not None,
                self.min_half_life_days is not None or self.max_half_life_days is not None,
                self.flag_unaddressed_regime_changes,
                self.min_hedge_ratio_r_squared is not None,
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


@dataclass(frozen=True)
class CriticWeakAssumptionEvidence:
    """Evidence required to detect weak statistical assumptions."""

    cointegration_p_value: float
    half_life_days: float
    regime_changes_detected: bool
    hedge_ratio_r_squared: float

    def __post_init__(self) -> None:
        _validate_probability(self.cointegration_p_value, label="cointegration_p_value")
        _validate_positive_float(self.half_life_days, label="half_life_days")
        if not isinstance(self.regime_changes_detected, bool):
            raise TypeError("regime_changes_detected must be a bool")
        _validate_probability(self.hedge_ratio_r_squared, label="hedge_ratio_r_squared")


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


def _validate_sensitivity_scenario_names(scenarios: tuple[str, ...]) -> None:
    for scenario in scenarios:
        if not isinstance(scenario, str) or not scenario.strip():
            raise ValueError("sensitivity scenario names must be non-empty strings")


def _normalized_sensitivity_scenarios(scenarios: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(scenario.strip().lower() for scenario in scenarios))


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
