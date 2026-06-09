"""Property tests for backtest core contracts."""

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stat_arb.backtest import run_pair_backtest_core


@pytest.mark.property
@settings(max_examples=100, deadline=None)
@given(
    z_scores=st.lists(
        st.floats(min_value=-4.0, max_value=4.0, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=50,
    ),
    hedge_ratio=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
)
def test_backtest_core_preserves_aligned_observation_count(
    z_scores: list[float],
    hedge_ratio: float,
) -> None:
    """Backtest core should emit exactly one step per aligned observation."""
    count = len(z_scores)
    result = run_pair_backtest_core(
        prices_a=[100.0 + index * 0.01 for index in range(count)],
        prices_b=[100.0 + index * 0.005 for index in range(count)],
        z_scores=z_scores,
        aligned_timestamps=_timestamps(count),
        hedge_ratio=hedge_ratio,
        entry_threshold=2.0,
        exit_threshold=0.5,
        exit_policy=None,
        risk_exit_policy_disabled_reason="unit test uses convergence-only exits",
    )

    assert result.observations == count
    assert len(result.steps) == count
    assert tuple(step.index for step in result.steps) == tuple(range(count))


def _timestamps(count: int) -> tuple[datetime, ...]:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    return tuple(start + timedelta(minutes=15 * index) for index in range(count))
