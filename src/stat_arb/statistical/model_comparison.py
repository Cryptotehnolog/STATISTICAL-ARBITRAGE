"""Explicit statistical model-comparison benchmark harness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import uuid4

import numpy as np
from numpy.typing import ArrayLike

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
        )

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
        reason=(
            f"{scenario.method} is registered as an explicit research scenario, "
            "but it is not implemented as a trusted production statistic yet."
        ),
    )
