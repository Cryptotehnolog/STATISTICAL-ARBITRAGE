"""Unit tests for pair backtest PnL and cost attribution."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from stat_arb.backtest import (
    BacktestCostConfig,
    CostAssumptionStatus,
    calculate_pair_pnl,
    run_pair_backtest_core,
)

TASKS_PATH = Path(".kiro/specs/quant-research-architecture/tasks.md")
DOMAIN_MODELS_PATH = Path("src/stat_arb/domain/models.py")
STORAGE_MODELS_PATH = Path("src/stat_arb/storage/models.py")


def test_calculate_pair_pnl_attributes_costs_and_preserves_net_formula() -> None:
    """Net PnL should equal gross PnL minus all attributed costs."""
    core = run_pair_backtest_core(
        prices_a=[100.0, 103.0, 101.0, 100.0],
        prices_b=[100.0, 100.0, 100.0, 100.0],
        z_scores=[2.2, 1.2, 0.2, 0.0],
        aligned_timestamps=[
            datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 15, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 30, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 45, tzinfo=UTC),
        ],
        hedge_ratio=1.0,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )

    result = calculate_pair_pnl(core, cost_config=_verified_cost_config(), periods_per_day=96.0)

    assert result.gross_pnl == pytest.approx(-1.0)
    assert result.traded_value == pytest.approx(401.0)
    assert result.costs.commission_cost == pytest.approx(0.401)
    assert result.costs.spread_cost == pytest.approx(0.2005)
    assert result.costs.slippage_cost == pytest.approx(0.0802)
    assert result.costs.funding_cost > 0.0
    assert result.costs.borrow_cost > 0.0
    assert result.net_pnl + result.costs.total_cost == pytest.approx(result.gross_pnl)
    assert result.num_trades == 2


def test_backtest_cost_config_requires_verified_or_manual_approved_status() -> None:
    """Stale or rejected cost snapshots must not be used for backtests."""
    with pytest.raises(ValueError, match="verified or manually approved"):
        BacktestCostConfig(
            commission_rate=0.001,
            spread_cost_rate=0.0005,
            slippage_rate=0.0002,
            funding_rate_daily=0.0001,
            borrow_rate_annual=0.005,
            status=CostAssumptionStatus.STALE,
            source="unit-test",
            verified_at=datetime(2024, 1, 1, tzinfo=UTC),
            venue="test-exchange",
            market_type="perpetual",
        )


def test_backtest_cost_config_requires_explicit_rates_and_provenance() -> None:
    """There should be no hidden runtime defaults for cost assumptions."""
    with pytest.raises(TypeError):
        BacktestCostConfig(  # type: ignore[call-arg]
            status=CostAssumptionStatus.VERIFIED,
            source="unit-test",
            verified_at=datetime(2024, 1, 1, tzinfo=UTC),
            venue="test-exchange",
            market_type="spot",
        )

    with pytest.raises(ValueError, match="source"):
        BacktestCostConfig(
            commission_rate=0.001,
            spread_cost_rate=0.0005,
            slippage_rate=0.0002,
            funding_rate_daily=0.0,
            borrow_rate_annual=0.0,
            status=CostAssumptionStatus.VERIFIED,
            source="",
            verified_at=datetime(2024, 1, 1, tzinfo=UTC),
            venue="test-exchange",
            market_type="spot",
        )


def test_calculate_pair_pnl_rejects_invalid_periods_per_day() -> None:
    """Holding-period costs need an explicit positive periods-per-day value."""
    core = run_pair_backtest_core(
        prices_a=[100.0, 101.0],
        prices_b=[100.0, 100.0],
        z_scores=[2.1, 0.0],
        aligned_timestamps=[
            datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
            datetime(2024, 1, 1, 0, 15, tzinfo=UTC),
        ],
        hedge_ratio=1.0,
    )

    with pytest.raises(ValueError, match="periods_per_day"):
        calculate_pair_pnl(core, cost_config=_verified_cost_config(), periods_per_day=0.0)


def test_backtest_costs_do_not_expose_legacy_planning_defaults() -> None:
    """Old Kiro planning percentages must not become trusted runtime defaults."""
    tasks = TASKS_PATH.read_text(encoding="utf-8")
    domain_models = DOMAIN_MODELS_PATH.read_text(encoding="utf-8")
    storage_models = STORAGE_MODELS_PATH.read_text(encoding="utf-8")

    for legacy_text in ("0.1% default", "0.05% default", "0.02% default"):
        assert legacy_text not in tasks

    assert "funding_cost: float = Field(default=0.0" not in domain_models
    assert "borrow_cost: float = Field(default=0.0" not in domain_models
    assert "funding_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)" not in storage_models
    assert "borrow_cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)" not in storage_models


@pytest.mark.property
@settings(max_examples=50, deadline=None)
@given(
    prices_a=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=40,
    ),
    prices_b=st.lists(
        st.floats(min_value=1.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=40,
    ),
    z_scores=st.lists(
        st.floats(min_value=-4.0, max_value=4.0, allow_nan=False, allow_infinity=False),
        min_size=3,
        max_size=40,
    ),
    hedge_ratio=st.floats(min_value=0.1, max_value=5.0, allow_nan=False, allow_infinity=False),
    commission_rate=st.floats(min_value=0.0, max_value=0.01, allow_nan=False, allow_infinity=False),
    spread_cost_rate=st.floats(min_value=0.0, max_value=0.01, allow_nan=False, allow_infinity=False),
    slippage_rate=st.floats(min_value=0.0, max_value=0.01, allow_nan=False, allow_infinity=False),
    funding_rate_daily=st.floats(min_value=0.0, max_value=0.01, allow_nan=False, allow_infinity=False),
    borrow_rate_annual=st.floats(min_value=0.0, max_value=0.20, allow_nan=False, allow_infinity=False),
)
def test_pair_pnl_conservation_property(
    prices_a: list[float],
    prices_b: list[float],
    z_scores: list[float],
    hedge_ratio: float,
    commission_rate: float,
    spread_cost_rate: float,
    slippage_rate: float,
    funding_rate_daily: float,
    borrow_rate_annual: float,
) -> None:
    """Property 11: net PnL plus all costs should equal gross PnL."""
    observations = min(len(prices_a), len(prices_b), len(z_scores))
    prices_a = prices_a[:observations]
    prices_b = prices_b[:observations]
    z_scores = z_scores[:observations]
    core = run_pair_backtest_core(
        prices_a=prices_a,
        prices_b=prices_b,
        z_scores=z_scores,
        aligned_timestamps=[
            datetime(2024, 1, 1, tzinfo=UTC) + timedelta(hours=index)
            for index in range(observations)
        ],
        hedge_ratio=hedge_ratio,
        entry_threshold=2.0,
        exit_threshold=0.5,
    )
    cost_config = BacktestCostConfig(
        commission_rate=commission_rate,
        spread_cost_rate=spread_cost_rate,
        slippage_rate=slippage_rate,
        funding_rate_daily=funding_rate_daily,
        borrow_rate_annual=borrow_rate_annual,
        status=CostAssumptionStatus.VERIFIED,
        source="hypothesis-generated explicit test config",
        verified_at=datetime(2024, 1, 1, tzinfo=UTC),
        venue="property-test",
        market_type="synthetic",
    )

    result = calculate_pair_pnl(core, cost_config=cost_config, periods_per_day=24.0)

    assert result.costs.commission_cost >= 0.0
    assert result.costs.spread_cost >= 0.0
    assert result.costs.slippage_cost >= 0.0
    assert result.costs.funding_cost >= 0.0
    assert result.costs.borrow_cost >= 0.0
    assert result.traded_value >= 0.0
    assert result.net_pnl + result.costs.total_cost == pytest.approx(result.gross_pnl)


def _verified_cost_config() -> BacktestCostConfig:
    return BacktestCostConfig(
        commission_rate=0.001,
        spread_cost_rate=0.0005,
        slippage_rate=0.0002,
        funding_rate_daily=0.0001,
        borrow_rate_annual=0.005,
        status=CostAssumptionStatus.VERIFIED,
        source="unit-test explicit assumptions",
        verified_at=datetime(2024, 1, 1, tzinfo=UTC),
        venue="test-exchange",
        market_type="perpetual",
    )
