from __future__ import annotations

import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from stat_arb.dashboard.data import (
    DashboardExperimentFilters,
    DashboardExperimentSort,
    get_dashboard_navigation,
    load_dashboard_snapshot,
)
from stat_arb.storage import (
    BacktestResult,
    Dataset,
    Experiment,
    Hypothesis,
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
