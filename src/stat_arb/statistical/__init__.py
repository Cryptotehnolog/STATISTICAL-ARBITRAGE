"""Statistical testing helpers for pair validation."""

from stat_arb.statistical.cointegration import (
    CointegrationTestResult,
    MultipleTestingMethod,
    adjust_p_values,
    engle_granger_cointegration_test,
)
from stat_arb.statistical.hedge_ratio import HedgeRatioResult, estimate_hedge_ratio
from stat_arb.statistical.mean_reversion import HalfLifeResult, estimate_half_life
from stat_arb.statistical.model_comparison import (
    ModelComparisonMethod,
    ModelComparisonReport,
    ModelComparisonScenario,
    ModelComparisonScenarioResult,
    compare_cointegration_models,
)
from stat_arb.statistical.regime import (
    RegimeChangePoint,
    RegimeChangeResult,
    detect_regime_changes,
)
from stat_arb.statistical.residual_diagnostics import (
    ResidualDiagnosticsResult,
    diagnose_residuals,
)
from stat_arb.statistical.stability import (
    StabilityDiagnosticsConfig,
    StabilityDiagnosticsResult,
    diagnose_pair_stability,
)
from stat_arb.statistical.stationarity import ADFTestResult, adf_stationarity_test
from stat_arb.statistical.validation import (
    IndexWindow,
    TrainTestSplit,
    WalkForwardWindow,
    assert_no_lookahead,
    chronological_train_test_split,
    generate_walk_forward_windows,
)
from stat_arb.statistical.zscore import ZScoreResult, construct_rolling_zscore

__all__ = [
    "ADFTestResult",
    "CointegrationTestResult",
    "HalfLifeResult",
    "HedgeRatioResult",
    "IndexWindow",
    "ModelComparisonMethod",
    "ModelComparisonReport",
    "ModelComparisonScenario",
    "ModelComparisonScenarioResult",
    "MultipleTestingMethod",
    "RegimeChangePoint",
    "RegimeChangeResult",
    "ResidualDiagnosticsResult",
    "StabilityDiagnosticsConfig",
    "StabilityDiagnosticsResult",
    "TrainTestSplit",
    "WalkForwardWindow",
    "ZScoreResult",
    "adf_stationarity_test",
    "assert_no_lookahead",
    "adjust_p_values",
    "chronological_train_test_split",
    "compare_cointegration_models",
    "construct_rolling_zscore",
    "detect_regime_changes",
    "diagnose_residuals",
    "diagnose_pair_stability",
    "engle_granger_cointegration_test",
    "estimate_half_life",
    "estimate_hedge_ratio",
    "generate_walk_forward_windows",
]
