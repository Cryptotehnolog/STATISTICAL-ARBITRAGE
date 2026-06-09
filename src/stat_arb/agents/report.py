"""Report Agent registry and memory boundary."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from stat_arb.memory import MemoryRecordType, MemoryWriteRequest
from stat_arb.reports import (
    BacktestReportSnapshot,
    GeneratedReportArtifact,
    generate_backtest_report_artifacts,
)
from stat_arb.storage.models import (
    BacktestResult as StoredBacktestResult,
)
from stat_arb.storage.models import (
    CriticReview as StoredCriticReview,
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
    generated = generate_backtest_report_artifacts(
        _snapshot_from(backtest, critic),
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


def _snapshot_from(
    backtest: StoredBacktestResult,
    critic: StoredCriticReview | None,
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
    )


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
