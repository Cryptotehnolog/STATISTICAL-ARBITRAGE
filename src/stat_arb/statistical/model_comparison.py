"""Explicit statistical model-comparison benchmark harness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import uuid4

import numpy as np
from numpy.typing import ArrayLike
from statsmodels.tsa.vector_ar.vecm import coint_johansen

from stat_arb.statistical.cointegration import (
    MultipleTestingMethod,
    engle_granger_cointegration_test,
)


class ModelComparisonMethod(StrEnum):
    """Supported model-comparison scenario identifiers."""

    ENGLE_GRANGER = "engle_granger"
    KALMAN = "kalman"
    JOHANSEN = "johansen"
    PHILLIPS_PERRON = "phillips_perron"


@dataclass(frozen=True)
class ModelComparisonScenario:
    """Explicit benchmark scenario for one statistical method."""

    name: str
    method: ModelComparisonMethod
    alpha: float
    parameters: dict[str, Any]
    is_baseline: bool

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("scenario name is required")
        if not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must be between 0 and 1")
        try:
            json.dumps(self.parameters, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ValueError("scenario parameters must be JSON-serializable") from exc


@dataclass(frozen=True)
class ModelComparisonScenarioResult:
    """Result for one model-comparison scenario."""

    name: str
    method: ModelComparisonMethod
    is_baseline: bool
    status: str
    statistic: float | None
    p_value: float | None
    passed: bool | None
    alpha: float
    observations: int
    parameters: dict[str, Any]
    details: dict[str, Any]
    reason: str | None = None


@dataclass(frozen=True)
class ModelComparisonReport:
    """Benchmark evidence for alternative pair-validation methods."""

    comparison_id: str
    hypothesis_id: str | None
    dataset_ids: tuple[str, str] | None
    baseline_method: ModelComparisonMethod
    results: tuple[ModelComparisonScenarioResult, ...]
    promotion_decision: None
    decision_boundary: str

    def to_payload(self) -> dict[str, Any]:
        """Return a stable JSON payload for registry/artifact persistence."""
        return {
            "comparison_id": self.comparison_id,
            "hypothesis_id": self.hypothesis_id,
            "dataset_ids": list(self.dataset_ids) if self.dataset_ids is not None else None,
            "baseline_method": self.baseline_method,
            "promotion_decision": self.promotion_decision,
            "decision_boundary": self.decision_boundary,
            "results": [
                {
                    "name": result.name,
                    "method": result.method,
                    "is_baseline": result.is_baseline,
                    "status": result.status,
                    "statistic": result.statistic,
                    "p_value": result.p_value,
                    "passed": result.passed,
                    "alpha": result.alpha,
                    "observations": result.observations,
                    "parameters": result.parameters,
                    "details": result.details,
                    "reason": result.reason,
                }
                for result in self.results
            ],
        }


def compare_cointegration_models(
    asset_a: ArrayLike,
    asset_b: ArrayLike,
    *,
    scenarios: tuple[ModelComparisonScenario, ...],
    dataset_ids: tuple[str, str] | None = None,
    hypothesis_id: str | None = None,
) -> ModelComparisonReport:
    """Compare explicitly requested statistical methods without making promotion decisions."""
    _validate_scenarios(scenarios)
    baseline = next(scenario for scenario in scenarios if scenario.is_baseline)

    results = tuple(_run_scenario(asset_a, asset_b, scenario) for scenario in scenarios)
    return ModelComparisonReport(
        comparison_id=str(uuid4()),
        hypothesis_id=hypothesis_id,
        dataset_ids=dataset_ids,
        baseline_method=baseline.method,
        results=results,
        promotion_decision=None,
        decision_boundary=(
            "Model comparison is evidence only; Coordinator/Critic promotion decisions must use "
            "explicit policies and registry-backed experiment context."
        ),
    )


def _validate_scenarios(scenarios: tuple[ModelComparisonScenario, ...]) -> None:
    if not scenarios:
        raise ValueError("at least one model-comparison scenario is required")
    baselines = tuple(scenario for scenario in scenarios if scenario.is_baseline)
    if len(baselines) != 1:
        raise ValueError("exactly one baseline scenario is required")
    if baselines[0].method != ModelComparisonMethod.ENGLE_GRANGER:
        raise ValueError("baseline must use engle_granger")
    names = [scenario.name for scenario in scenarios]
    if len(set(names)) != len(names):
        raise ValueError("scenario names must be unique")


def _run_scenario(
    asset_a: ArrayLike,
    asset_b: ArrayLike,
    scenario: ModelComparisonScenario,
) -> ModelComparisonScenarioResult:
    if scenario.method == ModelComparisonMethod.ENGLE_GRANGER:
        result = engle_granger_cointegration_test(
            asset_a,
            asset_b,
            alpha=scenario.alpha,
            multiple_testing_method=MultipleTestingMethod.NONE,
        )
        return ModelComparisonScenarioResult(
            name=scenario.name,
            method=scenario.method,
            is_baseline=scenario.is_baseline,
            status="completed",
            statistic=result.statistic,
            p_value=result.p_value,
            passed=result.passed,
            alpha=scenario.alpha,
            observations=result.observations,
            parameters=scenario.parameters,
            details={
                "critical_values": result.critical_values,
                "corrected_p_value": result.corrected_p_value,
                "multiple_testing_method": result.multiple_testing_method,
            },
        )
    if scenario.method == ModelComparisonMethod.JOHANSEN:
        return _run_johansen_scenario(asset_a, asset_b, scenario)

    observations = int(np.asarray(asset_a).size)
    return ModelComparisonScenarioResult(
        name=scenario.name,
        method=scenario.method,
        is_baseline=scenario.is_baseline,
        status="not_implemented",
        statistic=None,
        p_value=None,
        passed=None,
        alpha=scenario.alpha,
        observations=observations,
        parameters=scenario.parameters,
        details={},
        reason=(
            f"{scenario.method} is registered as an explicit research scenario, "
            "but it is not implemented as a trusted production statistic yet."
        ),
    )


def _run_johansen_scenario(
    asset_a: ArrayLike,
    asset_b: ArrayLike,
    scenario: ModelComparisonScenario,
) -> ModelComparisonScenarioResult:
    series_a = _as_1d_finite_array(asset_a, name="asset_a")
    series_b = _as_1d_finite_array(asset_b, name="asset_b")
    if series_a.shape != series_b.shape:
        raise ValueError("asset_a and asset_b must have the same length")
    if series_a.size < 20:
        raise ValueError("Johansen scenario requires at least 20 observations")

    det_order = _required_int_parameter(scenario, "det_order")
    k_ar_diff = _required_int_parameter(scenario, "k_ar_diff")
    if k_ar_diff < 0:
        raise ValueError("k_ar_diff must be non-negative")

    critical_value_index, critical_value_level = _johansen_critical_value_level(scenario.alpha)
    data = np.column_stack((series_a, series_b))
    result = coint_johansen(data, det_order=det_order, k_ar_diff=k_ar_diff)
    trace_statistic = float(result.lr1[0])
    max_eigen_statistic = float(result.lr2[0])
    trace_critical_values = tuple(float(value) for value in result.cvt[0])
    max_eigen_critical_values = tuple(float(value) for value in result.cvm[0])
    critical_value = trace_critical_values[critical_value_index]

    return ModelComparisonScenarioResult(
        name=scenario.name,
        method=scenario.method,
        is_baseline=scenario.is_baseline,
        status="completed",
        statistic=trace_statistic,
        p_value=None,
        passed=trace_statistic > critical_value,
        alpha=scenario.alpha,
        observations=int(series_a.size),
        parameters=scenario.parameters,
        details={
            "trace_statistic_rank_0": trace_statistic,
            "max_eigen_statistic_rank_0": max_eigen_statistic,
            "critical_value": critical_value,
            "critical_value_level": critical_value_level,
            "trace_critical_values": {
                "90%": trace_critical_values[0],
                "95%": trace_critical_values[1],
                "99%": trace_critical_values[2],
            },
            "max_eigen_critical_values": {
                "90%": max_eigen_critical_values[0],
                "95%": max_eigen_critical_values[1],
                "99%": max_eigen_critical_values[2],
            },
        },
    )


def _required_int_parameter(scenario: ModelComparisonScenario, name: str) -> int:
    if name not in scenario.parameters:
        raise ValueError(f"{name} is required for {scenario.method}")
    value = scenario.parameters[name]
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer for {scenario.method}")
    return value


def _johansen_critical_value_level(alpha: float) -> tuple[int, str]:
    supported = {
        0.10: (0, "90%"),
        0.05: (1, "95%"),
        0.01: (2, "99%"),
    }
    for supported_alpha, value in supported.items():
        if abs(alpha - supported_alpha) < 1e-12:
            return value
    raise ValueError("supported Johansen alpha values are 0.10, 0.05, and 0.01")


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array
