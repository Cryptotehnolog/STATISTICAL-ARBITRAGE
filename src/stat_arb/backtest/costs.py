"""PnL and cost attribution for pair backtests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

import numpy as np

from stat_arb.backtest.core import BacktestAction, BacktestCoreResult, BacktestStep


class CostAssumptionStatus(StrEnum):
    """Verification status for a cost assumption snapshot."""

    VERIFIED = "verified"
    MANUAL_APPROVED = "manual_approved"
    STALE = "stale"
    REJECTED = "rejected"


@dataclass(frozen=True)
class BacktestCostConfig:
    """Explicit cost assumption snapshot used by a backtest run.

    Rates are decimal fractions, not percentages. For example, one basis point is 0.0001.
    No runtime defaults are provided on purpose: callers must supply a verified or manually
    approved snapshot with provenance.
    """

    commission_rate: float
    spread_cost_rate: float
    slippage_rate: float
    funding_rate_daily: float
    borrow_rate_annual: float
    status: CostAssumptionStatus
    source: str
    verified_at: datetime
    venue: str
    market_type: str
    notes: str = ""

    def __post_init__(self) -> None:
        """Validate cost rates and provenance at construction time."""
        rates = {
            "commission_rate": self.commission_rate,
            "spread_cost_rate": self.spread_cost_rate,
            "slippage_rate": self.slippage_rate,
            "funding_rate_daily": self.funding_rate_daily,
            "borrow_rate_annual": self.borrow_rate_annual,
        }
        for name, value in rates.items():
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and non-negative")
        if self.status not in {
            CostAssumptionStatus.VERIFIED,
            CostAssumptionStatus.MANUAL_APPROVED,
        }:
            raise ValueError("cost config must be verified or manually approved")
        if not self.source.strip():
            raise ValueError("cost config source is required")
        if not self.venue.strip():
            raise ValueError("cost config venue is required")
        if not self.market_type.strip():
            raise ValueError("cost config market_type is required")


@dataclass(frozen=True)
class CostAttribution:
    """Detailed cost breakdown for one backtest."""

    commission_cost: float
    spread_cost: float
    slippage_cost: float
    funding_cost: float
    borrow_cost: float

    @property
    def total_cost(self) -> float:
        """Return all costs summed."""
        return (
            self.commission_cost
            + self.spread_cost
            + self.slippage_cost
            + self.funding_cost
            + self.borrow_cost
        )


@dataclass(frozen=True)
class PnLAttributionResult:
    """Gross/net PnL and costs produced from pair position steps."""

    gross_pnl: float
    net_pnl: float
    costs: CostAttribution
    traded_value: float
    turnover: float
    observations: int
    num_trades: int


def calculate_pair_pnl(
    core_result: BacktestCoreResult,
    *,
    cost_config: BacktestCostConfig,
    periods_per_day: float,
    average_portfolio_value: float | None = None,
) -> PnLAttributionResult:
    """Calculate pair backtest gross PnL, net PnL, and cost attribution."""
    if periods_per_day <= 0.0 or not np.isfinite(periods_per_day):
        raise ValueError("periods_per_day must be finite and positive")
    if core_result.observations < 2:
        raise ValueError("PnL calculation requires at least 2 observations")
    if average_portfolio_value is not None and (
        average_portfolio_value <= 0.0 or not np.isfinite(average_portfolio_value)
    ):
        raise ValueError("average_portfolio_value must be finite and positive")

    gross_pnl = 0.0
    traded_value = 0.0
    commission_cost = 0.0
    spread_cost = 0.0
    slippage_cost = 0.0
    funding_cost = 0.0
    borrow_cost = 0.0
    period_days = 1.0 / periods_per_day

    previous_step = core_result.steps[0]
    traded_value += _step_traded_value(previous_step)
    commission_cost += traded_value * cost_config.commission_rate
    spread_cost += traded_value * cost_config.spread_cost_rate
    slippage_cost += traded_value * cost_config.slippage_rate

    for step in core_result.steps[1:]:
        gross_pnl += _interval_gross_pnl(previous_step, step)
        funding_cost += _interval_funding_cost(previous_step, cost_config, period_days)
        borrow_cost += _interval_borrow_cost(previous_step, cost_config, period_days)

        interval_traded = _transition_traded_value(previous_step, step)
        traded_value += interval_traded
        commission_cost += interval_traded * cost_config.commission_rate
        spread_cost += interval_traded * cost_config.spread_cost_rate
        slippage_cost += interval_traded * cost_config.slippage_rate
        previous_step = step

    costs = CostAttribution(
        commission_cost=float(commission_cost),
        spread_cost=float(spread_cost),
        slippage_cost=float(slippage_cost),
        funding_cost=float(funding_cost),
        borrow_cost=float(borrow_cost),
    )
    return PnLAttributionResult(
        gross_pnl=float(gross_pnl),
        net_pnl=float(gross_pnl - costs.total_cost),
        costs=costs,
        traded_value=float(traded_value),
        turnover=calculate_turnover(
            traded_value=traded_value,
            periods=core_result.observations - 1,
            periods_per_day=periods_per_day,
            average_portfolio_value=average_portfolio_value,
        ),
        observations=core_result.observations,
        num_trades=sum(1 for step in core_result.trades if step.action != BacktestAction.HOLD),
    )


def calculate_turnover(
    *,
    traded_value: float,
    periods: int,
    periods_per_day: float,
    average_portfolio_value: float | None,
) -> float:
    """Calculate daily turnover from traded value and average portfolio value.

    Turnover is annualization-free: total traded value divided by elapsed days and average
    portfolio value. If no portfolio value is provided, return 0 only when no value traded;
    otherwise fail so callers cannot silently invent capital assumptions.
    """
    if not np.isfinite(traded_value) or traded_value < 0.0:
        raise ValueError("traded_value must be finite and non-negative")
    if isinstance(periods, bool) or not isinstance(periods, int) or periods < 1:
        raise ValueError("periods must be a positive integer")
    if not np.isfinite(periods_per_day) or periods_per_day <= 0.0:
        raise ValueError("periods_per_day must be finite and positive")
    if average_portfolio_value is None:
        if traded_value == 0.0:
            return 0.0
        raise ValueError("average_portfolio_value is required when traded_value is positive")
    if not np.isfinite(average_portfolio_value) or average_portfolio_value <= 0.0:
        raise ValueError("average_portfolio_value must be finite and positive")

    elapsed_days = periods / periods_per_day
    return float(traded_value / (elapsed_days * average_portfolio_value))


def _interval_gross_pnl(previous_step: BacktestStep, current_step: BacktestStep) -> float:
    return (
        previous_step.position_a * (current_step.price_a - previous_step.price_a)
        + previous_step.position_b * (current_step.price_b - previous_step.price_b)
    )


def _step_traded_value(step: BacktestStep) -> float:
    return abs(step.position_a) * step.price_a + abs(step.position_b) * step.price_b


def _transition_traded_value(previous_step: BacktestStep, current_step: BacktestStep) -> float:
    delta_a = current_step.position_a - previous_step.position_a
    delta_b = current_step.position_b - previous_step.position_b
    return abs(delta_a) * current_step.price_a + abs(delta_b) * current_step.price_b


def _interval_funding_cost(
    previous_step: BacktestStep,
    cost_config: BacktestCostConfig,
    period_days: float,
) -> float:
    exposure = _step_traded_value(previous_step)
    return exposure * cost_config.funding_rate_daily * period_days


def _interval_borrow_cost(
    previous_step: BacktestStep,
    cost_config: BacktestCostConfig,
    period_days: float,
) -> float:
    short_exposure = 0.0
    if previous_step.position_a < 0.0:
        short_exposure += abs(previous_step.position_a) * previous_step.price_a
    if previous_step.position_b < 0.0:
        short_exposure += abs(previous_step.position_b) * previous_step.price_b
    return short_exposure * cost_config.borrow_rate_annual * (period_days / 365.0)
