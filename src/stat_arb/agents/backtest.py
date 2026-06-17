"""Backtest Agent registry and memory integration boundary.

This boundary accepts completed backtest results that were built from aligned_timestamps
upstream. It must not accept raw OHLCV pairs or perform alignment itself.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from stat_arb.agents.audit import AgentAuditEvent
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
    ReportArtifact as StoredReportArtifact,
)
from stat_arb.storage.models import (
    StatisticalTestResult as StoredStatisticalTestResult,
)


class MemoryWriter(Protocol):
    """Minimal Memory Agent service protocol used by this boundary."""

    def write(self, request: MemoryWriteRequest) -> object:
        """Write a policy-approved memory record."""


class AuditWriter(Protocol):
    """Minimal append-only audit writer used by this boundary."""

    def append(self, event: AgentAuditEvent) -> object:
        """Append one operator-safe audit event."""


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
    experiment_id: UUID | None = None
    artifact_output_dir: Path | None = None
    series: BacktestSeriesArtifactInput | None = None


@dataclass(frozen=True)
class BacktestSeriesArtifactInput:
    """Chart-ready factual series to persist beside a backtest result."""

    timestamps: tuple[datetime, ...]
    equity_curve: tuple[float, ...]
    drawdown_curve: tuple[float, ...]
    z_scores: tuple[float, ...]
    entry_markers: tuple[int, ...]
    exit_markers: tuple[int, ...]
    rolling_sharpe: tuple[float, ...]
    trade_pnls: tuple[float, ...]


@dataclass(frozen=True)
class BacktestAgentRunResult:
    """Result of a registry-backed Backtest Agent persistence step."""

    stored_result: StoredBacktestResult
    memory_written: bool
    series_artifact: StoredReportArtifact | None = None
    audit_written: bool = False


def run_backtest_agent_persistence(
    request: BacktestAgentInput,
    *,
    session: Session,
    memory_service: MemoryWriter | None = None,
    audit_writer: AuditWriter | None = None,
) -> BacktestAgentRunResult:
    """Persist structured backtest results and write a concise memory summary."""
    _validate_request(request)
    _require_passed_data_quality_reports(
        session,
        dataset_ids=(request.dataset_a_id, request.dataset_b_id),
    )
    _require_passed_statistical_test(
        session,
        test_id=request.test_id,
        hypothesis_id=request.hypothesis_id,
        dataset_a_id=request.dataset_a_id,
        dataset_b_id=request.dataset_b_id,
    )

    stored = _persist_backtest_result(session, request)
    series_artifact = _persist_series_artifact(session, request, stored)
    memory_written = False
    if memory_service is not None:
        memory_service.write(_memory_request_for(stored))
        memory_written = True

    audit_written = False
    if audit_writer is not None:
        audit_writer.append(
            _audit_event_for(
                request=request,
                stored=stored,
                series_artifact=series_artifact,
                memory_written=memory_written,
            )
        )
        audit_written = True

    return BacktestAgentRunResult(
        stored_result=stored,
        memory_written=memory_written,
        series_artifact=series_artifact,
        audit_written=audit_written,
    )


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
        dataset_ids=list(request.reproducibility.dataset_ids),
        random_seed=request.reproducibility.random_seed,
        execution_command=list(request.reproducibility.execution_command),
        run_timestamp=request.reproducibility.run_timestamp,
        lock_file_hash=request.reproducibility.lock_file_hash,
        execution_time_seconds=None,
        train_window_days=request.train_window_days,
        test_window_days=request.test_window_days,
        num_windows=request.num_windows,
        entry_threshold=request.core_result.entry_threshold,
        exit_threshold=request.core_result.exit_threshold,
        hedge_ratio=request.core_result.hedge_ratio,
        risk_exit_policy=_risk_exit_policy_payload(request.core_result),
        risk_exit_policy_disabled_reason=request.core_result.risk_exit_policy_disabled_reason,
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


def _risk_exit_policy_payload(result: BacktestCoreResult) -> dict[str, object] | None:
    if result.exit_policy is None:
        return None
    return {
        "max_holding_bars": result.exit_policy.max_holding_bars,
        "emergency_z_score": result.exit_policy.emergency_z_score,
    }


def _persist_series_artifact(
    session: Session,
    request: BacktestAgentInput,
    stored: StoredBacktestResult,
) -> StoredReportArtifact | None:
    if request.series is None:
        return None
    if request.experiment_id is None or request.artifact_output_dir is None:
        raise ValueError(
            "experiment_id and artifact_output_dir are required when series sidecar is provided"
        )
    _validate_series(request.series, observations=request.core_result.observations)
    output_dir = request.artifact_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"backtest-{stored.backtest_id}.series.json"
    path.write_text(
        json.dumps(
            _series_payload(stored.backtest_id, request.series),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    artifact = StoredReportArtifact(
        experiment_id=str(request.experiment_id),
        artifact_type="backtest_series",
        file_path=str(path),
        format="json",
        created_at=request.reproducibility.run_timestamp,
    )
    session.add(artifact)
    session.flush()
    return artifact


def _validate_series(series: BacktestSeriesArtifactInput, *, observations: int) -> None:
    aligned_lengths = {
        "timestamps": len(series.timestamps),
        "equity_curve": len(series.equity_curve),
        "drawdown_curve": len(series.drawdown_curve),
        "z_scores": len(series.z_scores),
        "rolling_sharpe": len(series.rolling_sharpe),
    }
    mismatched = {
        name: length for name, length in aligned_lengths.items() if length != observations
    }
    if mismatched:
        raise ValueError(f"series lengths must match backtest observations: {mismatched}")
    for marker in (*series.entry_markers, *series.exit_markers):
        if isinstance(marker, bool) or marker < 0 or marker >= observations:
            raise ValueError("series markers must be valid observation indices")


def _series_payload(backtest_id: str, series: BacktestSeriesArtifactInput) -> dict[str, object]:
    return {
        "backtest_id": backtest_id,
        "timestamps": [timestamp.isoformat() for timestamp in series.timestamps],
        "equity_curve": list(series.equity_curve),
        "drawdown_curve": list(series.drawdown_curve),
        "z_scores": list(series.z_scores),
        "entry_markers": list(series.entry_markers),
        "exit_markers": list(series.exit_markers),
        "rolling_sharpe": list(series.rolling_sharpe),
        "trade_pnls": list(series.trade_pnls),
    }


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


def _audit_event_for(
    *,
    request: BacktestAgentInput,
    stored: StoredBacktestResult,
    series_artifact: StoredReportArtifact | None,
    memory_written: bool,
) -> AgentAuditEvent:
    registry_refs = [f"registry:backtest_results/{stored.backtest_id}"]
    if series_artifact is not None:
        registry_refs.append(f"registry:report_artifacts/{series_artifact.artifact_id}")
    return AgentAuditEvent(
        event_id=f"backtest-agent-{stored.backtest_id}",
        agent_name="backtest_agent",
        action="backtest_result_persisted",
        reason=(
            "Backtest result persisted after passed data-quality and statistical-test "
            "prerequisites. Exact metrics, costs, reproducibility hashes, and series "
            "sidecars remain in registry/artifacts."
        ),
        status="completed",
        registry_refs=tuple(registry_refs),
        memory_refs=(f"registry:backtest_results/{stored.backtest_id}",)
        if memory_written
        else (),
        metadata={
            "hypothesis_id": str(request.hypothesis_id),
            "test_id": str(request.test_id),
            "dataset_a_id": str(request.dataset_a_id),
            "dataset_b_id": str(request.dataset_b_id),
            "series_artifact_written": series_artifact is not None,
            "memory_written": memory_written,
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
    if (request.experiment_id is None) != (request.artifact_output_dir is None):
        raise ValueError("experiment_id and artifact_output_dir must be provided together")
    if request.series is None and (
        request.experiment_id is not None or request.artifact_output_dir is not None
    ):
        raise ValueError("series is required when artifact sidecar fields are provided")


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


def _require_passed_statistical_test(
    session: Session,
    *,
    test_id: UUID,
    hypothesis_id: UUID,
    dataset_a_id: UUID,
    dataset_b_id: UUID,
) -> None:
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
    if (
        test.hypothesis_id != str(hypothesis_id)
        or test.dataset_a_id != str(dataset_a_id)
        or test.dataset_b_id != str(dataset_b_id)
    ):
        raise ValueError(
            "statistical test provenance mismatch: test_id must match hypothesis_id, "
            "dataset_a_id, and dataset_b_id"
        )
