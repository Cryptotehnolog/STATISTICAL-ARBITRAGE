"""Unit tests for explicit capacity and execution realism scenarios."""

from datetime import UTC, datetime

import pytest

from stat_arb.backtest import (
    BacktestCostConfig,
    CapacityRealismScenario,
    CostAssumptionStatus,
    ExecutionDelayScenario,
    LegRiskScenario,
    LiquidityImpactScenario,
    run_capacity_cost_realism_scenarios,
    run_pair_backtest_core,
)


def test_capacity_cost_realism_scenarios_apply_explicit_liquidity_delay_and_leg_risk() -> None:
    """Realism scenarios should make capacity, liquidity, delay, and leg-risk visible."""
    core = run_pair_backtest_core(
        prices_a=[100.0, 104.0, 102.0, 101.0],
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
        exit_policy=None,
        risk_exit_policy_disabled_reason="unit test uses convergence-only exits",
    )

    result = run_capacity_cost_realism_scenarios(
        core,
        base_cost_config=_verified_cost_config(),
        base_sharpe_ratio=1.8,
        periods_per_day=96.0,
        average_portfolio_value=10_000.0,
        scenarios=(
            CapacityRealismScenario(
                name="capital_100k_delay_and_leg_risk",
                capital_size=100_000.0,
                liquidity=LiquidityImpactScenario(
                    average_daily_quote_volume=1_000_000.0,
                    market_impact_rate=0.0004,
                ),
                execution_delay=ExecutionDelayScenario(
                    delay_bars=2,
                    adverse_return_per_bar=0.0003,
                ),
                leg_risk=LegRiskScenario(
                    unhedged_notional_fraction=0.15,
                    adverse_move_rate=0.001,
                ),
                cost_multiplier=1.5,
            ),
        ),
    )

    scenario = result.scenarios[0]
    assert scenario.scenario.name == "capital_100k_delay_and_leg_risk"
    assert scenario.participation_rate == pytest.approx(0.1)
    assert scenario.market_impact_cost > 0.0
    assert scenario.execution_delay_cost > 0.0
    assert scenario.leg_risk_cost > 0.0
    assert scenario.realism_net_pnl < result.base.net_pnl
    assert scenario.capacity_adjusted_sharpe < result.base_sharpe_ratio
    assert result.worst_capacity_adjusted_sharpe == scenario.capacity_adjusted_sharpe
    assert result.max_participation_rate == pytest.approx(0.1)
    assert result.scenario_names == ("capital_100k_delay_and_leg_risk",)


def test_capacity_cost_realism_requires_explicit_liquidity_evidence_for_impact() -> None:
    """Liquidity-aware impact must not run without explicit market volume evidence."""
    with pytest.raises(ValueError, match="average_daily_quote_volume"):
        LiquidityImpactScenario(
            average_daily_quote_volume=0.0,
            market_impact_rate=0.0004,
        )

    with pytest.raises(ValueError, match="at least one"):
        run_capacity_cost_realism_scenarios(
            run_pair_backtest_core(
                prices_a=[100.0, 101.0],
                prices_b=[100.0, 100.0],
                z_scores=[2.1, 0.0],
                aligned_timestamps=[
                    datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
                    datetime(2024, 1, 1, 0, 15, tzinfo=UTC),
                ],
                hedge_ratio=1.0,
                entry_threshold=2.0,
                exit_threshold=0.5,
                exit_policy=None,
                risk_exit_policy_disabled_reason="unit test uses convergence-only exits",
            ),
            base_cost_config=_verified_cost_config(),
            base_sharpe_ratio=1.0,
            periods_per_day=96.0,
            average_portfolio_value=10_000.0,
            scenarios=(),
        )


def test_capacity_cost_realism_guards_do_not_hide_default_scenarios() -> None:
    """The API should require callers to provide named realism scenarios."""
    scenario = CapacityRealismScenario(
        name="capital_50k",
        capital_size=50_000.0,
        liquidity=LiquidityImpactScenario(
            average_daily_quote_volume=1_000_000.0,
            market_impact_rate=0.0002,
        ),
        execution_delay=ExecutionDelayScenario(delay_bars=1, adverse_return_per_bar=0.0001),
        leg_risk=LegRiskScenario(unhedged_notional_fraction=0.05, adverse_move_rate=0.0005),
        cost_multiplier=1.0,
    )

    with pytest.raises(TypeError):
        run_capacity_cost_realism_scenarios(  # type: ignore[call-arg]
            run_pair_backtest_core(
                prices_a=[100.0, 101.0],
                prices_b=[100.0, 100.0],
                z_scores=[2.1, 0.0],
                aligned_timestamps=[
                    datetime(2024, 1, 1, 0, 0, tzinfo=UTC),
                    datetime(2024, 1, 1, 0, 15, tzinfo=UTC),
                ],
                hedge_ratio=1.0,
                entry_threshold=2.0,
                exit_threshold=0.5,
                exit_policy=None,
                risk_exit_policy_disabled_reason="unit test uses convergence-only exits",
            ),
            base_cost_config=_verified_cost_config(),
            base_sharpe_ratio=1.0,
            periods_per_day=96.0,
            average_portfolio_value=10_000.0,
        )

    assert scenario.name == "capital_50k"


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
