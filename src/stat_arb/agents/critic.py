"""Critic Agent lookahead-bias detection boundary."""

from __future__ import annotations

from dataclasses import dataclass

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
