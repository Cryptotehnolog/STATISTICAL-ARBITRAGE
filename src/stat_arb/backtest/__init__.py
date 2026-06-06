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
from stat_arb.backtest.metrics import (
    ExposureByAssetAndSide,
    HoldingTimeMetrics,
    PerformanceMetricConfig,
    PerformanceMetricsResult,
    calculate_performance_metrics,
)
from stat_arb.backtest.sensitivity import (
    CostSensitivityAnalysisResult,
    CostSensitivityScenario,
    CostSensitivityScenarioResult,
    run_cost_sensitivity_analysis,
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
    "CostSensitivityAnalysisResult",
    "CostSensitivityScenario",
    "CostSensitivityScenarioResult",
    "ExposureByAssetAndSide",
    "HoldingTimeMetrics",
    "PnLAttributionResult",
    "PerformanceMetricConfig",
    "PerformanceMetricsResult",
    "SpreadPosition",
    "calculate_pair_pnl",
    "calculate_performance_metrics",
    "calculate_turnover",
    "run_pair_backtest_core",
    "run_cost_sensitivity_analysis",
    "run_walk_forward_backtest_core",
]
