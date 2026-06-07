"""Unit tests for Critic Agent lookahead-bias detection."""

import pytest

from stat_arb.agents import (
    CriticLookaheadEvidence,
    CriticLookaheadPolicy,
    CriticOverfittingEvidence,
    CriticOverfittingPolicy,
    CriticWeakAssumptionEvidence,
    CriticWeakAssumptionPolicy,
    detect_lookahead_bias,
    detect_overfitting,
    detect_weak_assumptions,
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


def test_critic_overfitting_detection_accepts_stable_out_of_sample_result() -> None:
    """Stable OOS performance and modest parameterization should not raise indicators."""
    assessment = detect_overfitting(
        CriticOverfittingEvidence(
            in_sample_sharpe=1.2,
            out_of_sample_sharpe=0.9,
            parameter_count=4,
            data_point_count=500,
        ),
        policy=CriticOverfittingPolicy(
            max_sharpe_degradation=0.5,
            max_parameter_to_data_ratio=0.05,
            near_perfect_in_sample_sharpe=5.0,
            near_perfect_min_trades=30,
        ),
    )

    assert assessment.overfitting_detected is False
    assert assessment.indicators == ()
    assert assessment.checked_rules == (
        "sharpe_degradation",
        "parameter_to_data_ratio",
        "near_perfect_in_sample",
    )


def test_critic_overfitting_detection_flags_sharpe_divergence() -> None:
    """Large in-sample vs out-of-sample degradation should be visible."""
    assessment = detect_overfitting(
        CriticOverfittingEvidence(
            in_sample_sharpe=2.4,
            out_of_sample_sharpe=0.7,
            parameter_count=4,
            data_point_count=500,
        ),
        policy=CriticOverfittingPolicy(
            max_sharpe_degradation=0.5,
            max_parameter_to_data_ratio=0.05,
            near_perfect_in_sample_sharpe=5.0,
            near_perfect_min_trades=30,
        ),
    )

    assert assessment.overfitting_detected is True
    assert assessment.indicators == (
        "sharpe_degradation: in-sample Sharpe 2.4000 vs out-of-sample Sharpe 0.7000 exceeds 0.5000",
    )


def test_critic_overfitting_detection_flags_parameter_ratio() -> None:
    """Too many fitted parameters per data point should be reported."""
    assessment = detect_overfitting(
        CriticOverfittingEvidence(
            in_sample_sharpe=1.0,
            out_of_sample_sharpe=0.8,
            parameter_count=30,
            data_point_count=200,
        ),
        policy=CriticOverfittingPolicy(
            max_sharpe_degradation=0.5,
            max_parameter_to_data_ratio=0.05,
            near_perfect_in_sample_sharpe=5.0,
            near_perfect_min_trades=30,
        ),
    )

    assert assessment.overfitting_detected is True
    assert assessment.indicators == (
        "parameter_to_data_ratio: 30 parameters / 200 data points = 0.150000 exceeds 0.050000",
    )


def test_critic_overfitting_detection_flags_near_perfect_in_sample_result() -> None:
    """Near-perfect in-sample Sharpe with enough trades should be suspicious."""
    assessment = detect_overfitting(
        CriticOverfittingEvidence(
            in_sample_sharpe=8.0,
            out_of_sample_sharpe=1.0,
            parameter_count=4,
            data_point_count=500,
            in_sample_trade_count=40,
        ),
        policy=CriticOverfittingPolicy(
            max_sharpe_degradation=10.0,
            max_parameter_to_data_ratio=0.05,
            near_perfect_in_sample_sharpe=5.0,
            near_perfect_min_trades=30,
        ),
    )

    assert assessment.overfitting_detected is True
    assert assessment.indicators == (
        "near_perfect_in_sample: in-sample Sharpe 8.0000 with 40 trades reaches suspicious threshold 5.0000",
    )


def test_critic_overfitting_policy_rejects_hidden_noop_policy() -> None:
    """At least one overfitting rule must be active."""
    with pytest.raises(ValueError, match="at least one"):
        CriticOverfittingPolicy(
            max_sharpe_degradation=None,
            max_parameter_to_data_ratio=None,
            near_perfect_in_sample_sharpe=None,
            near_perfect_min_trades=None,
        )


def test_critic_overfitting_evidence_rejects_invalid_counts() -> None:
    """Parameter and data counts must be explicit positive research inputs."""
    with pytest.raises(ValueError, match="data_point_count"):
        CriticOverfittingEvidence(
            in_sample_sharpe=1.0,
            out_of_sample_sharpe=0.8,
            parameter_count=4,
            data_point_count=0,
        )


def test_critic_weak_assumption_detection_accepts_strong_evidence() -> None:
    """Strong statistical evidence should not produce weak-assumption indicators."""
    assessment = detect_weak_assumptions(
        CriticWeakAssumptionEvidence(
            cointegration_p_value=0.01,
            half_life_days=5.0,
            regime_changes_detected=False,
            hedge_ratio_r_squared=0.82,
        ),
        policy=CriticWeakAssumptionPolicy(
            cointegration_alpha=0.05,
            p_value_warning_margin=0.01,
            min_half_life_days=1.0,
            max_half_life_days=30.0,
            flag_unaddressed_regime_changes=True,
            min_hedge_ratio_r_squared=0.7,
        ),
    )

    assert assessment.weak_assumptions_detected is False
    assert assessment.indicators == ()
    assert assessment.checked_rules == (
        "cointegration_p_value_proximity",
        "half_life_bounds",
        "unaddressed_regime_changes",
        "hedge_ratio_r_squared",
    )


def test_critic_weak_assumption_detection_flags_p_value_proximity() -> None:
    """P-values near the explicit alpha threshold should be visible."""
    assessment = detect_weak_assumptions(
        CriticWeakAssumptionEvidence(
            cointegration_p_value=0.046,
            half_life_days=5.0,
            regime_changes_detected=False,
            hedge_ratio_r_squared=0.82,
        ),
        policy=CriticWeakAssumptionPolicy(
            cointegration_alpha=0.05,
            p_value_warning_margin=0.01,
            min_half_life_days=1.0,
            max_half_life_days=30.0,
            flag_unaddressed_regime_changes=True,
            min_hedge_ratio_r_squared=0.7,
        ),
    )

    assert assessment.weak_assumptions_detected is True
    assert assessment.indicators == (
        "cointegration_p_value_proximity: p-value 0.046000 is within 0.010000 of alpha 0.050000",
    )


def test_critic_weak_assumption_detection_flags_half_life_outside_bounds() -> None:
    """Half-life outside explicit bounds should be reported."""
    assessment = detect_weak_assumptions(
        CriticWeakAssumptionEvidence(
            cointegration_p_value=0.01,
            half_life_days=45.0,
            regime_changes_detected=False,
            hedge_ratio_r_squared=0.82,
        ),
        policy=CriticWeakAssumptionPolicy(
            cointegration_alpha=0.05,
            p_value_warning_margin=0.01,
            min_half_life_days=1.0,
            max_half_life_days=30.0,
            flag_unaddressed_regime_changes=True,
            min_hedge_ratio_r_squared=0.7,
        ),
    )

    assert assessment.weak_assumptions_detected is True
    assert assessment.indicators == (
        "half_life_bounds: half-life 45.0000 days is outside [1.0000, 30.0000]",
    )


def test_critic_weak_assumption_detection_flags_regime_change() -> None:
    """Unaddressed regime changes should be weak-assumption indicators."""
    assessment = detect_weak_assumptions(
        CriticWeakAssumptionEvidence(
            cointegration_p_value=0.01,
            half_life_days=5.0,
            regime_changes_detected=True,
            hedge_ratio_r_squared=0.82,
        ),
        policy=CriticWeakAssumptionPolicy(
            cointegration_alpha=0.05,
            p_value_warning_margin=0.01,
            min_half_life_days=1.0,
            max_half_life_days=30.0,
            flag_unaddressed_regime_changes=True,
            min_hedge_ratio_r_squared=0.7,
        ),
    )

    assert assessment.weak_assumptions_detected is True
    assert assessment.indicators == (
        "unaddressed_regime_change: statistical test detected a regime change",
    )


def test_critic_weak_assumption_detection_flags_low_hedge_ratio_r_squared() -> None:
    """Weak hedge-ratio regression quality should be visible."""
    assessment = detect_weak_assumptions(
        CriticWeakAssumptionEvidence(
            cointegration_p_value=0.01,
            half_life_days=5.0,
            regime_changes_detected=False,
            hedge_ratio_r_squared=0.55,
        ),
        policy=CriticWeakAssumptionPolicy(
            cointegration_alpha=0.05,
            p_value_warning_margin=0.01,
            min_half_life_days=1.0,
            max_half_life_days=30.0,
            flag_unaddressed_regime_changes=True,
            min_hedge_ratio_r_squared=0.7,
        ),
    )

    assert assessment.weak_assumptions_detected is True
    assert assessment.indicators == (
        "hedge_ratio_r_squared: R2 0.550000 is below required 0.700000",
    )


def test_critic_weak_assumption_policy_rejects_hidden_noop_policy() -> None:
    """At least one weak-assumption rule must be active."""
    with pytest.raises(ValueError, match="at least one"):
        CriticWeakAssumptionPolicy(
            cointegration_alpha=None,
            p_value_warning_margin=None,
            min_half_life_days=None,
            max_half_life_days=None,
            flag_unaddressed_regime_changes=False,
            min_hedge_ratio_r_squared=None,
        )


def test_critic_weak_assumption_evidence_rejects_invalid_values() -> None:
    """Weak-assumption evidence should reject invalid p-values and R2 values."""
    with pytest.raises(ValueError, match="cointegration_p_value"):
        CriticWeakAssumptionEvidence(
            cointegration_p_value=1.5,
            half_life_days=5.0,
            regime_changes_detected=False,
            hedge_ratio_r_squared=0.82,
        )
