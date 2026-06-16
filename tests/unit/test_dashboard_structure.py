from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import pytest

from stat_arb.dashboard.data import (
    DashboardExperimentFilters,
    DashboardExperimentSort,
    DashboardMemorySearchRequest,
    get_dashboard_navigation,
    load_dashboard_snapshot,
    run_dashboard_memory_search,
)
from stat_arb.dashboard.presentation import (
    dashboard_column_label,
    dashboard_metric_value,
    dashboard_numeric_mean,
    dashboard_visible_columns,
)
from stat_arb.memory import (
    ApeRAGGraphSummary,
    ApeRAGSearchResult,
    MemoryQueryRequest,
    MemoryQueryResult,
)
from stat_arb.storage import (
    BacktestResult,
    CoordinatorTask,
    CriticReview,
    Dataset,
    Experiment,
    Hypothesis,
    ReportArtifact,
    StatisticalTestResult,
    init_database,
)
from stat_arb.storage.database import create_session_factory


def test_load_dashboard_snapshot_reads_registry_without_mutation(tmp_path) -> None:
    """Dashboard snapshot should expose registry counts without changing records."""
    db_path = tmp_path / "registry.db"
    engine = init_database(db_path)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            hypothesis = Hypothesis(
                hypothesis_id="hyp-1",
                asset_a="BTC/USDT",
                asset_b="ETH/USDT",
                rationale="Test pair",
                source="rule_based",
                novelty_score=0.9,
                status="new",
                created_by="test",
            )
            session.add(hypothesis)
            session.add(
                Experiment(
                    experiment_id="exp-1",
                    hypothesis_id="hyp-1",
                    status="statistical_testing",
                    current_agent="statistical_testing_agent",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.commit()

        snapshot = load_dashboard_snapshot(db_path)

        assert snapshot.registry_path == db_path
        assert snapshot.counts["hypotheses"] == 1
        assert snapshot.counts["experiments"] == 1
        assert snapshot.experiments[0]["experiment_id"] == "exp-1"
        assert snapshot.experiments[0]["pair"] == "BTC/USDT / ETH/USDT"

        with session_factory() as session:
            assert session.query(Experiment).count() == 1
            assert session.query(Hypothesis).count() == 1
    finally:
        engine.dispose()


def test_load_dashboard_snapshot_filters_and_sorts_experiment_list(tmp_path) -> None:
    """Experiment list should support status, asset, date filters and metric sorting."""
    db_path = tmp_path / "registry.db"
    engine = init_database(db_path)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            session.add_all(
                [
                    Hypothesis(
                        hypothesis_id="hyp-btc-eth",
                        asset_a="BTC/USDT",
                        asset_b="ETH/USDT",
                        rationale="Crypto majors",
                        source="rule_based",
                        novelty_score=0.82,
                        status="approved",
                        created_by="test",
                        created_at=datetime(2026, 1, 10, tzinfo=UTC).replace(tzinfo=None),
                    ),
                    Hypothesis(
                        hypothesis_id="hyp-sol-ada",
                        asset_a="SOL/USDT",
                        asset_b="ADA/USDT",
                        rationale="Layer 1 basket",
                        source="rule_based",
                        novelty_score=0.44,
                        status="testing",
                        created_by="test",
                        created_at=datetime(2026, 1, 11, tzinfo=UTC).replace(tzinfo=None),
                    ),
                    Hypothesis(
                        hypothesis_id="hyp-btc-sol",
                        asset_a="BTC/USDT",
                        asset_b="SOL/USDT",
                        rationale="Mixed basket",
                        source="rule_based",
                        novelty_score=0.71,
                        status="new",
                        created_by="test",
                        created_at=datetime(2026, 1, 12, tzinfo=UTC).replace(tzinfo=None),
                    ),
                ]
            )
            session.add_all(
                [
                    Dataset(
                        dataset_id="dataset-a",
                        symbol="BTC/USDT",
                        source="ccxt",
                        timeframe="15m",
                        start_date=datetime(2025, 1, 1),
                        end_date=datetime(2025, 6, 1),
                        bar_count=100,
                        missing_bars=0,
                        outlier_count=0,
                        quality_score=1.0,
                        adjustment_mode="none",
                        file_path="data/a.parquet",
                    ),
                    Dataset(
                        dataset_id="dataset-b",
                        symbol="ETH/USDT",
                        source="ccxt",
                        timeframe="15m",
                        start_date=datetime(2025, 1, 1),
                        end_date=datetime(2025, 6, 1),
                        bar_count=100,
                        missing_bars=0,
                        outlier_count=0,
                        quality_score=1.0,
                        adjustment_mode="none",
                        file_path="data/b.parquet",
                    ),
                ]
            )
            session.add_all(
                [
                    Experiment(
                        experiment_id="exp-btc-eth",
                        hypothesis_id="hyp-btc-eth",
                        status="reporting",
                        current_agent="report_agent",
                        statistical_tests_passed=True,
                        backtest_completed=True,
                        created_at=datetime(2026, 1, 20, tzinfo=UTC).replace(tzinfo=None),
                    ),
                    Experiment(
                        experiment_id="exp-sol-ada",
                        hypothesis_id="hyp-sol-ada",
                        status="backtesting",
                        current_agent="backtest_agent",
                        statistical_tests_passed=True,
                        created_at=datetime(2026, 1, 21, tzinfo=UTC).replace(tzinfo=None),
                    ),
                    Experiment(
                        experiment_id="exp-btc-sol-old",
                        hypothesis_id="hyp-btc-sol",
                        status="new",
                        current_agent=None,
                        created_at=datetime(2025, 12, 25, tzinfo=UTC).replace(tzinfo=None),
                    ),
                ]
            )
            session.add(
                StatisticalTestResult(
                    test_id="test-btc-eth",
                    hypothesis_id="hyp-btc-eth",
                    dataset_a_id="dataset-a",
                    dataset_b_id="dataset-b",
                    train_start=datetime(2025, 1, 1),
                    train_end=datetime(2025, 3, 1),
                    test_start=datetime(2025, 3, 2),
                    test_end=datetime(2025, 4, 1),
                    cointegration_statistic=-3.0,
                    cointegration_p_value=0.012,
                    adf_statistic=-4.0,
                    adf_p_value=0.02,
                    hedge_ratio=1.2,
                    hedge_ratio_r_squared=0.91,
                    half_life_days=7.0,
                    residual_ljung_box_p_value=0.2,
                    residual_jarque_bera_p_value=0.3,
                    residual_excess_kurtosis=0.1,
                    residual_diagnostics_lags=5,
                    passed=True,
                    tested_at=datetime(2026, 1, 22, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.flush()
            session.add(
                BacktestResult(
                    backtest_id="bt-btc-eth",
                    hypothesis_id="hyp-btc-eth",
                    test_id="test-btc-eth",
                    dataset_a_id="dataset-a",
                    dataset_b_id="dataset-b",
                    git_commit_hash="a" * 40,
                    config_hash="b" * 64,
                    dataset_ids=["dataset-a", "dataset-b"],
                    random_seed=7,
                    execution_command=["stat-arb"],
                    run_timestamp=datetime(2026, 1, 23, tzinfo=UTC).replace(tzinfo=None),
                    lock_file_hash="c" * 64,
                    train_window_days=90,
                    test_window_days=30,
                    num_windows=3,
                    entry_threshold=2.0,
                    exit_threshold=0.5,
                    hedge_ratio=1.2,
                    gross_pnl=130.0,
                    net_pnl=100.0,
                    commission_cost=10.0,
                    spread_cost=8.0,
                    slippage_cost=7.0,
                    funding_cost=3.0,
                    borrow_cost=2.0,
                    num_trades=12,
                    turnover=1.5,
                    avg_holding_time_hours=8.0,
                    median_holding_time_hours=7.0,
                    sharpe_ratio=1.7,
                    sortino_ratio=2.1,
                    volatility=0.11,
                    max_drawdown=-0.08,
                    win_rate=0.58,
                    profit_factor=1.8,
                    net_pnl_2x_costs=70.0,
                    net_pnl_half_costs=115.0,
                    baseline_sharpe=0.4,
                    tested_at=datetime(2026, 1, 24, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.commit()

        snapshot = load_dashboard_snapshot(
            db_path,
            experiment_filters=DashboardExperimentFilters(
                statuses=("reporting", "backtesting"),
                asset_query="btc",
                created_from=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            experiment_sort=DashboardExperimentSort(field="net_pnl", descending=True),
        )

        assert [row["experiment_id"] for row in snapshot.experiments] == ["exp-btc-eth"]
        row = snapshot.experiments[0]
        assert row["latest_cointegration_p_value"] == 0.012
        assert row["latest_sharpe_ratio"] == 1.7
        assert row["latest_net_pnl"] == 100.0
        assert row["latest_max_drawdown"] == -0.08
        assert row["latest_backtest_id"] == "bt-btc-eth"
    finally:
        engine.dispose()


def test_dashboard_sort_keeps_missing_metrics_last(tmp_path) -> None:
    """Descending metric sorts should not place missing values above real metrics."""
    db_path = tmp_path / "registry.db"
    engine = init_database(db_path)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            session.add_all(
                [
                    Hypothesis(
                        hypothesis_id="hyp-with-pnl",
                        asset_a="BTC/USDT",
                        asset_b="ETH/USDT",
                        rationale="With PnL",
                        source="rule_based",
                        novelty_score=0.8,
                        status="testing",
                        created_by="test",
                    ),
                    Hypothesis(
                        hypothesis_id="hyp-without-pnl",
                        asset_a="SOL/USDT",
                        asset_b="ADA/USDT",
                        rationale="Without PnL",
                        source="rule_based",
                        novelty_score=0.9,
                        status="testing",
                        created_by="test",
                    ),
                    Dataset(
                        dataset_id="dataset-a",
                        symbol="BTC/USDT",
                        source="ccxt",
                        timeframe="15m",
                        start_date=datetime(2025, 1, 1),
                        end_date=datetime(2025, 6, 1),
                        bar_count=100,
                        missing_bars=0,
                        outlier_count=0,
                        quality_score=1.0,
                        adjustment_mode="none",
                        file_path="data/a.parquet",
                    ),
                    Dataset(
                        dataset_id="dataset-b",
                        symbol="ETH/USDT",
                        source="ccxt",
                        timeframe="15m",
                        start_date=datetime(2025, 1, 1),
                        end_date=datetime(2025, 6, 1),
                        bar_count=100,
                        missing_bars=0,
                        outlier_count=0,
                        quality_score=1.0,
                        adjustment_mode="none",
                        file_path="data/b.parquet",
                    ),
                ]
            )
            session.add_all(
                [
                    Experiment(
                        experiment_id="exp-with-pnl",
                        hypothesis_id="hyp-with-pnl",
                        status="reporting",
                        created_at=datetime(2026, 1, 2, tzinfo=UTC).replace(tzinfo=None),
                    ),
                    Experiment(
                        experiment_id="exp-without-pnl",
                        hypothesis_id="hyp-without-pnl",
                        status="reporting",
                        created_at=datetime(2026, 1, 3, tzinfo=UTC).replace(tzinfo=None),
                    ),
                    StatisticalTestResult(
                        test_id="test-with-pnl",
                        hypothesis_id="hyp-with-pnl",
                        dataset_a_id="dataset-a",
                        dataset_b_id="dataset-b",
                        train_start=datetime(2025, 1, 1),
                        train_end=datetime(2025, 3, 1),
                        test_start=datetime(2025, 3, 2),
                        test_end=datetime(2025, 4, 1),
                        cointegration_statistic=-3.0,
                        cointegration_p_value=0.012,
                        adf_statistic=-4.0,
                        adf_p_value=0.02,
                        hedge_ratio=1.2,
                        hedge_ratio_r_squared=0.91,
                        half_life_days=7.0,
                        residual_ljung_box_p_value=0.2,
                        residual_jarque_bera_p_value=0.3,
                        residual_excess_kurtosis=0.1,
                        residual_diagnostics_lags=5,
                        passed=True,
                    ),
                ]
            )
            session.flush()
            session.add(
                BacktestResult(
                    backtest_id="bt-with-pnl",
                    hypothesis_id="hyp-with-pnl",
                    test_id="test-with-pnl",
                    dataset_a_id="dataset-a",
                    dataset_b_id="dataset-b",
                    git_commit_hash="a" * 40,
                    config_hash="b" * 64,
                    dataset_ids=["dataset-a", "dataset-b"],
                    random_seed=7,
                    execution_command=["stat-arb"],
                    run_timestamp=datetime(2026, 1, 23, tzinfo=UTC).replace(tzinfo=None),
                    lock_file_hash="c" * 64,
                    train_window_days=90,
                    test_window_days=30,
                    num_windows=3,
                    entry_threshold=2.0,
                    exit_threshold=0.5,
                    hedge_ratio=1.2,
                    gross_pnl=130.0,
                    net_pnl=100.0,
                    commission_cost=10.0,
                    spread_cost=8.0,
                    slippage_cost=7.0,
                    funding_cost=3.0,
                    borrow_cost=2.0,
                    num_trades=12,
                    turnover=1.5,
                    avg_holding_time_hours=8.0,
                    median_holding_time_hours=7.0,
                    sharpe_ratio=1.7,
                    sortino_ratio=2.1,
                    volatility=0.11,
                    max_drawdown=-0.08,
                    win_rate=0.58,
                    profit_factor=1.8,
                    net_pnl_2x_costs=70.0,
                    net_pnl_half_costs=115.0,
                    baseline_sharpe=0.4,
                    tested_at=datetime(2026, 1, 24, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.commit()

        snapshot = load_dashboard_snapshot(
            db_path,
            experiment_sort=DashboardExperimentSort(field="net_pnl", descending=True),
        )

        assert [row["experiment_id"] for row in snapshot.experiments] == [
            "exp-with-pnl",
            "exp-without-pnl",
        ]
    finally:
        engine.dispose()


def test_dashboard_navigation_is_read_only_and_russian() -> None:
    """Initial dashboard pages should be Russian read-only navigation labels."""
    navigation = get_dashboard_navigation()

    assert [item.label for item in navigation] == [
        "Обзор",
        "Эксперименты",
        "Гипотезы",
        "Статтесты",
        "Бэктесты",
        "Отчеты",
        "Память",
        "Очередь одобрения",
    ]
    assert all(item.mode == "read_only" for item in navigation)


def test_dashboard_presentation_helpers_are_streamlit_free() -> None:
    """Dashboard formatting/projection logic should be testable without importing Streamlit."""
    table = pd.DataFrame(
        [
            {"net_pnl": 100.12345, "missing": None, "pair": "BTC/USDT / ETH/USDT"},
            {"net_pnl": None, "missing": None, "pair": "SOL/USDT / ADA/USDT"},
        ]
    )

    assert dashboard_column_label("net_pnl") == "Net PnL"
    assert dashboard_column_label("unknown_field") == "unknown_field"
    assert dashboard_numeric_mean(table, "net_pnl") == 50.0617
    assert dashboard_numeric_mean(table, "does_not_exist") == 0.0
    assert dashboard_metric_value(("not", "streamlit")) == "('not', 'streamlit')"
    assert dashboard_visible_columns(table, ["pair", "net_pnl", "absent"]) == [
        "pair",
        "net_pnl",
    ]


def test_dashboard_experiment_list_ui_exposes_filters_and_sorting() -> None:
    """Task 16.2 UI should expose read-only experiment filters and sorting controls."""
    app = Path("src/stat_arb/dashboard/app.py").read_text(encoding="utf-8")

    assert "_render_experiment_list(snapshot)" in app
    assert "Фильтры экспериментов" in app
    assert "Статусы" in app
    assert "Актив" in app
    assert "Дата создания" in app
    assert "Сортировка" in app
    assert "Сначала большие/новые" in app
    assert "Эксперименты не найдены" in app
    assert "st.button" not in app
    assert "form_submit_button" not in app


def test_dashboard_snapshot_exposes_task16_registry_views(tmp_path) -> None:
    """Task 16 pages should read hypotheses, tests, backtests, reports and queues."""
    db_path = tmp_path / "registry.db"
    engine = init_database(db_path)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            session.add(
                Hypothesis(
                    hypothesis_id="hyp-dashboard",
                    asset_a="BTC/USDT",
                    asset_b="ETH/USDT",
                    rationale="Dashboard pair",
                    source="rule_based",
                    similar_hypotheses=["memory:hyp-old", "memory:hyp-old"],
                    novelty_score=0.73,
                    status="testing",
                    created_by="test",
                    created_at=datetime(2026, 2, 1, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.add_all(
                [
                    Dataset(
                        dataset_id="dataset-a",
                        symbol="BTC/USDT",
                        source="ccxt",
                        timeframe="15m",
                        start_date=datetime(2025, 1, 1),
                        end_date=datetime(2025, 6, 1),
                        bar_count=100,
                        missing_bars=0,
                        outlier_count=0,
                        quality_score=1.0,
                        adjustment_mode="none",
                        file_path="data/a.parquet",
                    ),
                    Dataset(
                        dataset_id="dataset-b",
                        symbol="ETH/USDT",
                        source="ccxt",
                        timeframe="15m",
                        start_date=datetime(2025, 1, 1),
                        end_date=datetime(2025, 6, 1),
                        bar_count=100,
                        missing_bars=0,
                        outlier_count=0,
                        quality_score=1.0,
                        adjustment_mode="none",
                        file_path="data/b.parquet",
                    ),
                ]
            )
            session.add(
                Experiment(
                    experiment_id="exp-dashboard",
                    hypothesis_id="hyp-dashboard",
                    status="reporting",
                    current_agent="report_agent",
                    data_quality_passed=True,
                    statistical_tests_passed=True,
                    backtest_completed=True,
                    critic_approved=True,
                    created_at=datetime(2026, 2, 2, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.add(
                StatisticalTestResult(
                    test_id="test-dashboard",
                    hypothesis_id="hyp-dashboard",
                    dataset_a_id="dataset-a",
                    dataset_b_id="dataset-b",
                    train_start=datetime(2025, 1, 1),
                    train_end=datetime(2025, 3, 1),
                    test_start=datetime(2025, 3, 2),
                    test_end=datetime(2025, 4, 1),
                    cointegration_statistic=-3.2,
                    cointegration_p_value=0.019,
                    adf_statistic=-4.2,
                    adf_p_value=0.021,
                    hedge_ratio=1.15,
                    hedge_ratio_r_squared=0.88,
                    half_life_days=6.5,
                    residual_ljung_box_p_value=0.31,
                    residual_jarque_bera_p_value=0.42,
                    residual_excess_kurtosis=0.11,
                    residual_diagnostics_lags=5,
                    regime_changes_detected=1,
                    passed=True,
                    tested_at=datetime(2026, 2, 3, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.flush()
            session.add(
                BacktestResult(
                    backtest_id="bt-dashboard",
                    hypothesis_id="hyp-dashboard",
                    test_id="test-dashboard",
                    dataset_a_id="dataset-a",
                    dataset_b_id="dataset-b",
                    git_commit_hash="a" * 40,
                    config_hash="b" * 64,
                    dataset_ids=["dataset-a", "dataset-b"],
                    random_seed=11,
                    execution_command=["stat-arb"],
                    run_timestamp=datetime(2026, 2, 4, tzinfo=UTC).replace(tzinfo=None),
                    lock_file_hash="c" * 64,
                    train_window_days=90,
                    test_window_days=30,
                    num_windows=3,
                    entry_threshold=2.0,
                    exit_threshold=0.5,
                    hedge_ratio=1.15,
                    gross_pnl=140.0,
                    net_pnl=101.0,
                    commission_cost=12.0,
                    spread_cost=9.0,
                    slippage_cost=8.0,
                    funding_cost=6.0,
                    borrow_cost=4.0,
                    num_trades=14,
                    turnover=1.9,
                    avg_holding_time_hours=9.0,
                    median_holding_time_hours=8.0,
                    sharpe_ratio=1.8,
                    sortino_ratio=2.2,
                    volatility=0.13,
                    max_drawdown=-0.09,
                    win_rate=0.61,
                    profit_factor=1.9,
                    net_pnl_2x_costs=62.0,
                    net_pnl_half_costs=120.5,
                    baseline_sharpe=0.5,
                    tested_at=datetime(2026, 2, 5, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.add(
                CriticReview(
                    review_id="review-dashboard",
                    backtest_id="bt-dashboard",
                    weak_assumptions=["half-life near policy bound"],
                    cost_concerns=["slippage snapshot requires refresh"],
                    status="approved",
                    recommendation="Ready for demo review with caveats.",
                    objections="No blocking objections.",
                    reviewed_at=datetime(2026, 2, 6, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.add(
                CoordinatorTask(
                    task_id="task-dashboard",
                    experiment_id="exp-dashboard",
                    task_type="reporting",
                    agent_name="report_agent",
                    priority=3,
                    status="failed",
                    attempt_count=2,
                    max_attempts=3,
                    payload={"stage": "reporting"},
                    last_error="Missing backtest_series sidecar",
                    created_at=datetime(2026, 2, 7, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.add(
                ReportArtifact(
                    artifact_id="artifact-dashboard",
                    experiment_id="exp-dashboard",
                    artifact_type="backtest_series",
                    file_path=str(tmp_path / "bt-dashboard.series.json"),
                    format="json",
                    created_at=datetime(2026, 2, 8, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            Path(tmp_path / "bt-dashboard.series.json").write_text(
                json.dumps({"backtest_id": "bt-dashboard"}),
                encoding="utf-8",
            )
            session.commit()

        snapshot = load_dashboard_snapshot(db_path)

        assert snapshot.hypotheses[0]["similar_hypotheses_count"] == 1
        assert snapshot.hypotheses[0]["related_experiments"] == 1
        assert snapshot.statistical_tests[0]["pair"] == "BTC/USDT / ETH/USDT"
        assert snapshot.statistical_tests[0]["regime_changes_detected"] == 1
        assert snapshot.backtests[0]["total_cost"] == 39.0
        assert snapshot.backtests[0]["has_series_sidecar"] is True
        assert snapshot.report_artifacts[0]["artifact_type"] == "backtest_series"
        assert snapshot.logs[0]["last_error"] == "Missing backtest_series sidecar"
        assert snapshot.approval_queue[0]["experiment_id"] == "exp-dashboard"
    finally:
        engine.dispose()


def test_dashboard_sidecar_readiness_requires_matching_json_payload(tmp_path) -> None:
    """Dashboard should not trust path substrings when checking factual sidecars."""
    db_path = tmp_path / "registry.db"
    engine = init_database(db_path)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            session.add_all(
                [
                    Hypothesis(
                        hypothesis_id="hyp-sidecar",
                        asset_a="BTC/USDT",
                        asset_b="ETH/USDT",
                        rationale="Sidecar check",
                        source="rule_based",
                        novelty_score=0.8,
                        status="testing",
                        created_by="test",
                    ),
                    Dataset(
                        dataset_id="dataset-a",
                        symbol="BTC/USDT",
                        source="ccxt",
                        timeframe="15m",
                        start_date=datetime(2025, 1, 1),
                        end_date=datetime(2025, 6, 1),
                        bar_count=100,
                        missing_bars=0,
                        outlier_count=0,
                        quality_score=1.0,
                        adjustment_mode="none",
                        file_path="data/a.parquet",
                    ),
                    Dataset(
                        dataset_id="dataset-b",
                        symbol="ETH/USDT",
                        source="ccxt",
                        timeframe="15m",
                        start_date=datetime(2025, 1, 1),
                        end_date=datetime(2025, 6, 1),
                        bar_count=100,
                        missing_bars=0,
                        outlier_count=0,
                        quality_score=1.0,
                        adjustment_mode="none",
                        file_path="data/b.parquet",
                    ),
                    Experiment(
                        experiment_id="exp-sidecar",
                        hypothesis_id="hyp-sidecar",
                        status="reporting",
                    ),
                    StatisticalTestResult(
                        test_id="test-sidecar",
                        hypothesis_id="hyp-sidecar",
                        dataset_a_id="dataset-a",
                        dataset_b_id="dataset-b",
                        train_start=datetime(2025, 1, 1),
                        train_end=datetime(2025, 3, 1),
                        test_start=datetime(2025, 3, 2),
                        test_end=datetime(2025, 4, 1),
                        cointegration_statistic=-3.0,
                        cointegration_p_value=0.012,
                        adf_statistic=-4.0,
                        adf_p_value=0.02,
                        hedge_ratio=1.2,
                        hedge_ratio_r_squared=0.91,
                        half_life_days=7.0,
                        residual_ljung_box_p_value=0.2,
                        residual_jarque_bera_p_value=0.3,
                        residual_excess_kurtosis=0.1,
                        residual_diagnostics_lags=5,
                        passed=True,
                    ),
                ]
            )
            session.flush()
            session.add(
                BacktestResult(
                    backtest_id="bt-1",
                    hypothesis_id="hyp-sidecar",
                    test_id="test-sidecar",
                    dataset_a_id="dataset-a",
                    dataset_b_id="dataset-b",
                    git_commit_hash="a" * 40,
                    config_hash="b" * 64,
                    dataset_ids=["dataset-a", "dataset-b"],
                    random_seed=7,
                    execution_command=["stat-arb"],
                    run_timestamp=datetime(2026, 1, 23, tzinfo=UTC).replace(tzinfo=None),
                    lock_file_hash="c" * 64,
                    train_window_days=90,
                    test_window_days=30,
                    num_windows=3,
                    entry_threshold=2.0,
                    exit_threshold=0.5,
                    hedge_ratio=1.2,
                    gross_pnl=130.0,
                    net_pnl=100.0,
                    commission_cost=10.0,
                    spread_cost=8.0,
                    slippage_cost=7.0,
                    funding_cost=3.0,
                    borrow_cost=2.0,
                    num_trades=12,
                    turnover=1.5,
                    avg_holding_time_hours=8.0,
                    median_holding_time_hours=7.0,
                    sharpe_ratio=1.7,
                    sortino_ratio=2.1,
                    volatility=0.11,
                    max_drawdown=-0.08,
                    win_rate=0.58,
                    profit_factor=1.8,
                    net_pnl_2x_costs=70.0,
                    net_pnl_half_costs=115.0,
                    baseline_sharpe=0.4,
                    tested_at=datetime(2026, 1, 24, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            wrong_path = tmp_path / "backtest-bt-10.series.json"
            wrong_path.write_text(json.dumps({"backtest_id": "bt-10"}), encoding="utf-8")
            session.add(
                ReportArtifact(
                    artifact_id="artifact-wrong",
                    experiment_id="exp-sidecar",
                    artifact_type="backtest_series",
                    file_path=str(wrong_path),
                    format="json",
                )
            )
            session.commit()

        snapshot = load_dashboard_snapshot(db_path)

        assert snapshot.backtests[0]["has_series_sidecar"] is False
    finally:
        engine.dispose()


class FakeDashboardMemoryService:
    """Fake Memory Agent read boundary for dashboard search tests."""

    def __init__(self) -> None:
        self.requests: list[MemoryQueryRequest] = []

    def query(self, request: MemoryQueryRequest) -> MemoryQueryResult:
        self.requests.append(request)
        return MemoryQueryResult(
            results=(
                ApeRAGSearchResult(
                    text=(
                        "DEC-0065 says dashboard memory search must go through "
                        "Memory Agent policy. api_key=SHOULD_NOT_LEAK " + "x" * 700
                    ),
                    score=0.91,
                    source="decisions_dashboard.md",
                    metadata={"raw": {"nested": "hidden"}},
                ),
            ),
            graph_summary=ApeRAGGraphSummary(labels=3, nodes=4, edges=2),
        )


def test_dashboard_memory_search_uses_memory_agent_query_boundary() -> None:
    """Task 16.7b should query memory through a sanitized read-only Memory Agent boundary."""
    memory = FakeDashboardMemoryService()

    result = run_dashboard_memory_search(
        DashboardMemorySearchRequest(
            query="dashboard memory search",
            query_type="topic",
            scope="project",
            keywords=("dashboard", "memory"),
            top_k=3,
        ),
        memory_service=memory,
    )

    assert memory.requests[0].query_type == "topic"
    assert memory.requests[0].scope == "project"
    assert memory.requests[0].top_k == 3
    assert result.ready is True
    assert result.graph_labels == 3
    assert result.items[0].source == "decisions_dashboard.md"
    assert "api_key" not in result.items[0].snippet.lower()
    assert len(result.items[0].snippet) <= 420
    assert result.items[0].metadata_keys == ("raw",)


def test_dashboard_memory_search_rejects_empty_query() -> None:
    """Dashboard memory search should fail closed before calling backend on empty input."""
    memory = FakeDashboardMemoryService()

    with pytest.raises(ValueError, match="query is required"):
        run_dashboard_memory_search(
            DashboardMemorySearchRequest(query=" ", query_type="topic"),
            memory_service=memory,
        )

    assert memory.requests == []


def test_dashboard_task16_pages_are_rendered_read_only() -> None:
    """Task 16.3-16.8a pages should be concrete read-only sections, not placeholders."""
    app = Path("src/stat_arb/dashboard/app.py").read_text(encoding="utf-8")
    data = Path("src/stat_arb/dashboard/data.py").read_text(encoding="utf-8")

    for call in (
        "_render_hypothesis_status(snapshot)",
        "_render_statistical_tests(snapshot)",
        "_render_backtests(snapshot)",
        "_render_reports(snapshot)",
        "_render_memory_search(snapshot)",
        "_render_approval_queue(snapshot)",
    ):
        assert call in app

    assert "Похожие гипотезы" in app
    assert "Cointegration p-value" in app
    assert "Cost attribution" in app
    assert "Журнал ошибок" in app
    assert "Поиск по памяти" in app
    assert "query_dashboard_memory" in app
    assert "audited Coordinator API" in app
    assert "_read_only_session" in data
    assert "session.rollback()" in data
    assert "st.button" not in app
    assert "form_submit_button" not in app


def test_check_dashboard_structure_script_passes() -> None:
    """Dashboard guard should validate scaffold files and read-only boundaries."""
    powershell_exe = shutil.which("pwsh") or shutil.which("powershell")
    assert powershell_exe is not None

    result = subprocess.run(
        [
            powershell_exe,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/check_dashboard_structure.ps1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_dashboard_structure_guard_blocks_raw_http_and_bytecode_output() -> None:
    """Dashboard guard should block raw HTTP bypasses and avoid __pycache__ churn."""
    script = Path("scripts/check_dashboard_structure.ps1").read_text(encoding="utf-8")

    assert "httpx|requests|urllib|/api/v1/collections|Invoke-RestMethod" in script
    assert "PYTHONDONTWRITEBYTECODE" in script


def test_dashboard_memory_query_factory_stays_outside_streamlit_surface() -> None:
    """Dashboard should use a factory wrapper, not raw ApeRAG or HTTP clients in Streamlit code."""
    app = Path("src/stat_arb/dashboard/app.py").read_text(encoding="utf-8")
    factory = Path("src/stat_arb/memory/dashboard_query.py").read_text(encoding="utf-8")

    assert "query_dashboard_memory" in app
    assert "ApeRAGMemoryClient" not in app
    assert "MemoryAgentService" not in app
    assert "MemoryAgentService" in factory
    assert "ApeRAGMemoryClient" in factory


def test_pre_commit_runs_dashboard_structure_guard() -> None:
    """Fast pre-commit should keep the dashboard read-only scaffold guarded."""
    script = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")

    assert "check_dashboard_structure.ps1" in script
    assert "$dashboardStructureCheckScript" in script
    assert "Invoke-RequiredCheck $dashboardStructureCheckScript" in script


def test_dashboard_local_launcher_is_background_and_project_rooted() -> None:
    """Dashboard launcher should let localhost:8501 work without manual cwd setup."""
    script = Path("scripts/start_dashboard.ps1").read_text(encoding="utf-8")
    config = Path(".streamlit/config.toml").read_text(encoding="utf-8")

    assert "$repoRoot = Split-Path -Parent $PSScriptRoot" in script
    assert "src\\stat_arb\\dashboard\\app.py" in script
    assert "--server.port" in script
    assert "--server.headless" in script
    assert "-WindowStyle Hidden" in script
    assert "http://localhost:$Port" in script
    assert "gatherUsageStats = false" in config


def test_dashboard_autostart_installer_registers_startup_task() -> None:
    """Dashboard should have an optional Windows startup task installer."""
    script = Path("scripts/install_dashboard_autostart.ps1").read_text(encoding="utf-8")

    assert "StatArbDashboard" in script
    assert "Get-Variable IsWindows" in script
    assert "New-ScheduledTaskAction" in script
    assert "New-ScheduledTaskTrigger -AtLogOn" in script
    assert "WScript.Shell" in script
    assert "Startup" in script
    assert "start_dashboard.ps1" in script
