"""Streamlit entrypoint for the read-only Statistical Arbitrage dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from stat_arb.dashboard.data import (
    DashboardExperimentFilters,
    DashboardExperimentSort,
    DashboardSnapshot,
    get_dashboard_navigation,
    load_dashboard_snapshot,
)

_COLUMN_LABELS = {
    "experiment_id": "ID эксперимента",
    "hypothesis_id": "ID гипотезы",
    "status": "Статус",
    "current_agent": "Текущий агент",
    "final_decision": "Финальное решение",
    "pair": "Пара",
    "asset_a": "Актив A",
    "asset_b": "Актив B",
    "hypothesis_status": "Статус гипотезы",
    "data_quality_passed": "Data quality пройдена",
    "statistical_tests_passed": "Статтесты пройдены",
    "backtest_completed": "Бэктест завершен",
    "critic_approved": "Critic одобрил",
    "novelty_score": "Novelty score",
    "latest_test_id": "Последний stat test",
    "latest_cointegration_p_value": "Cointegration p-value",
    "latest_hedge_ratio": "Hedge ratio",
    "latest_half_life_days": "Half-life, дни",
    "latest_backtest_id": "Последний бэктест",
    "latest_net_pnl": "Net PnL",
    "latest_sharpe_ratio": "Sharpe",
    "latest_max_drawdown": "Max drawdown",
    "latest_critic_status": "Статус Critic",
    "source": "Источник",
    "created_by": "Создано",
    "created_at": "Создано в",
}

_EXPERIMENT_STATUS_OPTIONS = [
    "new",
    "data_validation",
    "statistical_testing",
    "backtesting",
    "critic_review",
    "reporting",
    "final_decision",
]

_EXPERIMENT_SORT_OPTIONS = {
    "Дата создания": "created_at",
    "Статус": "status",
    "Пара": "pair",
    "Novelty score": "novelty_score",
    "Cointegration p-value": "cointegration_p_value",
    "Net PnL": "net_pnl",
    "Sharpe": "sharpe_ratio",
    "Max drawdown": "max_drawdown",
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
    st.caption("Dashboard только на чтение для мониторинга registry и просмотра отчетов.")

    registry_path = Path(
        st.sidebar.text_input("Путь к registry", value="data/registry.db", help="Файл SQLite registry.")
    )
    st.sidebar.markdown("### Навигация")
    selected = st.sidebar.radio(
        "Раздел",
        options=[item.key for item in get_dashboard_navigation()],
        format_func=lambda key: next(item.label for item in get_dashboard_navigation() if item.key == key),
        label_visibility="collapsed",
    )
    st.sidebar.info("Текущий dashboard работает только на чтение. Запуск stages и approvals пока отключен.")
    experiment_filters, experiment_sort = _experiment_controls() if selected == "experiments" else (
        DashboardExperimentFilters(),
        DashboardExperimentSort(),
    )
    snapshot = load_dashboard_snapshot(
        registry_path,
        experiment_filters=experiment_filters,
        experiment_sort=experiment_sort,
    )

    _render_overview(snapshot.counts, snapshot.registry_path)

    if selected == "overview":
        _render_overview_details(snapshot)
    elif selected == "experiments":
        _render_experiment_list(snapshot)
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


def _experiment_controls() -> tuple[DashboardExperimentFilters, DashboardExperimentSort]:
    st.sidebar.markdown("### Фильтры экспериментов")
    statuses = st.sidebar.multiselect(
        "Статусы",
        options=_EXPERIMENT_STATUS_OPTIONS,
        default=[],
        help="Пустой выбор показывает все статусы.",
    )
    asset_query = st.sidebar.text_input("Актив", value="", placeholder="BTC, ETH, SOL")
    date_range = st.sidebar.date_input("Дата создания", value=[], format="YYYY-MM-DD")
    sort_label = st.sidebar.selectbox("Сортировка", options=list(_EXPERIMENT_SORT_OPTIONS), index=0)
    descending = st.sidebar.toggle("Сначала большие/новые", value=True)
    created_from = date_range[0] if isinstance(date_range, tuple) and len(date_range) >= 1 else None
    created_to = date_range[1] if isinstance(date_range, tuple) and len(date_range) >= 2 else None
    return (
        DashboardExperimentFilters(
            statuses=tuple(statuses),
            asset_query=asset_query,
            created_from=created_from,
            created_to=created_to,
        ),
        DashboardExperimentSort(
            field=_EXPERIMENT_SORT_OPTIONS[sort_label],
            descending=descending,
        ),
    )


def _render_experiment_list(snapshot: DashboardSnapshot) -> None:
    st.markdown("### Эксперименты")
    st.caption("Список только на чтение: lifecycle, гипотезы и последние результаты из registry.")
    if not snapshot.experiments:
        st.info("Эксперименты не найдены. Проверьте фильтры или наличие записей в registry.")
        return

    status_counts: dict[str, int] = {}
    for row in snapshot.experiments:
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    columns = st.columns(min(4, max(1, len(status_counts))))
    for column, (status, count) in zip(columns, status_counts.items(), strict=False):
        with column:
            st.metric(status, count)

    visible_columns = [
        "experiment_id",
        "pair",
        "status",
        "current_agent",
        "final_decision",
        "latest_cointegration_p_value",
        "latest_net_pnl",
        "latest_sharpe_ratio",
        "latest_max_drawdown",
        "latest_critic_status",
        "created_at",
    ]
    table = pd.DataFrame(snapshot.experiments)
    table = table[[column for column in visible_columns if column in table.columns]]
    st.dataframe(
        table.rename(columns=_COLUMN_LABELS),
        use_container_width=True,
        hide_index=True,
    )


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
