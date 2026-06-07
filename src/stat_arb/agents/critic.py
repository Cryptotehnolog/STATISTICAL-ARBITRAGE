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
