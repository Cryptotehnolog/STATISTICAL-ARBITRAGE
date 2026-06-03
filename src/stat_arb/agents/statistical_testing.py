"""Statistical Testing Agent service boundary."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

import numpy as np
from numpy.typing import ArrayLike
from sqlalchemy.orm import Session

from stat_arb.domain import StatisticalTestResult as DomainStatisticalTestResult
from stat_arb.memory import MemoryRecordType, MemoryWriteRequest
from stat_arb.statistical import (
    adf_stationarity_test,
    chronological_train_test_split,
    detect_regime_changes,
    engle_granger_cointegration_test,
    estimate_half_life,
    estimate_hedge_ratio,
)
from stat_arb.storage.models import (
    DataQualityReportRecord,
)
from stat_arb.storage.models import (
    StatisticalTestResult as StoredStatisticalTestResult,
)


class MemoryWriter(Protocol):
    """Minimal Memory Agent service protocol used by this boundary."""

    def write(self, request: MemoryWriteRequest) -> object:
        """Write a policy-approved memory record."""


@dataclass(frozen=True)
class StatisticalTestingInput:
    """Input contract for one pair validation run."""

    hypothesis_id: UUID
    dataset_a_id: UUID
    dataset_b_id: UUID
    prices_a: ArrayLike
    prices_b: ArrayLike
    aligned_timestamps: Sequence[datetime]
    train_fraction: float = 0.7
    alpha: float = 0.05
    periods_per_day: float = 1.0
    regime_window: int = 60


@dataclass(frozen=True)
class StatisticalTestingRunResult:
    """Result of a registry-backed statistical testing run."""

    domain_result: DomainStatisticalTestResult
    stored_result: StoredStatisticalTestResult
    memory_written: bool


def run_statistical_testing(
    request: StatisticalTestingInput,
    *,
    session: Session,
    memory_service: MemoryWriter | None = None,
) -> StatisticalTestingRunResult:
    """Run statistical pair validation after registry data-quality prerequisites."""
    prices_a = _as_1d_finite_array(request.prices_a, name="prices_a")
    prices_b = _as_1d_finite_array(request.prices_b, name="prices_b")
    aligned_timestamps = tuple(request.aligned_timestamps)
    _validate_inputs(prices_a, prices_b, aligned_timestamps)
    _require_passed_data_quality_reports(
        session,
        dataset_ids=(request.dataset_a_id, request.dataset_b_id),
    )

    split = chronological_train_test_split(
        prices_a.size,
        train_fraction=request.train_fraction,
        min_train_size=20,
        min_test_size=1,
    )
    train_slice = slice(split.train.start, split.train.end)
    train_a = prices_a[train_slice]
    train_b = prices_b[train_slice]

    cointegration = engle_granger_cointegration_test(train_a, train_b, alpha=request.alpha)
    hedge_ratio = estimate_hedge_ratio(train_a, train_b)
    residuals = train_a - (hedge_ratio.intercept + hedge_ratio.hedge_ratio * train_b)
    adf = adf_stationarity_test(residuals, alpha=request.alpha)
    half_life = estimate_half_life(residuals, periods_per_day=request.periods_per_day)
    regime = detect_regime_changes(
        residuals,
        window=min(request.regime_window, max(5, residuals.size // 2)),
    )

    rejection_reasons = _rejection_reasons(
        cointegration_passed=cointegration.passed,
        adf_passed=adf.passed,
        regime_changes_detected=regime.has_regime_change,
    )
    passed = not rejection_reasons
    domain_result = DomainStatisticalTestResult(
        hypothesis_id=request.hypothesis_id,
        dataset_a_id=request.dataset_a_id,
        dataset_b_id=request.dataset_b_id,
        train_start=aligned_timestamps[split.train.start],
        train_end=aligned_timestamps[split.train.end - 1],
        test_start=aligned_timestamps[split.test.start],
        test_end=aligned_timestamps[split.test.end - 1],
        cointegration_statistic=cointegration.statistic,
        cointegration_p_value=cointegration.p_value,
        adf_statistic=adf.statistic,
        adf_p_value=adf.p_value,
        hedge_ratio=hedge_ratio.hedge_ratio,
        hedge_ratio_r_squared=hedge_ratio.r_squared,
        half_life_days=half_life.half_life_days,
        regime_changes_detected=regime.has_regime_change,
        passed=passed,
        rejection_reason="; ".join(rejection_reasons) if rejection_reasons else None,
    )
    stored_result = _persist_statistical_result(session, domain_result)
    memory_written = False
    if memory_service is not None:
        memory_service.write(_memory_request_for(domain_result))
        memory_written = True

    return StatisticalTestingRunResult(
        domain_result=domain_result,
        stored_result=stored_result,
        memory_written=memory_written,
    )


def _as_1d_finite_array(values: ArrayLike, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _validate_inputs(
    prices_a: np.ndarray,
    prices_b: np.ndarray,
    aligned_timestamps: Sequence[datetime],
) -> None:
    if prices_a.shape != prices_b.shape:
        raise ValueError("prices_a and prices_b must have the same length")
    if prices_a.size < 21:
        raise ValueError("statistical testing requires at least 21 observations")
    if len(aligned_timestamps) != prices_a.size:
        raise ValueError("aligned_timestamps must match price series length")
    if any(
        aligned_timestamps[index] >= aligned_timestamps[index + 1]
        for index in range(len(aligned_timestamps) - 1)
    ):
        raise ValueError("aligned_timestamps must be strictly increasing")


def _require_passed_data_quality_reports(
    session: Session,
    *,
    dataset_ids: tuple[UUID, UUID],
) -> None:
    for dataset_id in dataset_ids:
        report = (
            session.query(DataQualityReportRecord)
            .filter(
                DataQualityReportRecord.dataset_id == str(dataset_id),
                DataQualityReportRecord.passed.is_(True),
            )
            .first()
        )
        if report is None:
            raise ValueError(f"passed data quality report is required for dataset {dataset_id}")


def _rejection_reasons(
    *,
    cointegration_passed: bool,
    adf_passed: bool,
    regime_changes_detected: bool,
) -> list[str]:
    reasons: list[str] = []
    if not cointegration_passed:
        reasons.append("cointegration test failed")
    if not adf_passed:
        reasons.append("ADF residual stationarity test failed")
    if regime_changes_detected:
        reasons.append("regime change detected")
    return reasons


def _persist_statistical_result(
    session: Session,
    result: DomainStatisticalTestResult,
) -> StoredStatisticalTestResult:
    stored = StoredStatisticalTestResult(
        test_id=str(result.test_id),
        hypothesis_id=str(result.hypothesis_id),
        dataset_a_id=str(result.dataset_a_id),
        dataset_b_id=str(result.dataset_b_id),
        train_start=result.train_start,
        train_end=result.train_end,
        test_start=result.test_start,
        test_end=result.test_end,
        cointegration_statistic=result.cointegration_statistic,
        cointegration_p_value=result.cointegration_p_value,
        adf_statistic=result.adf_statistic,
        adf_p_value=result.adf_p_value,
        hedge_ratio=result.hedge_ratio,
        hedge_ratio_r_squared=result.hedge_ratio_r_squared,
        half_life_days=result.half_life_days,
        regime_changes_detected=result.regime_changes_detected,
        passed=result.passed,
        rejection_reason=result.rejection_reason,
        tested_at=result.tested_at,
    )
    session.add(stored)
    session.flush()
    return stored


def _memory_request_for(result: DomainStatisticalTestResult) -> MemoryWriteRequest:
    status = "passed" if result.passed else "failed"
    reason = result.rejection_reason or "all configured statistical checks passed"
    return MemoryWriteRequest(
        record_type=MemoryRecordType.LESSON,
        title=f"Statistical validation {status}",
        body=(
            f"Pair statistical validation {status}. Structured test metrics are stored "
            f"in the registry. Decision reason: {reason}."
        ),
        source_id=str(result.test_id),
        registry_reference=f"registry:statistical_test_results/{result.test_id}",
        tags=["statistical-testing", status],
        metadata={
            "hypothesis_id": str(result.hypothesis_id),
            "dataset_a_id": str(result.dataset_a_id),
            "dataset_b_id": str(result.dataset_b_id),
        },
    )
