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
        DashboardNavigationItem("approval", "Очередь одобрения", "Статус будущих approvals только на чтение."),
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
        hypothesis_rows = session.execute(
            select(Hypothesis).order_by(Hypothesis.created_at.desc()).limit(25)
        ).scalars()

        experiments = [
            _experiment_row(session, experiment=experiment, hypothesis=hypothesis)
            for experiment, hypothesis in experiment_rows
        ]
        experiments = _sort_experiments(experiments, experiment_sort)[:experiment_limit]
        hypotheses = [
            {
                "hypothesis_id": hypothesis.hypothesis_id,
                "pair": f"{hypothesis.asset_a} / {hypothesis.asset_b}",
                "status": hypothesis.status,
                "novelty_score": hypothesis.novelty_score,
                "source": hypothesis.source,
                "created_by": hypothesis.created_by,
                "created_at": hypothesis.created_at.isoformat(),
            }
            for hypothesis in hypothesis_rows
        ]

    return DashboardSnapshot(
        registry_path=registry_path,
        counts=counts,
        experiments=experiments,
        hypotheses=hypotheses,
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
