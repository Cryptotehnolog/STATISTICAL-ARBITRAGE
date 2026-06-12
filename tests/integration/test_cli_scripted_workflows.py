"""Integration checkpoint for Task 15 scripted CLI workflows."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from stat_arb.storage import (
    BacktestResult,
    Base,
    CoordinatorTask,
    DataQualityReportRecord,
    Dataset,
    Experiment,
    Hypothesis,
    ReportArtifact,
    StatisticalTestResult,
    create_database_engine,
    create_session_factory,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_scripted_cli_workflows_chain_through_registry_and_reporting_guard(
    tmp_path: Path,
) -> None:
    """Mock-data scripts should compose without bypassing registry or agent boundaries."""
    db_path = tmp_path / "registry.db"
    assets_path, correlations_path, p_values_path = _write_pair_screening_inputs(tmp_path)

    _run_script(
        "scripts/screen_pairs.ps1",
        "-AssetsJson",
        assets_path,
        "-CorrelationsJson",
        correlations_path,
        "-PValuesJson",
        p_values_path,
        "-MinAbsCorrelation",
        "0.85",
        "-MinMarketCap",
        "50000000000",
        "-MaxPairs",
        "1",
        "-MultipleTestingMethod",
        "bonferroni",
        "-CandidateAlpha",
        "0.05",
        "-InitialNoveltyScore",
        "1.0",
        "-InitialStatus",
        "new",
        "-Source",
        "scripted-integration",
        "-CreatedBy",
        "hypothesis_agent",
        "-DbPath",
        db_path,
        "-RequireSameSector",
    )
    hypothesis_id = _single_hypothesis_id(db_path)
    dataset_a_id, dataset_b_id, stat_payload_path = _seed_statistical_prerequisites(
        tmp_path,
        db_path,
        hypothesis_id=hypothesis_id,
    )
    experiment_id = _seed_experiment(
        db_path,
        hypothesis_id=hypothesis_id,
        status="data_validation",
        current_agent="data_agent",
    )

    _run_script(
        "scripts/run_statistical_testing.ps1",
        "-ExperimentId",
        experiment_id,
        "-PayloadJson",
        stat_payload_path,
        "-Priority",
        "1",
        "-MaxAttempts",
        "2",
        "-Reason",
        "scripted integration statistical testing",
        "-Actor",
        "pytest",
        "-MaxRunningTasks",
        "1",
        "-MaxRunningTasksPerAgent",
        "1",
        "-DbPath",
        db_path,
    )
    test_id = _single_statistical_test_id(db_path)

    backtest_payload_path = _write_backtest_payload(
        tmp_path,
        hypothesis_id=hypothesis_id,
        test_id=test_id,
        dataset_a_id=dataset_a_id,
        dataset_b_id=dataset_b_id,
    )
    _run_script(
        "scripts/run_backtest.ps1",
        "-ExperimentId",
        experiment_id,
        "-PayloadJson",
        backtest_payload_path,
        "-Priority",
        "2",
        "-MaxAttempts",
        "2",
        "-Reason",
        "scripted integration backtest",
        "-Actor",
        "pytest",
        "-MaxRunningTasks",
        "1",
        "-MaxRunningTasksPerAgent",
        "1",
        "-DbPath",
        db_path,
    )
    backtest_id = _single_backtest_id(db_path)

    report_payload_path = _write_report_payload(
        tmp_path,
        backtest_id=backtest_id,
    )
    _run_cli(
        "experiment",
        "run-stage",
        "--experiment-id",
        experiment_id,
        "--stage",
        "reporting",
        "--task-type",
        "write_report",
        "--agent-name",
        "report_agent",
        "--priority",
        "3",
        "--max-attempts",
        "2",
        "--payload-json",
        report_payload_path,
        "--db-path",
        db_path,
    )
    reporting_task_id = _pending_reporting_task_id(db_path)
    _run_cli(
        "experiment",
        "execute-stage",
        "--task-id",
        reporting_task_id,
        "--stage",
        "reporting",
        "--max-running-tasks",
        "1",
        "--max-running-tasks-per-agent",
        "1",
        "--db-path",
        db_path,
    )

    _assert_workflow_outputs(db_path)


def _run_script(script: str, *args: object) -> None:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if executable is None:
        raise AssertionError("PowerShell executable not found")
    command = [
        executable,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(REPO_ROOT / script),
        *(str(arg) for arg in args),
    ]
    result = subprocess.run(command, cwd=REPO_ROOT, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


def _run_cli(*args: object) -> None:
    result = subprocess.run(
        ["uv", "run", "stat-arb", *(str(arg) for arg in args)],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _write_pair_screening_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    assets_path = tmp_path / "assets.json"
    correlations_path = tmp_path / "correlations.json"
    p_values_path = tmp_path / "p_values.json"
    assets_path.write_text(
        json.dumps(
            [
                {"symbol": "AAA", "sector": "Banks", "market_cap": 100_000_000_000},
                {"symbol": "BBB", "sector": "Banks", "market_cap": 95_000_000_000},
            ],
        ),
        encoding="utf-8",
    )
    correlations_path.write_text(
        json.dumps([{"asset_a": "AAA", "asset_b": "BBB", "correlation": 0.93}]),
        encoding="utf-8",
    )
    p_values_path.write_text(
        json.dumps([{"asset_a": "AAA", "asset_b": "BBB", "p_value": 0.01}]),
        encoding="utf-8",
    )
    return assets_path, correlations_path, p_values_path


def _seed_statistical_prerequisites(
    tmp_path: Path,
    db_path: Path,
    *,
    hypothesis_id: str,
) -> tuple[str, str, Path]:
    start = datetime(2024, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    prices_a, prices_b, timestamps = _cli_cointegrated_pair(start)
    dataset_a_id = str(uuid4())
    dataset_b_id = str(uuid4())
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        session.add_all(
            [
                Dataset(
                    dataset_id=dataset_a_id,
                    symbol="AAA",
                    source="scripted-integration",
                    timeframe="15m",
                    start_date=start,
                    end_date=timestamps[-1],
                    bar_count=len(timestamps),
                    adjustment_mode="none",
                    file_path=str(tmp_path / "aaa.parquet"),
                ),
                Dataset(
                    dataset_id=dataset_b_id,
                    symbol="BBB",
                    source="scripted-integration",
                    timeframe="15m",
                    start_date=start,
                    end_date=timestamps[-1],
                    bar_count=len(timestamps),
                    adjustment_mode="none",
                    file_path=str(tmp_path / "bbb.parquet"),
                ),
                _quality_report(dataset_a_id, "AAA", start, timestamps[-1], len(timestamps)),
                _quality_report(dataset_b_id, "BBB", start, timestamps[-1], len(timestamps)),
            ],
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    payload_path = tmp_path / "statistical_payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "hypothesis_id": hypothesis_id,
                "dataset_a_id": dataset_a_id,
                "dataset_b_id": dataset_b_id,
                "prices_a": prices_a,
                "prices_b": prices_b,
                "aligned_timestamps": [timestamp.isoformat() for timestamp in timestamps],
                "train_fraction": 0.7,
                "alpha": 0.99,
                "adf_regression": "c",
                "adf_autolag": "AIC",
                "periods_per_day": 96.0,
                "residual_diagnostics_lags": 10,
                "regime_window": 60,
                "regime_mean_shift_threshold": 3.0,
                "regime_volatility_ratio_threshold": 2.5,
            },
        ),
        encoding="utf-8",
    )
    return dataset_a_id, dataset_b_id, payload_path


def _write_backtest_payload(
    tmp_path: Path,
    *,
    hypothesis_id: str,
    test_id: str,
    dataset_a_id: str,
    dataset_b_id: str,
) -> Path:
    start = datetime(2024, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    prices_a, prices_b, timestamps = _cli_backtest_pair(start)
    lock_path = tmp_path / "uv.lock"
    lock_path.write_text("scripted integration lock", encoding="utf-8")
    payload_path = tmp_path / "backtest_payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "hypothesis_id": hypothesis_id,
                "test_id": test_id,
                "dataset_a_id": dataset_a_id,
                "dataset_b_id": dataset_b_id,
                "prices_a": prices_a,
                "prices_b": prices_b,
                "z_scores": [0.0, 2.2, 1.2, 0.2, -2.1, 0.0],
                "aligned_timestamps": [timestamp.isoformat() for timestamp in timestamps],
                "hedge_ratio": 1.0,
                "entry_threshold": 2.0,
                "exit_threshold": 0.5,
                "exit_policy": None,
                "risk_exit_policy_disabled_reason": "integration test uses convergence-only exits",
                "cost_config": {
                    "commission_rate": 0.001,
                    "spread_cost_rate": 0.0005,
                    "slippage_rate": 0.0002,
                    "funding_rate_daily": 0.0001,
                    "borrow_rate_annual": 0.005,
                    "status": "verified",
                    "source": "scripted-integration",
                    "verified_at": "2024-01-01T00:00:00+00:00",
                    "venue": "test-exchange",
                    "market_type": "perpetual",
                    "notes": "synthetic integration fixture",
                },
                "periods_per_day": 96.0,
                "average_portfolio_value": 10000.0,
                "equity_curve": [100.0, 102.0, 100.98, 102.49, 103.0, 103.25],
                "period_returns": [0.02, -0.01, 0.015, 0.005, 0.002],
                "trade_pnls": [5.0, -2.0],
                "metric_config": {
                    "periods_per_year": 365,
                    "risk_free_rate_per_period": 0.0,
                    "var_confidence": 0.95,
                    "cvar_confidence": 0.95,
                },
                "baseline_config": {
                    "kind": "buy_and_hold",
                    "name": "long_asset_a_one_unit",
                    "asset": "asset_a",
                    "side": "long",
                    "units": 1.0,
                    "initial_capital": 100.0,
                },
                "sensitivity_scenarios": [
                    {"name": "double_costs", "cost_multiplier": 2.0},
                    {"name": "half_costs", "cost_multiplier": 0.5},
                ],
                "reproducibility": {
                    "git_commit_hash": "abcdef1",
                    "dataset_ids": [dataset_a_id, dataset_b_id],
                    "random_seed": None,
                    "execution_command": ["stat-arb", "experiment", "execute-stage"],
                    "run_timestamp": "2024-01-02T00:00:00+00:00",
                    "lock_file_path": str(lock_path),
                },
                "train_window_days": 60,
                "test_window_days": 30,
                "num_windows": 2,
                "artifact_output_dir": str(tmp_path / "backtest-artifacts"),
                "series": {
                    "timestamps": [timestamp.isoformat() for timestamp in timestamps],
                    "equity_curve": [100.0, 102.0, 100.98, 102.49, 103.0, 103.25],
                    "drawdown_curve": [0.0, 0.0, 0.01, 0.0, 0.0, 0.0],
                    "z_scores": [0.0, 2.2, 1.2, 0.2, -2.1, 0.0],
                    "entry_markers": [1, 4],
                    "exit_markers": [3, 5],
                    "rolling_sharpe": [0.0, 0.1, 0.2, 0.3, 0.2, 0.4],
                    "trade_pnls": [5.0, -2.0],
                },
            },
        ),
        encoding="utf-8",
    )
    return payload_path


def _write_report_payload(tmp_path: Path, *, backtest_id: str) -> Path:
    payload_path = tmp_path / "report_payload.json"
    payload_path.write_text(
        json.dumps(
            {
                "backtest_id": backtest_id,
                "output_dir": str(tmp_path / "reports"),
            },
        ),
        encoding="utf-8",
    )
    return payload_path


def _quality_report(
    dataset_id: str,
    symbol: str,
    start: datetime,
    end: datetime,
    count: int,
) -> DataQualityReportRecord:
    return DataQualityReportRecord(
        report_id=str(uuid4()),
        dataset_id=dataset_id,
        symbol=symbol,
        source="scripted-integration",
        timeframe="15m",
        start_date=start,
        end_date=end,
        bar_count=count,
        expected_bar_count=count,
        timezone_normalized=True,
        alignment_score=1.0,
        quality_score=1.0,
        passed=True,
        issues=[],
        report_path=f"/tmp/{symbol}-quality.json",
        generated_at=start,
    )


def _cli_cointegrated_pair(start: datetime) -> tuple[list[float], list[float], list[datetime]]:
    observations = 240
    prices_b = [100.0]
    for index in range(1, observations):
        prices_b.append(prices_b[-1] + 0.05 + 0.2 * ((index % 7) - 3))
    residuals = [0.0]
    for index in range(1, observations):
        shock = 0.08 * ((index % 5) - 2)
        residuals.append(0.65 * residuals[-1] + shock)
    prices_a = [1.4 * price + residual for price, residual in zip(prices_b, residuals)]
    timestamps = [start + timedelta(minutes=15 * index) for index in range(observations)]
    return prices_a, prices_b, timestamps


def _cli_backtest_pair(start: datetime) -> tuple[list[float], list[float], list[datetime]]:
    prices_a = [100.0, 103.0, 101.0, 100.0, 99.0, 100.0]
    prices_b = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
    timestamps = [start + timedelta(minutes=15 * index) for index in range(len(prices_a))]
    return prices_a, prices_b, timestamps


def _seed_experiment(
    db_path: Path,
    *,
    hypothesis_id: str,
    status: str,
    current_agent: str,
) -> str:
    experiment_id = str(uuid4())
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        session.add(
            Experiment(
                experiment_id=experiment_id,
                hypothesis_id=hypothesis_id,
                status=status,
                current_agent=current_agent,
            ),
        )
        session.commit()
        return experiment_id
    finally:
        session.close()
        engine.dispose()


def _single_hypothesis_id(db_path: Path) -> str:
    engine = create_database_engine(db_path)
    session = create_session_factory(engine)()
    try:
        return str(session.query(Hypothesis).one().hypothesis_id)
    finally:
        session.close()
        engine.dispose()


def _single_statistical_test_id(db_path: Path) -> str:
    engine = create_database_engine(db_path)
    session = create_session_factory(engine)()
    try:
        return str(session.query(StatisticalTestResult).one().test_id)
    finally:
        session.close()
        engine.dispose()


def _single_backtest_id(db_path: Path) -> str:
    engine = create_database_engine(db_path)
    session = create_session_factory(engine)()
    try:
        return str(session.query(BacktestResult).one().backtest_id)
    finally:
        session.close()
        engine.dispose()


def _pending_reporting_task_id(db_path: Path) -> str:
    engine = create_database_engine(db_path)
    session = create_session_factory(engine)()
    try:
        task = (
            session.query(CoordinatorTask)
            .filter(
                CoordinatorTask.task_type == "write_report",
                CoordinatorTask.status == "pending",
            )
            .one()
        )
        return str(task.task_id)
    finally:
        session.close()
        engine.dispose()


def _assert_workflow_outputs(db_path: Path) -> None:
    engine = create_database_engine(db_path)
    session = create_session_factory(engine)()
    try:
        experiment = session.query(Experiment).one()
        artifact_types = {row.artifact_type for row in session.query(ReportArtifact).all()}
        assert session.query(Hypothesis).count() == 1
        assert session.query(StatisticalTestResult).count() == 1
        assert session.query(BacktestResult).count() == 1
        assert "backtest_series" in artifact_types
        assert {
            "backtest_report",
            "json_summary",
            "equity_curve",
            "z_score_signals",
            "cost_attribution",
            "rolling_sharpe",
            "trade_distribution",
        } <= artifact_types
        assert experiment.status == "backtesting"
        assert experiment.current_agent == "backtest_agent"
        assert all(task.status == "completed" for task in session.query(CoordinatorTask).all())
    finally:
        session.close()
        engine.dispose()
