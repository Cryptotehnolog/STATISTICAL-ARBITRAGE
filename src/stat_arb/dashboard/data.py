"""Read-only data boundary for the Streamlit dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select

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


def load_dashboard_snapshot(db_path: Path | str = DEFAULT_DB_PATH) -> DashboardSnapshot:
    """Load a read-only registry snapshot for dashboard rendering."""
    registry_path = Path(db_path)
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

        experiment_rows = session.execute(
            select(Experiment, Hypothesis)
            .join(Hypothesis, Experiment.hypothesis_id == Hypothesis.hypothesis_id)
            .order_by(Experiment.created_at.desc())
            .limit(25)
        ).all()
        hypothesis_rows = session.execute(
            select(Hypothesis).order_by(Hypothesis.created_at.desc()).limit(25)
        ).scalars()

        experiments = [
            {
                "experiment_id": experiment.experiment_id,
                "status": experiment.status,
                "current_agent": experiment.current_agent,
                "final_decision": experiment.final_decision,
                "pair": f"{hypothesis.asset_a} / {hypothesis.asset_b}",
                "data_quality_passed": experiment.data_quality_passed,
                "statistical_tests_passed": experiment.statistical_tests_passed,
                "backtest_completed": experiment.backtest_completed,
                "critic_approved": experiment.critic_approved,
                "created_at": experiment.created_at.isoformat(),
            }
            for experiment, hypothesis in experiment_rows
        ]
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
