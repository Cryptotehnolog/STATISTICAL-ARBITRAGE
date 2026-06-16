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
    BacktestExitPolicyConfig,
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
from stat_arb.backtest.realism import (
    CapacityRealismAnalysisResult,
    CapacityRealismScenario,
    CapacityRealismScenarioResult,
    ExecutionDelayScenario,
    LegRiskScenario,
    LiquidityImpactScenario,
    run_capacity_cost_realism_scenarios,
)
from stat_arb.backtest.reproducibility import (
    ReproducibilityManifest,
    calculate_config_hash,
    create_reproducibility_manifest,
    hash_file,
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
    "BacktestExitPolicyConfig",
    "BacktestStep",
    "BacktestWalkForwardConfig",
    "BacktestWalkForwardFold",
    "BacktestWalkForwardResult",
    "CapacityRealismAnalysisResult",
    "CapacityRealismScenario",
    "CapacityRealismScenarioResult",
    "CostAssumptionStatus",
    "CostAttribution",
    "CostSensitivityAnalysisResult",
    "CostSensitivityScenario",
    "CostSensitivityScenarioResult",
    "ExecutionDelayScenario",
    "BuyAndHoldBaselineConfig",
    "ExposureByAssetAndSide",
    "HoldingTimeMetrics",
    "LegRiskScenario",
    "LiquidityImpactScenario",
    "PnLAttributionResult",
    "PerformanceMetricConfig",
    "PerformanceMetricsResult",
    "RandomSpreadBaselineConfig",
    "ReproducibilityManifest",
    "SpreadPosition",
    "calculate_config_hash",
    "calculate_pair_pnl",
    "calculate_performance_metrics",
    "calculate_turnover",
    "compare_to_buy_and_hold_baseline",
    "compare_to_random_spread_baseline",
    "create_reproducibility_manifest",
    "hash_file",
    "run_pair_backtest_core",
    "run_capacity_cost_realism_scenarios",
    "run_cost_sensitivity_analysis",
    "run_walk_forward_backtest_core",
]
