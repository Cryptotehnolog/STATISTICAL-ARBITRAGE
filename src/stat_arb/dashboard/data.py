"""Read-only data boundary for the Streamlit dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from stat_arb.storage import (
    BacktestResult,
    CoordinatorTask,
    CriticReview,
    DataQualityReportRecord,
    Dataset,
    Experiment,
    Hypothesis,
    ReportArtifact,
    StatisticalTestResult,
    get_session,
)
from stat_arb.storage.database import DEFAULT_DB_PATH


@dataclass(frozen=True)
class DashboardNavigationItem:
    """One read-only dashboard navigation target."""

    key: str
    label: str
    description: str
    mode: str = "read_only"


@dataclass(frozen=True)
class DashboardSnapshot:
    """Small registry snapshot for the first dashboard scaffold."""

    registry_path: Path
    counts: dict[str, int]
    experiments: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    statistical_tests: list[dict[str, Any]]
    backtests: list[dict[str, Any]]
    report_artifacts: list[dict[str, Any]]
    logs: list[dict[str, Any]]
    approval_queue: list[dict[str, Any]]


@dataclass(frozen=True)
class DashboardExperimentFilters:
    """Read-only filters for the experiment list view."""

    statuses: tuple[str, ...] = ()
    asset_query: str = ""
    created_from: datetime | date | None = None
    created_to: datetime | date | None = None


@dataclass(frozen=True)
class DashboardExperimentSort:
    """Read-only sort option for the experiment list view."""

    field: str = "created_at"
    descending: bool = True


def get_dashboard_navigation() -> list[DashboardNavigationItem]:
    """Return the initial read-only dashboard navigation model."""
    return [
        DashboardNavigationItem("overview", "Обзор", "Состояние registry и очереди."),
        DashboardNavigationItem("experiments", "Эксперименты", "Lifecycle и активные агенты."),
        DashboardNavigationItem("hypotheses", "Гипотезы", "Кандидаты пар и novelty score."),
        DashboardNavigationItem("stat_tests", "Статтесты", "Cointegration, ADF, hedge ratio."),
        DashboardNavigationItem("backtests", "Бэктесты", "PnL, costs, drawdown и metrics."),
        DashboardNavigationItem("reports", "Отчеты", "Report artifacts из registry."),
        DashboardNavigationItem("memory", "Память", "Готовность ApeRAG и будущий поиск."),
        DashboardNavigationItem(
            "approval", "Очередь одобрения", "Статус будущих approvals только на чтение."
        ),
    ]


def load_dashboard_snapshot(
    db_path: Path | str = DEFAULT_DB_PATH,
    *,
    experiment_filters: DashboardExperimentFilters | None = None,
    experiment_sort: DashboardExperimentSort | None = None,
    experiment_limit: int = 100,
) -> DashboardSnapshot:
    """Load a read-only registry snapshot for dashboard rendering."""
    registry_path = Path(db_path)
    experiment_filters = experiment_filters or DashboardExperimentFilters()
    experiment_sort = experiment_sort or DashboardExperimentSort()
    if not registry_path.exists():
        return DashboardSnapshot(
            registry_path=registry_path,
            counts=_empty_counts(),
            experiments=[],
            hypotheses=[],
            statistical_tests=[],
            backtests=[],
            report_artifacts=[],
            logs=[],
            approval_queue=[],
        )

    with get_session(db_path=registry_path) as session:
        counts = {
            "hypotheses": session.query(Hypothesis).count(),
            "datasets": session.query(Dataset).count(),
            "quality_reports": session.query(DataQualityReportRecord).count(),
            "statistical_tests": session.query(StatisticalTestResult).count(),
            "backtests": session.query(BacktestResult).count(),
            "critic_reviews": session.query(CriticReview).count(),
            "experiments": session.query(Experiment).count(),
            "coordinator_tasks": session.query(CoordinatorTask).count(),
            "report_artifacts": session.query(ReportArtifact).count(),
        }

        experiment_query = select(Experiment, Hypothesis).join(
            Hypothesis, Experiment.hypothesis_id == Hypothesis.hypothesis_id
        )
        if experiment_filters.statuses:
            experiment_query = experiment_query.where(
                Experiment.status.in_(experiment_filters.statuses)
            )
        asset_query = experiment_filters.asset_query.strip().lower()
        if asset_query:
            experiment_query = experiment_query.where(
                (Hypothesis.asset_a.ilike(f"%{asset_query}%"))
                | (Hypothesis.asset_b.ilike(f"%{asset_query}%"))
            )
        if experiment_filters.created_from is not None:
            experiment_query = experiment_query.where(
                Experiment.created_at >= _as_datetime(experiment_filters.created_from, end=False)
            )
        if experiment_filters.created_to is not None:
            experiment_query = experiment_query.where(
                Experiment.created_at <= _as_datetime(experiment_filters.created_to, end=True)
            )
        experiment_rows = session.execute(experiment_query).all()
        hypothesis_rows = list(
            session.execute(select(Hypothesis).order_by(Hypothesis.created_at.desc()).limit(100))
            .scalars()
            .all()
        )

        experiments = [
            _experiment_row(session, experiment=experiment, hypothesis=hypothesis)
            for experiment, hypothesis in experiment_rows
        ]
        experiments = _sort_experiments(experiments, experiment_sort)[:experiment_limit]
        hypotheses = [_hypothesis_row(session, hypothesis) for hypothesis in hypothesis_rows]
        statistical_tests = [
            _statistical_test_row(session, row)
            for row in _latest_rows(session, StatisticalTestResult, StatisticalTestResult.tested_at)
        ]
        backtests = [
            _backtest_row(session, row)
            for row in _latest_rows(session, BacktestResult, BacktestResult.tested_at)
        ]
        report_artifacts = [
            _report_artifact_row(row)
            for row in _latest_rows(session, ReportArtifact, ReportArtifact.created_at)
        ]
        logs = [
            _coordinator_log_row(row)
            for row in _latest_rows(session, CoordinatorTask, CoordinatorTask.created_at)
            if row.last_error or row.status in {"failed", "retry_pending"}
        ]
        approval_queue = _approval_queue_rows(session)

    return DashboardSnapshot(
        registry_path=registry_path,
        counts=counts,
        experiments=experiments,
        hypotheses=hypotheses,
        statistical_tests=statistical_tests,
        backtests=backtests,
        report_artifacts=report_artifacts,
        logs=logs,
        approval_queue=approval_queue,
    )


def _empty_counts() -> dict[str, int]:
    return {
        "hypotheses": 0,
        "datasets": 0,
        "quality_reports": 0,
        "statistical_tests": 0,
        "backtests": 0,
        "critic_reviews": 0,
        "experiments": 0,
        "coordinator_tasks": 0,
        "report_artifacts": 0,
    }


def _latest_rows(
    session: Session, model: type[Any], ordering: Any, *, limit: int = 100
) -> list[Any]:
    return list(
        session.execute(select(model).order_by(ordering.desc()).limit(limit)).scalars().all()
    )


def _hypothesis_row(session: Session, hypothesis: Hypothesis) -> dict[str, Any]:
    related_experiments = (
        session.query(Experiment)
        .filter(Experiment.hypothesis_id == hypothesis.hypothesis_id)
        .count()
    )
    raw_similar = hypothesis.similar_hypotheses
    similar: list[Any] = raw_similar if isinstance(raw_similar, list) else []
    unique_similar = sorted({str(item) for item in similar})
    return {
        "hypothesis_id": hypothesis.hypothesis_id,
        "pair": f"{hypothesis.asset_a} / {hypothesis.asset_b}",
        "asset_a": hypothesis.asset_a,
        "asset_b": hypothesis.asset_b,
        "status": hypothesis.status,
        "novelty_score": hypothesis.novelty_score,
        "source": hypothesis.source,
        "created_by": hypothesis.created_by,
        "similar_hypotheses_count": len(unique_similar),
        "similar_hypotheses": ", ".join(unique_similar),
        "related_experiments": related_experiments,
        "created_at": hypothesis.created_at.isoformat(),
    }


def _hypothesis_for(session: Session, hypothesis_id: str) -> Hypothesis | None:
    return (
        session.execute(
            select(Hypothesis).where(Hypothesis.hypothesis_id == hypothesis_id).limit(1)
        )
        .scalars()
        .first()
    )


def _pair_for(session: Session, hypothesis_id: str) -> str:
    hypothesis = _hypothesis_for(session, hypothesis_id)
    if hypothesis is None:
        return hypothesis_id
    return f"{hypothesis.asset_a} / {hypothesis.asset_b}"


def _statistical_test_row(session: Session, result: StatisticalTestResult) -> dict[str, Any]:
    return {
        "test_id": result.test_id,
        "hypothesis_id": result.hypothesis_id,
        "pair": _pair_for(session, result.hypothesis_id),
        "passed": result.passed,
        "cointegration_p_value": result.cointegration_p_value,
        "adf_p_value": result.adf_p_value,
        "hedge_ratio": result.hedge_ratio,
        "hedge_ratio_r_squared": result.hedge_ratio_r_squared,
        "half_life_days": result.half_life_days,
        "regime_changes_detected": result.regime_changes_detected,
        "rejection_reason": result.rejection_reason,
        "tested_at": result.tested_at.isoformat(),
    }


def _backtest_row(session: Session, result: BacktestResult) -> dict[str, Any]:
    total_cost = (
        result.commission_cost
        + result.spread_cost
        + result.slippage_cost
        + result.funding_cost
        + result.borrow_cost
    )
    experiment_ids = [
        experiment_id
        for (experiment_id,) in session.execute(
            select(Experiment.experiment_id).where(Experiment.hypothesis_id == result.hypothesis_id)
        ).all()
    ]
    has_series_sidecar = False
    if experiment_ids:
        artifacts = session.execute(
            select(ReportArtifact).where(
                ReportArtifact.experiment_id.in_(experiment_ids),
                ReportArtifact.artifact_type == "backtest_series",
            )
        ).scalars()
        has_series_sidecar = any(result.backtest_id in artifact.file_path for artifact in artifacts)
    return {
        "backtest_id": result.backtest_id,
        "hypothesis_id": result.hypothesis_id,
        "test_id": result.test_id,
        "pair": _pair_for(session, result.hypothesis_id),
        "gross_pnl": result.gross_pnl,
        "net_pnl": result.net_pnl,
        "commission_cost": result.commission_cost,
        "spread_cost": result.spread_cost,
        "slippage_cost": result.slippage_cost,
        "funding_cost": result.funding_cost,
        "borrow_cost": result.borrow_cost,
        "total_cost": total_cost,
        "num_trades": result.num_trades,
        "turnover": result.turnover,
        "avg_holding_time_hours": result.avg_holding_time_hours,
        "sharpe_ratio": result.sharpe_ratio,
        "sortino_ratio": result.sortino_ratio,
        "max_drawdown": result.max_drawdown,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "has_series_sidecar": has_series_sidecar,
        "tested_at": result.tested_at.isoformat(),
    }


def _report_artifact_row(artifact: ReportArtifact) -> dict[str, Any]:
    return {
        "artifact_id": artifact.artifact_id,
        "experiment_id": artifact.experiment_id,
        "artifact_type": artifact.artifact_type,
        "format": artifact.format,
        "file_path": artifact.file_path,
        "created_at": artifact.created_at.isoformat(),
    }


def _coordinator_log_row(task: CoordinatorTask) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "experiment_id": task.experiment_id,
        "task_type": task.task_type,
        "agent_name": task.agent_name,
        "status": task.status,
        "attempts": f"{task.attempt_count}/{task.max_attempts}",
        "last_error": task.last_error,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def _approval_queue_rows(session: Session) -> list[dict[str, Any]]:
    rows = session.execute(
        select(Experiment, Hypothesis)
        .join(Hypothesis, Experiment.hypothesis_id == Hypothesis.hypothesis_id)
        .where(
            (Experiment.critic_approved.is_(True))
            | (Experiment.status.in_(("reporting", "final_decision")))
        )
        .order_by(Experiment.created_at.desc())
        .limit(100)
    ).all()
    return [
        {
            "experiment_id": experiment.experiment_id,
            "hypothesis_id": hypothesis.hypothesis_id,
            "pair": f"{hypothesis.asset_a} / {hypothesis.asset_b}",
            "status": experiment.status,
            "current_agent": experiment.current_agent,
            "critic_approved": experiment.critic_approved,
            "final_decision": experiment.final_decision,
            "rejection_reason": experiment.rejection_reason,
            "created_at": experiment.created_at.isoformat(),
        }
        for experiment, hypothesis in rows
    ]


def _experiment_row(
    session: Session, *, experiment: Experiment, hypothesis: Hypothesis
) -> dict[str, Any]:
    latest_test = (
        session.execute(
            select(StatisticalTestResult)
            .where(StatisticalTestResult.hypothesis_id == hypothesis.hypothesis_id)
            .order_by(StatisticalTestResult.tested_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    latest_backtest = (
        session.execute(
            select(BacktestResult)
            .where(BacktestResult.hypothesis_id == hypothesis.hypothesis_id)
            .order_by(BacktestResult.tested_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    latest_critic = (
        session.execute(
            select(CriticReview)
            .join(BacktestResult, CriticReview.backtest_id == BacktestResult.backtest_id)
            .where(BacktestResult.hypothesis_id == hypothesis.hypothesis_id)
            .order_by(CriticReview.reviewed_at.desc())
            .limit(1)
        )
        .scalars()
        .first()
    )
    return {
        "experiment_id": experiment.experiment_id,
        "hypothesis_id": hypothesis.hypothesis_id,
        "status": experiment.status,
        "current_agent": experiment.current_agent,
        "final_decision": experiment.final_decision,
        "pair": f"{hypothesis.asset_a} / {hypothesis.asset_b}",
        "asset_a": hypothesis.asset_a,
        "asset_b": hypothesis.asset_b,
        "hypothesis_status": hypothesis.status,
        "novelty_score": hypothesis.novelty_score,
        "data_quality_passed": experiment.data_quality_passed,
        "statistical_tests_passed": experiment.statistical_tests_passed,
        "backtest_completed": experiment.backtest_completed,
        "critic_approved": experiment.critic_approved,
        "latest_test_id": latest_test.test_id if latest_test else None,
        "latest_cointegration_p_value": latest_test.cointegration_p_value if latest_test else None,
        "latest_hedge_ratio": latest_test.hedge_ratio if latest_test else None,
        "latest_half_life_days": latest_test.half_life_days if latest_test else None,
        "latest_backtest_id": latest_backtest.backtest_id if latest_backtest else None,
        "latest_net_pnl": latest_backtest.net_pnl if latest_backtest else None,
        "latest_sharpe_ratio": latest_backtest.sharpe_ratio if latest_backtest else None,
        "latest_max_drawdown": latest_backtest.max_drawdown if latest_backtest else None,
        "latest_critic_status": latest_critic.status if latest_critic else None,
        "created_at": experiment.created_at.isoformat(),
    }


def _sort_experiments(
    rows: list[dict[str, Any]], sort: DashboardExperimentSort
) -> list[dict[str, Any]]:
    allowed_fields = {
        "created_at",
        "status",
        "pair",
        "novelty_score",
        "cointegration_p_value",
        "net_pnl",
        "sharpe_ratio",
        "max_drawdown",
    }
    if sort.field not in allowed_fields:
        raise ValueError(f"Unsupported dashboard experiment sort field: {sort.field}")
    field_by_alias = {
        "cointegration_p_value": "latest_cointegration_p_value",
        "net_pnl": "latest_net_pnl",
        "sharpe_ratio": "latest_sharpe_ratio",
        "max_drawdown": "latest_max_drawdown",
    }
    actual_field = field_by_alias.get(sort.field, sort.field)

    def sort_key(row: dict[str, Any]) -> tuple[bool, Any]:
        value = row.get(actual_field)
        return value is None, value

    return sorted(rows, key=sort_key, reverse=sort.descending)


def _as_datetime(value: datetime | date, *, end: bool) -> datetime:
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    boundary_time = time.max if end else time.min
    return datetime.combine(value, boundary_time)
