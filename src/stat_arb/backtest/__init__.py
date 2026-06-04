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
from stat_arb.backtest.walk_forward import (
    BacktestWalkForwardConfig,
    BacktestWalkForwardFold,
    BacktestWalkForwardResult,
    run_walk_forward_backtest_core,
)

__all__ = [
    "BacktestAction",
    "BacktestCoreResult",
    "BacktestCostConfig",
    "BacktestStep",
    "BacktestWalkForwardConfig",
    "BacktestWalkForwardFold",
    "BacktestWalkForwardResult",
    "CostAssumptionStatus",
    "CostAttribution",
    "PnLAttributionResult",
    "SpreadPosition",
    "calculate_pair_pnl",
    "calculate_turnover",
    "run_pair_backtest_core",
    "run_walk_forward_backtest_core",
]
