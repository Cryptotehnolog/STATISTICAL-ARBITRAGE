"""CI reproducibility checkpoint for deterministic scripted workflows."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from stat_arb.storage import (
    BacktestResult,
    CoordinatorTask,
    Experiment,
    Hypothesis,
    ReportArtifact,
    StatisticalTestResult,
    create_database_engine,
    create_session_factory,
)

HELPERS_PATH = Path(__file__).with_name("test_cli_scripted_workflows.py")
HELPERS_SPEC = importlib.util.spec_from_file_location(
    "stat_arb_cli_scripted_workflow_helpers",
    HELPERS_PATH,
)
if HELPERS_SPEC is None or HELPERS_SPEC.loader is None:
    raise RuntimeError(f"Cannot load scripted workflow helpers from {HELPERS_PATH}")
HELPERS = importlib.util.module_from_spec(HELPERS_SPEC)
HELPERS_SPEC.loader.exec_module(HELPERS)


def test_scripted_workflow_reproduces_metrics_with_same_inputs(tmp_path: Path) -> None:
    """Running the same scripted experiment twice should reproduce registry metrics."""
    first = _run_reproducible_scripted_workflow(tmp_path / "first")
    second = _run_reproducible_scripted_workflow(tmp_path / "second")

    assert second == first


def _run_reproducible_scripted_workflow(work_dir: Path) -> dict[str, object]:
    work_dir.mkdir(parents=True)
    db_path = work_dir / "registry.db"
    assets_path, correlations_path, p_values_path = HELPERS._write_pair_screening_inputs(work_dir)

    HELPERS._run_script(
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
        "scripted-reproducibility",
        "-CreatedBy",
        "hypothesis_agent",
        "-DbPath",
        db_path,
        "-RequireSameSector",
    )
    hypothesis_id = HELPERS._single_hypothesis_id(db_path)
    dataset_a_id, dataset_b_id, stat_payload_path = HELPERS._seed_statistical_prerequisites(
        work_dir,
        db_path,
        hypothesis_id=hypothesis_id,
    )
    experiment_id = HELPERS._seed_experiment(
        db_path,
        hypothesis_id=hypothesis_id,
        status="data_validation",
        current_agent="data_agent",
    )

    HELPERS._run_script(
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
        "scripted reproducibility statistical testing",
        "-Actor",
        "pytest",
        "-MaxRunningTasks",
        "1",
        "-MaxRunningTasksPerAgent",
        "1",
        "-DbPath",
        db_path,
    )
    test_id = HELPERS._single_statistical_test_id(db_path)

    backtest_payload_path = HELPERS._write_backtest_payload(
        work_dir,
        hypothesis_id=hypothesis_id,
        test_id=test_id,
        dataset_a_id=dataset_a_id,
        dataset_b_id=dataset_b_id,
    )
    HELPERS._run_script(
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
        "scripted reproducibility backtest",
        "-Actor",
        "pytest",
        "-MaxRunningTasks",
        "1",
        "-MaxRunningTasksPerAgent",
        "1",
        "-DbPath",
        db_path,
    )
    backtest_id = HELPERS._single_backtest_id(db_path)

    report_payload_path = HELPERS._write_report_payload(work_dir, backtest_id=backtest_id)
    HELPERS._run_cli(
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
    reporting_task_id = HELPERS._pending_reporting_task_id(db_path)
    HELPERS._run_cli(
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

    return _reproducibility_snapshot(db_path)


def _reproducibility_snapshot(db_path: Path) -> dict[str, object]:
    engine = create_database_engine(db_path)
    session = create_session_factory(engine)()
    try:
        backtest = session.query(BacktestResult).one()
        statistical = session.query(StatisticalTestResult).one()
        experiment = session.query(Experiment).one()
        artifact_types = sorted(row.artifact_type for row in session.query(ReportArtifact).all())
        task_statuses = sorted(
            (task.task_type, task.agent_name, task.status, task.attempt_count)
            for task in session.query(CoordinatorTask).all()
        )
        hypothesis = session.query(Hypothesis).one()
        return {
            "hypothesis_pair": (hypothesis.asset_a, hypothesis.asset_b),
            "hypothesis_novelty_score": round(float(hypothesis.novelty_score), 12),
            "experiment_status": experiment.status,
            "experiment_current_agent": experiment.current_agent,
            "statistical": {
                "cointegration_p_value": round(statistical.cointegration_p_value, 12),
                "adf_p_value": round(statistical.adf_p_value, 12),
                "hedge_ratio": round(statistical.hedge_ratio, 12),
                "half_life_days": round(statistical.half_life_days, 12),
                "passed": statistical.passed,
            },
            "backtest": {
                "config_hash": backtest.config_hash,
                "lock_file_hash": backtest.lock_file_hash,
                "random_seed": backtest.random_seed,
                "gross_pnl": round(backtest.gross_pnl, 12),
                "net_pnl": round(backtest.net_pnl, 12),
                "commission_cost": round(backtest.commission_cost, 12),
                "spread_cost": round(backtest.spread_cost, 12),
                "slippage_cost": round(backtest.slippage_cost, 12),
                "funding_cost": round(backtest.funding_cost, 12),
                "borrow_cost": round(backtest.borrow_cost, 12),
                "num_trades": backtest.num_trades,
                "turnover": round(backtest.turnover, 12),
                "sharpe_ratio": round(backtest.sharpe_ratio, 12),
                "sortino_ratio": round(backtest.sortino_ratio, 12),
                "max_drawdown": round(backtest.max_drawdown, 12),
                "win_rate": round(backtest.win_rate, 12),
                "profit_factor": round(backtest.profit_factor, 12),
                "baseline_sharpe": round(backtest.baseline_sharpe, 12),
            },
            "artifact_types": artifact_types,
            "task_statuses": task_statuses,
        }
    finally:
        session.close()
        engine.dispose()
