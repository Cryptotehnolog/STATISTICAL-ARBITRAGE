"""Streamlit-free dashboard presentation helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd

COLUMN_LABELS: dict[str, str] = {
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


def dashboard_column_label(column: str) -> str:
    """Return the human-facing dashboard label for one registry column."""
    return COLUMN_LABELS.get(column, column)


def dashboard_column_labels() -> dict[str, str]:
    """Return a copy of dashboard column labels for DataFrame renaming."""
    return dict(COLUMN_LABELS)


def dashboard_visible_columns(table: pd.DataFrame, requested_columns: list[str]) -> list[str]:
    """Return requested columns that are present in the DataFrame."""
    return [column for column in requested_columns if column in table.columns]


def dashboard_numeric_mean(table: pd.DataFrame, column: str) -> float:
    """Return a rounded numeric mean for dashboard metric cards."""
    if column not in table.columns or table.empty:
        return 0.0
    return round(float(table[column].fillna(0.0).mean()), 4)


def dashboard_metric_value(value: object) -> int | float | str | None:
    """Normalize a metric value to Streamlit-compatible scalar text."""
    if value is None or isinstance(value, (int, float, str)):
        return value
    return str(value)
