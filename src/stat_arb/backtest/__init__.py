"""Backtest helpers for pair-trading research."""

from stat_arb.backtest.core import (
    BacktestAction,
    BacktestCoreResult,
    BacktestStep,
    SpreadPosition,
    run_pair_backtest_core,
)

__all__ = [
    "BacktestAction",
    "BacktestCoreResult",
    "BacktestStep",
    "SpreadPosition",
    "run_pair_backtest_core",
]
