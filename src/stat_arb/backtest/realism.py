"""Capacity, liquidity, execution-delay, and leg-risk realism scenarios."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from stat_arb.backtest.core import BacktestCoreResult
from stat_arb.backtest.costs import BacktestCostConfig, PnLAttributionResult
from stat_arb.backtest.sensitivity import CostSensitivityScenario, run_cost_sensitivity_analysis


@dataclass(frozen=True)
class LiquidityImpactScenario:
    """Explicit liquidity evidence and market-impact assumption for one scenario."""

    average_daily_quote_volume: float
    market_impact_rate: float

    def __post_init__(self) -> None:
        _validate_positive_float(
            self.average_daily_quote_volume,
            label="average_daily_quote_volume",
        )
        _validate_non_negative_float(self.market_impact_rate, label="market_impact_rate")


@dataclass(frozen=True)
class ExecutionDelayScenario:
    """Explicit execution-delay stress assumption."""

    delay_bars: int
    adverse_return_per_bar: float

    def __post_init__(self) -> None:
        if isinstance(self.delay_bars, bool) or not isinstance(self.delay_bars, int):
            raise TypeError("delay_bars must be an integer")
        if self.delay_bars < 0:
            raise ValueError("delay_bars must be non-negative")
        _validate_non_negative_float(
            self.adverse_return_per_bar,
            label="adverse_return_per_bar",
        )


@dataclass(frozen=True)
class LegRiskScenario:
    """Explicit unhedged-leg stress assumption."""

    unhedged_notional_fraction: float
    adverse_move_rate: float

    def __post_init__(self) -> None:
        _validate_probability_like(
            self.unhedged_notional_fraction,
            label="unhedged_notional_fraction",
        )
        _validate_non_negative_float(self.adverse_move_rate, label="adverse_move_rate")


@dataclass(frozen=True)
class CapacityRealismScenario:
    """One explicit capacity/cost realism scenario."""

    name: str
    capital_size: float
    liquidity: LiquidityImpactScenario
    execution_delay: ExecutionDelayScenario
    leg_risk: LegRiskScenario
    cost_multiplier: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("capacity realism scenario name is required")
        _validate_positive_float(self.capital_size, label="capital_size")
        _validate_non_negative_float(self.cost_multiplier, label="cost_multiplier")


@dataclass(frozen=True)
class CapacityRealismScenarioResult:
    """Result of one explicit capacity/cost realism scenario."""

    scenario: CapacityRealismScenario
    pnl: PnLAttributionResult
    participation_rate: float
    market_impact_cost: float
    execution_delay_cost: float
    leg_risk_cost: float
    realism_net_pnl: float
    capacity_adjusted_sharpe: float


@dataclass(frozen=True)
class CapacityRealismAnalysisResult:
    """Base PnL plus explicit capacity/cost realism scenarios."""

    base: PnLAttributionResult
    base_sharpe_ratio: float
    scenarios: tuple[CapacityRealismScenarioResult, ...]

    @property
    def scenario_names(self) -> tuple[str, ...]:
        """Return scenario names for Critic coverage checks."""
        return tuple(result.scenario.name for result in self.scenarios)

    @property
    def worst_capacity_adjusted_sharpe(self) -> float:
        """Return the lowest capacity-adjusted Sharpe across scenarios."""
        return min(result.capacity_adjusted_sharpe for result in self.scenarios)

    @property
    def min_realism_net_pnl(self) -> float:
        """Return the lowest net PnL after explicit realism stresses."""
        return min(result.realism_net_pnl for result in self.scenarios)

    @property
    def max_participation_rate(self) -> float:
        """Return the largest capital-to-liquidity participation rate."""
        return max(result.participation_rate for result in self.scenarios)

    @property
    def max_execution_delay_cost(self) -> float:
        """Return the largest execution-delay stress cost."""
        return max(result.execution_delay_cost for result in self.scenarios)


def run_capacity_cost_realism_scenarios(
    core_result: BacktestCoreResult,
    *,
    base_cost_config: BacktestCostConfig,
    base_sharpe_ratio: float,
    periods_per_day: float,
    average_portfolio_value: float,
    scenarios: tuple[CapacityRealismScenario, ...],
) -> CapacityRealismAnalysisResult:
    """Run explicit capacity, liquidity, execution-delay, and leg-risk scenarios."""
    _validate_finite_float(base_sharpe_ratio, label="base_sharpe_ratio")
    _validate_positive_float(average_portfolio_value, label="average_portfolio_value")
    if not scenarios:
        raise ValueError("at least one capacity realism scenario is required")
    _validate_unique_scenario_names(scenarios)

    sensitivity = run_cost_sensitivity_analysis(
        core_result,
        base_cost_config=base_cost_config,
        periods_per_day=periods_per_day,
        average_portfolio_value=average_portfolio_value,
        scenarios=tuple(
            CostSensitivityScenario(
                name=scenario.name,
                cost_multiplier=scenario.cost_multiplier,
            )
            for scenario in scenarios
        ),
    )
    scenario_results = tuple(
        _run_realism_scenario(
            scenario,
            pnl=sensitivity.scenarios[index].pnl,
            base_sharpe_ratio=base_sharpe_ratio,
        )
        for index, scenario in enumerate(scenarios)
    )
    return CapacityRealismAnalysisResult(
        base=sensitivity.base,
        base_sharpe_ratio=base_sharpe_ratio,
        scenarios=scenario_results,
    )


def _run_realism_scenario(
    scenario: CapacityRealismScenario,
    *,
    pnl: PnLAttributionResult,
    base_sharpe_ratio: float,
) -> CapacityRealismScenarioResult:
    participation_rate = scenario.capital_size / scenario.liquidity.average_daily_quote_volume
    market_impact_cost = scenario.capital_size * participation_rate * scenario.liquidity.market_impact_rate
    execution_delay_cost = (
        scenario.capital_size
        * scenario.execution_delay.delay_bars
        * scenario.execution_delay.adverse_return_per_bar
    )
    leg_risk_cost = (
        scenario.capital_size
        * scenario.leg_risk.unhedged_notional_fraction
        * scenario.leg_risk.adverse_move_rate
    )
    total_realism_cost = market_impact_cost + execution_delay_cost + leg_risk_cost
    realism_net_pnl = pnl.net_pnl - total_realism_cost
    capacity_adjusted_sharpe = _capacity_adjusted_sharpe(
        base_sharpe_ratio=base_sharpe_ratio,
        scenario_net_pnl=pnl.net_pnl,
        realism_net_pnl=realism_net_pnl,
    )
    return CapacityRealismScenarioResult(
        scenario=scenario,
        pnl=pnl,
        participation_rate=float(participation_rate),
        market_impact_cost=float(market_impact_cost),
        execution_delay_cost=float(execution_delay_cost),
        leg_risk_cost=float(leg_risk_cost),
        realism_net_pnl=float(realism_net_pnl),
        capacity_adjusted_sharpe=float(capacity_adjusted_sharpe),
    )


def _capacity_adjusted_sharpe(
    *,
    base_sharpe_ratio: float,
    scenario_net_pnl: float,
    realism_net_pnl: float,
) -> float:
    if scenario_net_pnl <= 0.0:
        return 0.0 if realism_net_pnl <= 0.0 else base_sharpe_ratio
    return float(base_sharpe_ratio * (realism_net_pnl / scenario_net_pnl))


def _validate_unique_scenario_names(scenarios: tuple[CapacityRealismScenario, ...]) -> None:
    names = [scenario.name.strip().lower() for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ValueError("capacity realism scenario names must be unique")


def _validate_finite_float(value: float, *, label: str) -> None:
    if not np.isfinite(value):
        raise ValueError(f"{label} must be finite")


def _validate_positive_float(value: float, *, label: str) -> None:
    if not np.isfinite(value) or value <= 0.0:
        raise ValueError(f"{label} must be finite and positive")


def _validate_non_negative_float(value: float, *, label: str) -> None:
    if not np.isfinite(value) or value < 0.0:
        raise ValueError(f"{label} must be finite and non-negative")


def _validate_probability_like(value: float, *, label: str) -> None:
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be between 0 and 1")
