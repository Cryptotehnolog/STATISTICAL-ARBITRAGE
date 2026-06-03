"""Statistical testing helpers for pair validation."""

from stat_arb.statistical.cointegration import (
    CointegrationTestResult,
    MultipleTestingMethod,
    adjust_p_values,
    engle_granger_cointegration_test,
)

__all__ = [
    "CointegrationTestResult",
    "MultipleTestingMethod",
    "adjust_p_values",
    "engle_granger_cointegration_test",
]
