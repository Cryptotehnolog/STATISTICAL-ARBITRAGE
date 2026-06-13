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
    "similar_hypotheses_count": "Похожие гипотезы",
    "similar_hypotheses": "Ссылки на похожие",
    "related_experiments": "Эксперименты",
    "test_id": "ID stat test",
    "passed": "Пройден",
    "cointegration_p_value": "Cointegration p-value",
    "adf_p_value": "ADF p-value",
    "hedge_ratio": "Hedge ratio",
    "hedge_ratio_r_squared": "Hedge R2",
    "half_life_days": "Half-life, дни",
    "regime_changes_detected": "Regime changes",
    "rejection_reason": "Причина отклонения",
    "tested_at": "Проверено в",
    "backtest_id": "ID бэктеста",
    "gross_pnl": "Gross PnL",
    "net_pnl": "Net PnL",
    "commission_cost": "Commission",
    "spread_cost": "Spread",
    "slippage_cost": "Slippage",
    "funding_cost": "Funding",
    "borrow_cost": "Borrow",
    "total_cost": "Total cost",
    "num_trades": "Сделки",
    "turnover": "Turnover",
    "avg_holding_time_hours": "Среднее удержание, ч",
    "sortino_ratio": "Sortino",
    "win_rate": "Win rate",
    "profit_factor": "Profit factor",
    "has_series_sidecar": "Series sidecar",
    "artifact_id": "ID artifact",
    "artifact_type": "Тип artifact",
    "format": "Формат",
    "file_path": "Путь",
    "task_id": "ID задачи",
    "task_type": "Тип задачи",
    "agent_name": "Агент",
    "attempts": "Попытки",
    "last_error": "Ошибка",
    "started_at": "Начато в",
    "completed_at": "Завершено в",
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
        st.sidebar.text_input(
            "Путь к registry", value="data/registry.db", help="Файл SQLite registry."
        )
    )
    st.sidebar.markdown("### Навигация")
    selected = st.sidebar.radio(
        "Раздел",
        options=[item.key for item in get_dashboard_navigation()],
        format_func=lambda key: next(
            item.label for item in get_dashboard_navigation() if item.key == key
        ),
        label_visibility="collapsed",
    )
    st.sidebar.info(
        "Текущий dashboard работает только на чтение. Запуск stages и approvals пока отключен."
    )
    experiment_filters, experiment_sort = (
        _experiment_controls()
        if selected == "experiments"
        else (
            DashboardExperimentFilters(),
            DashboardExperimentSort(),
        )
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
        _render_hypothesis_status(snapshot)
    elif selected == "stat_tests":
        _render_statistical_tests(snapshot)
    elif selected == "backtests":
        _render_backtests(snapshot)
    elif selected == "reports":
        _render_reports(snapshot)
    elif selected == "memory":
        _render_memory_search(snapshot)
    elif selected == "approval":
        _render_approval_queue(snapshot)
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


def _render_hypothesis_status(snapshot: DashboardSnapshot) -> None:
    st.markdown("### Гипотезы")
    st.caption("Статусы гипотез, novelty score и Похожие гипотезы из registry.")
    if not snapshot.hypotheses:
        st.info("Гипотезы пока не найдены.")
        return
    table = pd.DataFrame(snapshot.hypotheses)
    _render_metric_strip(
        [
            ("Всего гипотез", len(table)),
            ("Средний novelty score", _mean_or_zero(table, "novelty_score")),
            ("С похожими", int((table["similar_hypotheses_count"] > 0).sum())),
        ]
    )
    visible_columns = [
        "hypothesis_id",
        "pair",
        "status",
        "novelty_score",
        "similar_hypotheses_count",
        "similar_hypotheses",
        "related_experiments",
        "source",
        "created_at",
    ]
    _render_dataframe(table, visible_columns)


def _render_statistical_tests(snapshot: DashboardSnapshot) -> None:
    st.markdown("### Результаты stat tests")
    st.caption("Cointegration p-value, ADF p-value, hedge ratio, half-life и regime checks.")
    if not snapshot.statistical_tests:
        st.info("Stat test results пока не найдены.")
        return
    table = pd.DataFrame(snapshot.statistical_tests)
    _render_metric_strip(
        [
            ("Всего tests", len(table)),
            ("Пройдено", int(table["passed"].sum())),
            ("Средний hedge ratio", _mean_or_zero(table, "hedge_ratio")),
        ]
    )
    visible_columns = [
        "test_id",
        "pair",
        "passed",
        "cointegration_p_value",
        "adf_p_value",
        "hedge_ratio",
        "hedge_ratio_r_squared",
        "half_life_days",
        "regime_changes_detected",
        "rejection_reason",
        "tested_at",
    ]
    _render_dataframe(table, visible_columns)


def _render_backtests(snapshot: DashboardSnapshot) -> None:
    st.markdown("### Бэктесты")
    st.caption("Performance metrics, Cost attribution и готовность factual series sidecars.")
    if not snapshot.backtests:
        st.info("Backtest results пока не найдены.")
        return
    table = pd.DataFrame(snapshot.backtests)
    _render_metric_strip(
        [
            ("Всего бэктестов", len(table)),
            ("Средний Net PnL", _mean_or_zero(table, "net_pnl")),
            ("Series sidecars", int(table["has_series_sidecar"].sum())),
        ]
    )
    cost_columns = [
        "commission_cost",
        "spread_cost",
        "slippage_cost",
        "funding_cost",
        "borrow_cost",
    ]
    cost_frame = table[cost_columns].sum().rename(index=_COLUMN_LABELS)
    st.markdown("#### Cost attribution")
    st.bar_chart(cost_frame)
    visible_columns = [
        "backtest_id",
        "pair",
        "net_pnl",
        "gross_pnl",
        "total_cost",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown",
        "win_rate",
        "profit_factor",
        "turnover",
        "num_trades",
        "has_series_sidecar",
        "tested_at",
    ]
    _render_dataframe(table, visible_columns)
    if not bool(table["has_series_sidecar"].any()):
        st.warning("Equity/drawdown charts скрыты: нет matching backtest_series sidecar.")


def _render_reports(snapshot: DashboardSnapshot) -> None:
    st.markdown("### Отчеты")
    st.caption("Report artifacts и visualization sidecars, зарегистрированные в registry.")
    _render_table("Report artifacts", snapshot.report_artifacts)
    if snapshot.logs:
        _render_table("Журнал ошибок", snapshot.logs)


def _render_memory_search(snapshot: DashboardSnapshot) -> None:
    st.markdown("### Поиск по памяти")
    st.caption("Read-only boundary для будущего ApeRAG search через Memory Agent policy.")
    left, right = st.columns([2, 1])
    with left:
        st.text_input("Запрос", placeholder="topic, entity или relationship", disabled=True)
    with right:
        st.selectbox("Тип поиска", options=["topic", "entity", "relationship"], disabled=True)
    st.info(
        "Прямой ApeRAG-запрос из dashboard отключен. Поиск будет подключен через "
        "отдельный read-only Memory Agent boundary, чтобы UI не обходил policy слой."
    )
    _render_metric_strip(
        [
            ("ApeRAG backend", "active"),
            ("Registry artifacts", snapshot.counts["report_artifacts"]),
            ("Memory writes", "через policy"),
        ]
    )


def _render_approval_queue(snapshot: DashboardSnapshot) -> None:
    st.markdown("### Очередь одобрения")
    st.caption("Эксперименты, готовые к human review. Кнопки approve/reject отключены.")
    if not snapshot.approval_queue:
        st.info("Очередь одобрения пуста.")
        return
    st.warning(
        "Approve/reject мутации намеренно не встроены в dashboard: решение должно идти "
        "через audited Coordinator boundary с reason input и registry transition."
    )
    visible_columns = [
        "experiment_id",
        "pair",
        "status",
        "current_agent",
        "critic_approved",
        "final_decision",
        "rejection_reason",
        "created_at",
    ]
    _render_dataframe(pd.DataFrame(snapshot.approval_queue), visible_columns)


def _render_table(title: str, rows: list[dict[str, object]]) -> None:
    st.markdown(f"### {title}")
    if not rows:
        st.info("В registry пока нет данных для этого раздела.")
        return
    table = pd.DataFrame(rows).rename(columns=_COLUMN_LABELS)
    st.dataframe(table, use_container_width=True, hide_index=True)


def _render_dataframe(table: pd.DataFrame, visible_columns: list[str]) -> None:
    columns = [column for column in visible_columns if column in table.columns]
    st.dataframe(
        table[columns].rename(columns=_COLUMN_LABELS),
        use_container_width=True,
        hide_index=True,
    )


def _render_metric_strip(metrics: list[tuple[str, object]]) -> None:
    columns = st.columns(min(4, max(1, len(metrics))))
    for column, (label, value) in zip(columns, metrics, strict=False):
        with column:
            st.metric(label, _metric_value(value))


def _mean_or_zero(table: pd.DataFrame, column: str) -> float:
    if column not in table.columns or table.empty:
        return 0.0
    return round(float(table[column].fillna(0.0).mean()), 4)


def _metric_value(value: object) -> int | float | str | None:
    if value is None or isinstance(value, (int, float, str)):
        return value
    return str(value)


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
