"""Unit tests for Critic Agent lookahead-bias detection."""

import pytest

from stat_arb.agents import (
    CriticLookaheadEvidence,
    CriticLookaheadPolicy,
    detect_lookahead_bias,
)
from stat_arb.statistical import IndexWindow, WalkForwardWindow


def test_critic_lookahead_detection_accepts_strictly_past_evidence() -> None:
    """Clean evidence should produce an explicit no-bias assessment."""
    assessment = detect_lookahead_bias(
        CriticLookaheadEvidence(
            signal_decision_indices=(10, 11, 12),
            signal_data_through_indices=(9, 10, 11),
            position_decision_indices=(10, 11, 12),
            position_data_through_indices=(9, 10, 11),
            walk_forward_windows=(
                WalkForwardWindow(
                    fold=0,
                    train=IndexWindow(start=0, end=10),
                    test=IndexWindow(start=10, end=15),
                ),
                WalkForwardWindow(
                    fold=1,
                    train=IndexWindow(start=5, end=15),
                    test=IndexWindow(start=15, end=20),
                ),
            ),
        ),
        policy=CriticLookaheadPolicy(
            require_strictly_past_signals=True,
            require_strictly_past_position_sizing=True,
            require_valid_walk_forward_windows=True,
        ),
    )

    assert assessment.lookahead_bias_detected is False
    assert assessment.issues == ()
    assert assessment.checked_rules == (
        "strictly_past_signals",
        "strictly_past_position_sizing",
        "valid_walk_forward_windows",
    )


def test_critic_lookahead_detection_flags_signal_future_data() -> None:
    """Signals that use current/future information should be flagged."""
    assessment = detect_lookahead_bias(
        CriticLookaheadEvidence(
            signal_decision_indices=(10, 11),
            signal_data_through_indices=(9, 11),
            position_decision_indices=(10, 11),
            position_data_through_indices=(9, 10),
            walk_forward_windows=(
                WalkForwardWindow(
                    fold=0,
                    train=IndexWindow(start=0, end=10),
                    test=IndexWindow(start=10, end=15),
                ),
            ),
        ),
        policy=CriticLookaheadPolicy(
            require_strictly_past_signals=True,
            require_strictly_past_position_sizing=True,
            require_valid_walk_forward_windows=True,
        ),
    )

    assert assessment.lookahead_bias_detected is True
    assert assessment.issues == (
        "signal_lookahead: decision index 11 uses data through index 11",
    )


def test_critic_lookahead_detection_flags_position_sizing_future_data() -> None:
    """Position sizing should not use information from the decision bar or later."""
    assessment = detect_lookahead_bias(
        CriticLookaheadEvidence(
            signal_decision_indices=(10,),
            signal_data_through_indices=(9,),
            position_decision_indices=(10,),
            position_data_through_indices=(10,),
            walk_forward_windows=(
                WalkForwardWindow(
                    fold=0,
                    train=IndexWindow(start=0, end=10),
                    test=IndexWindow(start=10, end=15),
                ),
            ),
        ),
        policy=CriticLookaheadPolicy(
            require_strictly_past_signals=True,
            require_strictly_past_position_sizing=True,
            require_valid_walk_forward_windows=True,
        ),
    )

    assert assessment.lookahead_bias_detected is True
    assert assessment.issues == (
        "position_sizing_lookahead: decision index 10 uses data through index 10",
    )


def test_critic_lookahead_detection_flags_invalid_walk_forward_windows() -> None:
    """Overlapping train/test windows should be flagged by Critic evidence review."""
    assessment = detect_lookahead_bias(
        CriticLookaheadEvidence(
            signal_decision_indices=(10,),
            signal_data_through_indices=(9,),
            position_decision_indices=(10,),
            position_data_through_indices=(9,),
            walk_forward_windows=(
                WalkForwardWindow(
                    fold=0,
                    train=IndexWindow(start=0, end=11),
                    test=IndexWindow(start=10, end=15),
                ),
            ),
        ),
        policy=CriticLookaheadPolicy(
            require_strictly_past_signals=True,
            require_strictly_past_position_sizing=True,
            require_valid_walk_forward_windows=True,
        ),
    )

    assert assessment.lookahead_bias_detected is True
    assert assessment.issues == (
        "walk_forward_lookahead: train window must not overlap or follow test window",
    )


def test_critic_lookahead_policy_must_enable_at_least_one_rule() -> None:
    """A policy with no enabled rules would be a hidden no-op."""
    with pytest.raises(ValueError, match="at least one"):
        CriticLookaheadPolicy(
            require_strictly_past_signals=False,
            require_strictly_past_position_sizing=False,
            require_valid_walk_forward_windows=False,
        )


def test_critic_lookahead_evidence_requires_matching_lengths() -> None:
    """Decision indices and data-through indices must be paired explicitly."""
    with pytest.raises(ValueError, match="signal evidence lengths"):
        CriticLookaheadEvidence(
            signal_decision_indices=(10, 11),
            signal_data_through_indices=(9,),
            position_decision_indices=(10,),
            position_data_through_indices=(9,),
            walk_forward_windows=(
                WalkForwardWindow(
                    fold=0,
                    train=IndexWindow(start=0, end=10),
                    test=IndexWindow(start=10, end=15),
                ),
            ),
        )
