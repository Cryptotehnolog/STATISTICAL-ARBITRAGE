"""Cost sensitivity analysis for pair backtests."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from stat_arb.backtest.core import BacktestCoreResult
from stat_arb.backtest.costs import BacktestCostConfig, PnLAttributionResult, calculate_pair_pnl


@dataclass(frozen=True)
class CostSensitivityScenario:
    """One explicit cost multiplier scenario."""

    name: str
    cost_multiplier: float

    def __post_init__(self) -> None:
        """Validate scenario name and multiplier."""
        if not self.name.strip():
            raise ValueError("sensitivity scenario name is required")
        if not np.isfinite(self.cost_multiplier) or self.cost_multiplier < 0.0:
            raise ValueError("cost_multiplier must be finite and non-negative")


@dataclass(frozen=True)
class CostSensitivityScenarioResult:
    """PnL result for one explicit cost sensitivity scenario."""

    scenario: CostSensitivityScenario
    pnl: PnLAttributionResult
    net_pnl_delta: float


@dataclass(frozen=True)
class CostSensitivityAnalysisResult:
    """Base PnL plus all explicit cost sensitivity scenarios."""

    base: PnLAttributionResult
    scenarios: tuple[CostSensitivityScenarioResult, ...]


def run_cost_sensitivity_analysis(
    core_result: BacktestCoreResult,
    *,
    base_cost_config: BacktestCostConfig,
    periods_per_day: float,
    average_portfolio_value: float | None,
    scenarios: tuple[CostSensitivityScenario, ...],
) -> CostSensitivityAnalysisResult:
    """Run base PnL and explicit cost multiplier scenarios."""
    if not scenarios:
        raise ValueError("at least one sensitivity scenario is required")
    _validate_unique_scenario_names(scenarios)

    base = calculate_pair_pnl(
        core_result,
        cost_config=base_cost_config,
        periods_per_day=periods_per_day,
        average_portfolio_value=average_portfolio_value,
    )
    scenario_results = tuple(
        _run_scenario(
            core_result,
            base=base,
            base_cost_config=base_cost_config,
            periods_per_day=periods_per_day,
            average_portfolio_value=average_portfolio_value,
            scenario=scenario,
        )
        for scenario in scenarios
    )
    return CostSensitivityAnalysisResult(base=base, scenarios=scenario_results)


def _run_scenario(
    core_result: BacktestCoreResult,
    *,
    base: PnLAttributionResult,
    base_cost_config: BacktestCostConfig,
    periods_per_day: float,
    average_portfolio_value: float | None,
    scenario: CostSensitivityScenario,
) -> CostSensitivityScenarioResult:
    scaled_config = _scaled_cost_config(base_cost_config, scenario=scenario)
    pnl = calculate_pair_pnl(
        core_result,
        cost_config=scaled_config,
        periods_per_day=periods_per_day,
        average_portfolio_value=average_portfolio_value,
    )
    return CostSensitivityScenarioResult(
        scenario=scenario,
        pnl=pnl,
        net_pnl_delta=float(pnl.net_pnl - base.net_pnl),
    )


def _scaled_cost_config(
    base_cost_config: BacktestCostConfig,
    *,
    scenario: CostSensitivityScenario,
) -> BacktestCostConfig:
    multiplier = scenario.cost_multiplier
    notes = base_cost_config.notes.strip()
    scenario_note = f"cost sensitivity scenario={scenario.name}, multiplier={multiplier:g}"
    notes = f"{notes}; {scenario_note}" if notes else scenario_note
    return BacktestCostConfig(
        commission_rate=base_cost_config.commission_rate * multiplier,
        spread_cost_rate=base_cost_config.spread_cost_rate * multiplier,
        slippage_rate=base_cost_config.slippage_rate * multiplier,
        funding_rate_daily=base_cost_config.funding_rate_daily * multiplier,
        borrow_rate_annual=base_cost_config.borrow_rate_annual * multiplier,
        status=base_cost_config.status,
        source=base_cost_config.source,
        verified_at=base_cost_config.verified_at,
        venue=base_cost_config.venue,
        market_type=base_cost_config.market_type,
        notes=notes,
    )


def _validate_unique_scenario_names(scenarios: tuple[CostSensitivityScenario, ...]) -> None:
    names = [scenario.name.strip().lower() for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ValueError("sensitivity scenario names must be unique")
