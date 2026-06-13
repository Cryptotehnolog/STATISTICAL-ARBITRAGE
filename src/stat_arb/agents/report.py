"""Report Agent registry and memory boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from stat_arb.memory import MemoryRecordType, MemoryWriteRequest
from stat_arb.reports import (
    BacktestReportSnapshot,
    DataQualityReportSnapshot,
    GeneratedReportArtifact,
    ReportSeriesSnapshot,
    generate_backtest_report_artifacts,
)
from stat_arb.storage.models import (
    BacktestResult as StoredBacktestResult,
)
from stat_arb.storage.models import (
    CriticReview as StoredCriticReview,
)
from stat_arb.storage.models import (
    DataQualityReportRecord as StoredDataQualityReportRecord,
)
from stat_arb.storage.models import (
    Experiment as StoredExperiment,
)
from stat_arb.storage.models import (
    ReportArtifact as StoredReportArtifact,
)


@dataclass(frozen=True)
class ReportAgentInput:
    """Input contract for generating registry-backed report artifacts."""

    experiment_id: UUID
    backtest_id: UUID
    output_dir: Path


@dataclass(frozen=True)
class ReportAgentRunResult:
    """Result of one Report Agent artifact generation run."""

    artifacts: tuple[StoredReportArtifact, ...]
    memory_written: bool


class MemoryWriter(Protocol):
    """Minimal Memory Agent service protocol used by this boundary."""

    def write(self, request: MemoryWriteRequest) -> object:
        """Write a policy-approved memory record."""


def run_report_agent(
    request: ReportAgentInput,
    *,
    session: Session,
    memory_service: MemoryWriter | None = None,
) -> ReportAgentRunResult:
    """Generate backtest report artifacts and persist registry links."""
    experiment = _require_experiment(session, experiment_id=request.experiment_id)
    backtest = _require_backtest(session, backtest_id=request.backtest_id)
    if experiment.hypothesis_id != backtest.hypothesis_id:
        raise ValueError("experiment/backtest hypothesis mismatch")

    critic = _latest_critic_review(session, backtest_id=request.backtest_id)
    data_quality_reports = _data_quality_reports_for(session, backtest)
    series = _require_series_sidecar(
        session,
        experiment_id=request.experiment_id,
        backtest_id=request.backtest_id,
    )
    generated = generate_backtest_report_artifacts(
        _snapshot_from(backtest, critic, data_quality_reports, series),
        output_dir=request.output_dir,
    )
    stored = _persist_artifacts(
        session,
        experiment_id=request.experiment_id,
        generated=generated,
    )

    memory_written = False
    if memory_service is not None:
        memory_service.write(_memory_request_for(stored[0], request.backtest_id))
        memory_written = True

    return ReportAgentRunResult(artifacts=stored, memory_written=memory_written)


def _require_experiment(session: Session, *, experiment_id: UUID) -> StoredExperiment:
    experiment = (
        session.query(StoredExperiment)
        .filter(StoredExperiment.experiment_id == str(experiment_id))
        .first()
    )
    if experiment is None:
        raise ValueError(f"experiment is required for report generation {experiment_id}")
    return experiment


def _require_backtest(session: Session, *, backtest_id: UUID) -> StoredBacktestResult:
    backtest = (
        session.query(StoredBacktestResult)
        .filter(StoredBacktestResult.backtest_id == str(backtest_id))
        .first()
    )
    if backtest is None:
        raise ValueError(f"backtest result is required for report generation {backtest_id}")
    return backtest


def _latest_critic_review(session: Session, *, backtest_id: UUID) -> StoredCriticReview | None:
    return (
        session.query(StoredCriticReview)
        .filter(StoredCriticReview.backtest_id == str(backtest_id))
        .order_by(StoredCriticReview.reviewed_at.desc())
        .first()
    )


def _data_quality_reports_for(
    session: Session,
    backtest: StoredBacktestResult,
) -> tuple[StoredDataQualityReportRecord, ...]:
    rows = (
        session.query(StoredDataQualityReportRecord)
        .filter(
            StoredDataQualityReportRecord.dataset_id.in_(
                [backtest.dataset_a_id, backtest.dataset_b_id]
            )
        )
        .order_by(StoredDataQualityReportRecord.symbol.asc())
        .all()
    )
    return tuple(rows)


def _require_series_sidecar(
    session: Session,
    *,
    experiment_id: UUID,
    backtest_id: UUID,
) -> ReportSeriesSnapshot:
    artifacts = (
        session.query(StoredReportArtifact)
        .filter(
            StoredReportArtifact.experiment_id == str(experiment_id),
            StoredReportArtifact.artifact_type == "backtest_series",
            StoredReportArtifact.format == "json",
        )
        .order_by(StoredReportArtifact.created_at.desc())
        .all()
    )
    if not artifacts:
        raise ValueError("matching backtest_series sidecar is required before report generation")
    for artifact in artifacts:
        payload = json.loads(Path(artifact.file_path).read_text(encoding="utf-8"))
        if payload.get("backtest_id") == str(backtest_id):
            return _series_snapshot_from_payload(payload)
    raise ValueError(
        "matching backtest_series sidecar is required before report generation; "
        "backtest_series artifact does not match requested backtest"
    )


def _series_snapshot_from_payload(payload: dict[str, object]) -> ReportSeriesSnapshot:
    return ReportSeriesSnapshot(
        timestamps=tuple(_string_list(payload, "timestamps")),
        equity_curve=tuple(_float_list(payload, "equity_curve")),
        drawdown_curve=tuple(_float_list(payload, "drawdown_curve")),
        z_scores=tuple(_float_list(payload, "z_scores")),
        entry_markers=tuple(_int_list(payload, "entry_markers")),
        exit_markers=tuple(_int_list(payload, "exit_markers")),
        rolling_sharpe=tuple(_float_list(payload, "rolling_sharpe")),
        trade_pnls=tuple(_float_list(payload, "trade_pnls")),
    )


def _snapshot_from(
    backtest: StoredBacktestResult,
    critic: StoredCriticReview | None,
    data_quality_reports: tuple[StoredDataQualityReportRecord, ...],
    series: ReportSeriesSnapshot | None,
) -> BacktestReportSnapshot:
    return BacktestReportSnapshot(
        backtest_id=backtest.backtest_id,
        hypothesis_id=backtest.hypothesis_id,
        net_pnl=backtest.net_pnl,
        gross_pnl=backtest.gross_pnl,
        total_cost=(
            backtest.commission_cost
            + backtest.spread_cost
            + backtest.slippage_cost
            + backtest.funding_cost
            + backtest.borrow_cost
        ),
        sharpe_ratio=backtest.sharpe_ratio,
        sortino_ratio=backtest.sortino_ratio,
        max_drawdown=backtest.max_drawdown,
        win_rate=backtest.win_rate,
        profit_factor=backtest.profit_factor,
        turnover=backtest.turnover,
        num_trades=backtest.num_trades,
        baseline_sharpe=backtest.baseline_sharpe,
        net_pnl_2x_costs=backtest.net_pnl_2x_costs,
        net_pnl_half_costs=backtest.net_pnl_half_costs,
        critic_status=critic.status if critic is not None else None,
        critic_objections=critic.objections if critic is not None else None,
        tested_at=backtest.tested_at,
        data_quality_reports=tuple(
            DataQualityReportSnapshot(
                dataset_id=report.dataset_id,
                symbol=report.symbol,
                timeframe=report.timeframe,
                passed=report.passed,
                quality_score=report.quality_score,
                missing_bars=report.missing_bars,
                duplicate_timestamps=report.duplicate_timestamps,
                outlier_count=report.outlier_count,
                alignment_score=report.alignment_score,
                issues=tuple(str(issue) for issue in (report.issues or [])),
                report_path=report.report_path,
            )
            for report in data_quality_reports
        ),
        series=series,
    )


def _string_list(payload: dict[str, object], key: str) -> list[str]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"backtest_series.{key} must be a list of strings")
    return value


def _float_list(payload: dict[str, object], key: str) -> list[float]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"backtest_series.{key} must be a list")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise ValueError(f"backtest_series.{key} must contain only numbers")
        result.append(float(item))
    return result


def _int_list(payload: dict[str, object], key: str) -> list[int]:
    value = payload.get(key)
    if not isinstance(value, list) or any(
        isinstance(item, bool) or not isinstance(item, int) for item in value
    ):
        raise ValueError(f"backtest_series.{key} must be a list of integers")
    return value


def _persist_artifacts(
    session: Session,
    *,
    experiment_id: UUID,
    generated: tuple[GeneratedReportArtifact, ...],
) -> tuple[StoredReportArtifact, ...]:
    stored = tuple(
        StoredReportArtifact(
            experiment_id=str(experiment_id),
            artifact_type=artifact.artifact_type,
            file_path=str(artifact.file_path),
            format=artifact.format,
            created_at=artifact.created_at,
        )
        for artifact in generated
    )
    session.add_all(stored)
    session.flush()
    return stored


def _memory_request_for(artifact: StoredReportArtifact, backtest_id: UUID) -> MemoryWriteRequest:
    return MemoryWriteRequest(
        record_type=MemoryRecordType.REPORT_SUMMARY,
        title="Backtest report generated",
        body=(
            "Report artifacts were generated. Structured metrics, cost attribution, "
            "critic status, and artifact paths are stored in the registry."
        ),
        source_id=artifact.artifact_id,
        registry_reference=f"registry:report_artifacts/{artifact.artifact_id}",
        tags=["report", "backtest"],
        metadata={
            "backtest_id": str(backtest_id),
            "experiment_id": artifact.experiment_id,
        },
    )
