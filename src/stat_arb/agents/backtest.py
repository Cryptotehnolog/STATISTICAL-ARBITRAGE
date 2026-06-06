"""Backtest Agent registry and memory integration boundary.

This boundary accepts completed backtest results that were built from aligned_timestamps
upstream. It must not accept raw OHLCV pairs or perform alignment itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from stat_arb.backtest import (
    BacktestCoreResult,
    BaselineComparisonResult,
    CostSensitivityAnalysisResult,
    PerformanceMetricsResult,
    PnLAttributionResult,
    ReproducibilityManifest,
)
from stat_arb.memory import MemoryRecordType, MemoryWriteRequest
from stat_arb.storage.models import (
    BacktestResult as StoredBacktestResult,
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
class BacktestAgentInput:
    """Input contract for persisting one completed backtest."""

    hypothesis_id: UUID
    test_id: UUID
    dataset_a_id: UUID
    dataset_b_id: UUID
    core_result: BacktestCoreResult
    pnl: PnLAttributionResult
    metrics: PerformanceMetricsResult
    baseline: BaselineComparisonResult
    sensitivity: CostSensitivityAnalysisResult
    reproducibility: ReproducibilityManifest
    train_window_days: int
    test_window_days: int
    num_windows: int


@dataclass(frozen=True)
class BacktestAgentRunResult:
    """Result of a registry-backed Backtest Agent persistence step."""

    stored_result: StoredBacktestResult
    memory_written: bool


def run_backtest_agent_persistence(
    request: BacktestAgentInput,
    *,
    session: Session,
    memory_service: MemoryWriter | None = None,
) -> BacktestAgentRunResult:
    """Persist structured backtest results and write a concise memory summary."""
    _validate_request(request)
    _require_passed_data_quality_reports(
        session,
        dataset_ids=(request.dataset_a_id, request.dataset_b_id),
    )
    _require_passed_statistical_test(session, test_id=request.test_id)

    stored = _persist_backtest_result(session, request)
    memory_written = False
    if memory_service is not None:
        memory_service.write(_memory_request_for(stored))
        memory_written = True

    return BacktestAgentRunResult(stored_result=stored, memory_written=memory_written)


def _persist_backtest_result(
    session: Session,
    request: BacktestAgentInput,
) -> StoredBacktestResult:
    sensitivity_by_name = {
        result.scenario.name.strip().lower(): result.pnl.net_pnl
        for result in request.sensitivity.scenarios
    }
    if "double_costs" not in sensitivity_by_name or "half_costs" not in sensitivity_by_name:
        raise ValueError("sensitivity must include double_costs and half_costs scenarios")

    stored = StoredBacktestResult(
        hypothesis_id=str(request.hypothesis_id),
        test_id=str(request.test_id),
        dataset_a_id=str(request.dataset_a_id),
        dataset_b_id=str(request.dataset_b_id),
        git_commit_hash=request.reproducibility.git_commit_hash,
        config_hash=request.reproducibility.config_hash,
        train_window_days=request.train_window_days,
        test_window_days=request.test_window_days,
        num_windows=request.num_windows,
        entry_threshold=request.core_result.entry_threshold,
        exit_threshold=request.core_result.exit_threshold,
        hedge_ratio=request.core_result.hedge_ratio,
        gross_pnl=request.pnl.gross_pnl,
        net_pnl=request.pnl.net_pnl,
        commission_cost=request.pnl.costs.commission_cost,
        spread_cost=request.pnl.costs.spread_cost,
        slippage_cost=request.pnl.costs.slippage_cost,
        funding_cost=request.pnl.costs.funding_cost,
        borrow_cost=request.pnl.costs.borrow_cost,
        num_trades=request.pnl.num_trades,
        turnover=request.pnl.turnover,
        avg_holding_time_hours=request.metrics.holding_times.average_holding_time_hours,
        median_holding_time_hours=request.metrics.holding_times.median_holding_time_hours,
        sharpe_ratio=request.metrics.sharpe_ratio,
        sortino_ratio=request.metrics.sortino_ratio,
        volatility=request.metrics.volatility,
        max_drawdown=request.metrics.max_drawdown,
        win_rate=request.metrics.win_rate,
        profit_factor=request.metrics.profit_factor,
        net_pnl_2x_costs=sensitivity_by_name["double_costs"],
        net_pnl_half_costs=sensitivity_by_name["half_costs"],
        baseline_sharpe=request.baseline.baseline_sharpe_ratio,
        tested_at=request.reproducibility.run_timestamp,
    )
    session.add(stored)
    session.flush()
    return stored


def _memory_request_for(result: StoredBacktestResult) -> MemoryWriteRequest:
    return MemoryWriteRequest(
        record_type=MemoryRecordType.REPORT_SUMMARY,
        title="Backtest completed",
        body=(
            "Backtest completed. Structured performance metrics, cost attribution, "
            "baseline comparison, and reproducibility hashes are stored in the registry."
        ),
        source_id=result.backtest_id,
        registry_reference=f"registry:backtest_results/{result.backtest_id}",
        tags=["backtest", "report-summary"],
        metadata={
            "hypothesis_id": result.hypothesis_id,
            "test_id": result.test_id,
            "dataset_a_id": result.dataset_a_id,
            "dataset_b_id": result.dataset_b_id,
        },
    )


def _validate_request(request: BacktestAgentInput) -> None:
    if request.dataset_a_id == request.dataset_b_id:
        raise ValueError("dataset_a_id and dataset_b_id must be different")
    if request.pnl.observations != request.core_result.observations:
        raise ValueError("pnl observations must match core_result observations")
    if request.metrics.observations != request.core_result.observations:
        raise ValueError("metrics observations must match core_result observations")
    if request.sensitivity.base != request.pnl:
        raise ValueError("sensitivity base PnL must match persisted PnL")
    if request.train_window_days <= 0:
        raise ValueError("train_window_days must be positive")
    if request.test_window_days <= 0:
        raise ValueError("test_window_days must be positive")
    if request.num_windows <= 0:
        raise ValueError("num_windows must be positive")


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


def _require_passed_statistical_test(session: Session, *, test_id: UUID) -> None:
    test = (
        session.query(StoredStatisticalTestResult)
        .filter(
            StoredStatisticalTestResult.test_id == str(test_id),
            StoredStatisticalTestResult.passed.is_(True),
        )
        .first()
    )
    if test is None:
        raise ValueError(f"passed statistical test is required for test {test_id}")
