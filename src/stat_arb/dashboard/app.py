"""Streamlit entrypoint for the read-only Statistical Arbitrage dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from stat_arb.dashboard.data import (
    DashboardSnapshot,
    get_dashboard_navigation,
    load_dashboard_snapshot,
)

_COLUMN_LABELS = {
    "experiment_id": "Experiment ID",
    "hypothesis_id": "Hypothesis ID",
    "status": "Статус",
    "current_agent": "Текущий агент",
    "final_decision": "Финальное решение",
    "pair": "Пара",
    "data_quality_passed": "Data quality пройдена",
    "statistical_tests_passed": "Статтесты пройдены",
    "backtest_completed": "Бэктест завершен",
    "critic_approved": "Critic одобрил",
    "novelty_score": "Novelty score",
    "source": "Источник",
    "created_by": "Создано",
    "created_at": "Создано в",
}


def main() -> None:
    """Render the dashboard shell."""
    st.set_page_config(
        page_title="Statistical Arbitrage Dashboard",
        page_icon="SA",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_style()

    st.title("Statistical Arbitrage")
    st.caption("Dashboard только на чтение для мониторинга registry и просмотра reports.")

    registry_path = Path(
        st.sidebar.text_input("Путь к registry", value="data/registry.db", help="Файл SQLite registry.")
    )
    snapshot = load_dashboard_snapshot(registry_path)

    st.sidebar.markdown("### Навигация")
    selected = st.sidebar.radio(
        "Раздел",
        options=[item.key for item in get_dashboard_navigation()],
        format_func=lambda key: next(item.label for item in get_dashboard_navigation() if item.key == key),
        label_visibility="collapsed",
    )
    st.sidebar.info("Текущий dashboard работает только на чтение. Запуск stages и approvals пока отключен.")

    _render_overview(snapshot.counts, snapshot.registry_path)

    if selected == "overview":
        _render_overview_details(snapshot)
    elif selected == "experiments":
        _render_table("Эксперименты", snapshot.experiments)
    elif selected == "hypotheses":
        _render_table("Гипотезы", snapshot.hypotheses)
    else:
        item = next(item for item in get_dashboard_navigation() if item.key == selected)
        _render_placeholder(item.label, item.description)


def _render_overview(counts: dict[str, int], registry_path: Path) -> None:
    st.markdown("### Снимок registry")
    st.caption(f"Источник: `{registry_path}`")
    columns = st.columns(4)
    metrics = [
        ("Эксперименты", counts["experiments"]),
        ("Гипотезы", counts["hypotheses"]),
        ("Бэктесты", counts["backtests"]),
        ("Отчеты", counts["report_artifacts"]),
    ]
    for column, (label, value) in zip(columns, metrics, strict=True):
        with column:
            st.metric(label, value)


def _render_overview_details(snapshot: DashboardSnapshot) -> None:
    left, right = st.columns(2)
    with left:
        _render_table("Последние эксперименты", snapshot.experiments)
    with right:
        _render_table("Последние гипотезы", snapshot.hypotheses)


def _render_table(title: str, rows: list[dict[str, object]]) -> None:
    st.markdown(f"### {title}")
    if not rows:
        st.info("В registry пока нет данных для этого раздела.")
        return
    table = pd.DataFrame(rows).rename(columns=_COLUMN_LABELS)
    st.dataframe(table, use_container_width=True, hide_index=True)


def _render_placeholder(title: str, description: str) -> None:
    st.markdown(f"### {title}")
    st.info(f"{description} Этот раздел пока доступен как read-only заготовка для Task 16.1.")


def _inject_style() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stMetric"] {
            border: 1px solid #d9e1ea;
            border-radius: 6px;
            padding: 0.75rem 0.9rem;
            background: #f8fafc;
        }
        section[data-testid="stSidebar"] {
            border-right: 1px solid #d9e1ea;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
