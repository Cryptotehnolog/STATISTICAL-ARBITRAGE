"""Backtest helpers for pair-trading research."""

from stat_arb.backtest.baseline import (
    BaselineAsset,
    BaselineComparisonResult,
    BaselineKind,
    BaselineSide,
    BuyAndHoldBaselineConfig,
    RandomSpreadBaselineConfig,
    compare_to_buy_and_hold_baseline,
    compare_to_random_spread_baseline,
)
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
    "BaselineAsset",
    "BaselineComparisonResult",
    "BaselineKind",
    "BaselineSide",
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
    "BuyAndHoldBaselineConfig",
    "ExposureByAssetAndSide",
    "HoldingTimeMetrics",
    "PnLAttributionResult",
    "PerformanceMetricConfig",
    "PerformanceMetricsResult",
    "RandomSpreadBaselineConfig",
    "SpreadPosition",
    "calculate_pair_pnl",
    "calculate_performance_metrics",
    "calculate_turnover",
    "compare_to_buy_and_hold_baseline",
    "compare_to_random_spread_baseline",
    "run_pair_backtest_core",
    "run_cost_sensitivity_analysis",
    "run_walk_forward_backtest_core",
]
