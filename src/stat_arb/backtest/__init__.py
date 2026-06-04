"""Backtest helpers for pair-trading research."""

from stat_arb.backtest.core import (
    BacktestAction,
    BacktestCoreResult,
    BacktestStep,
    SpreadPosition,
    run_pair_backtest_core,
)
from stat_arb.backtest.costs import (
    BacktestCostConfig,
    CostAssumptionStatus,
    CostAttribution,
    PnLAttributionResult,
    calculate_pair_pnl,
    calculate_turnover,
)

__all__ = [
    "BacktestAction",
    "BacktestCoreResult",
    "BacktestCostConfig",
    "BacktestStep",
    "CostAssumptionStatus",
    "CostAttribution",
    "PnLAttributionResult",
    "SpreadPosition",
    "calculate_pair_pnl",
    "calculate_turnover",
    "run_pair_backtest_core",
]
