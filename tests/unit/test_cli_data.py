"""Unit tests for Task 15.1 data CLI commands."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from importlib import import_module
from pathlib import Path
from typing import Any
from uuid import uuid4

from click.testing import CliRunner

from stat_arb.cli import main
from stat_arb.storage import (
    BacktestResult,
    Base,
    CoordinatorTask,
    CriticReview,
    DataQualityReportRecord,
    Dataset,
    Experiment,
    Hypothesis,
    ReportArtifact,
    StatisticalTestResult,
    create_database_engine,
    create_session_factory,
)

cli_main = import_module("stat_arb.cli.main")


class FakeExchange:
    """Minimal fake exchange for CLI ingestion tests."""

    id = "fake"

    def __init__(self, rows: list[list[Any]]) -> None:
        self.rows = rows

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: int | None = None,
        limit: int | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[list[Any]]:
        return self.rows


def _row(timestamp: datetime, open_price: float = 100.0) -> list[Any]:
    return [
        int(timestamp.timestamp() * 1000),
        open_price,
        open_price + 2.0,
        open_price - 1.0,
        open_price + 1.0,
        10.0,
    ]


def test_data_list_reads_registry_datasets(tmp_path: Path) -> None:
    """data list should show persisted registry datasets."""
    db_path = tmp_path / "registry.db"
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    start = datetime(2024, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    try:
        session.add(
            Dataset(
                dataset_id=str(uuid4()),
                symbol="BTC/USDT",
                source="ccxt",
                timeframe="5m",
                start_date=start,
                end_date=start + timedelta(minutes=5),
                bar_count=2,
                missing_bars=0,
                outlier_count=0,
                quality_score=1.0,
                adjustment_mode="none",
                file_path="/tmp/btc.parquet",
            )
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    result = CliRunner().invoke(main, ["data", "list", "--db-path", str(db_path)])

    assert result.exit_code == 0, result.output
    assert "Найдено datasets: 1" in result.output
    assert "BTC/USDT" in result.output
    assert "quality=1.000000" in result.output


def test_data_validate_fetches_and_reports_quality_without_registry_write(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """data validate should fetch and validate a sample without writing registry rows."""
    rows = [
        _row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC), 100.0),
        _row(datetime(2024, 1, 1, 0, 5, tzinfo=UTC), 101.0),
    ]
    monkeypatch.setattr(
        cli_main,
        "CCXTOHLCVSource",
        lambda exchange_id: cli_main._CCXTOHLCVSource(
            exchange_id=exchange_id,
            exchange=FakeExchange(rows),
            sleep=lambda _: None,
        ),
    )
    db_path = tmp_path / "registry.db"

    result = CliRunner().invoke(
        main,
        [
            "data",
            "validate",
            "--exchange",
            "fake",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "5m",
            "--since",
            "2024-01-01T00:00:00+00:00",
            "--limit",
            "2",
            "--max-missing-bar-ratio",
            "0",
            "--max-abnormal-volume-ratio",
            "0",
            "--volume-spike-multiplier",
            "10",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Качество данных пройдено" in result.output
    assert not db_path.exists()


def test_data_download_persists_parquet_registry_and_sidecars(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """data download should use the guarded ingestion and registry persistence boundary."""
    rows = [
        _row(datetime(2024, 1, 1, 0, 0, tzinfo=UTC), 100.0),
        _row(datetime(2024, 1, 1, 0, 5, tzinfo=UTC), 101.0),
    ]
    monkeypatch.setattr(
        cli_main,
        "CCXTOHLCVSource",
        lambda exchange_id: cli_main._CCXTOHLCVSource(
            exchange_id=exchange_id,
            exchange=FakeExchange(rows),
            sleep=lambda _: None,
        ),
    )
    db_path = tmp_path / "registry.db"
    raw_root = tmp_path / "raw"
    metadata_root = tmp_path / "registry-sidecars"

    result = CliRunner().invoke(
        main,
        [
            "data",
            "download",
            "--exchange",
            "fake",
            "--symbol",
            "BTC/USDT",
            "--timeframe",
            "5m",
            "--since",
            "2024-01-01T00:00:00+00:00",
            "--limit",
            "2",
            "--raw-output-root",
            str(raw_root),
            "--metadata-root",
            str(metadata_root),
            "--db-path",
            str(db_path),
            "--max-missing-bar-ratio",
            "0",
            "--max-abnormal-volume-ratio",
            "0",
            "--volume-spike-multiplier",
            "10",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Dataset сохранен" in result.output
    assert "Quality report сохранен" in result.output
    assert list(raw_root.rglob("*.parquet"))
    assert list(metadata_root.rglob("*.metadata.json"))
    assert list(metadata_root.rglob("*.quality.json"))


def test_hypothesis_add_and_list_use_registry(tmp_path: Path) -> None:
    """hypothesis add should persist manual records and list should read them."""
    db_path = tmp_path / "registry.db"
    runner = CliRunner()

    add_result = runner.invoke(
        main,
        [
            "hypothesis",
            "add",
            "--asset-a",
            "BTC/USDT",
            "--asset-b",
            "ETH/USDT",
            "--rationale",
            "Manual crypto spread candidate",
            "--source",
            "user_provided",
            "--created-by",
            "operator",
            "--novelty-score",
            "0.75",
            "--status",
            "new",
            "--db-path",
            str(db_path),
        ],
    )

    assert add_result.exit_code == 0, add_result.output
    assert "Hypothesis сохранена" in add_result.output

    list_result = runner.invoke(main, ["hypothesis", "list", "--db-path", str(db_path)])

    assert list_result.exit_code == 0, list_result.output
    assert "Найдено hypotheses: 1" in list_result.output
    assert "BTC/USDT/ETH/USDT" in list_result.output
    assert "novelty=0.750000" in list_result.output


def test_hypothesis_generate_uses_rule_based_agent_boundary(tmp_path: Path) -> None:
    """hypothesis generate should persist candidates through Hypothesis Agent config."""
    db_path = tmp_path / "registry.db"
    assets_path = tmp_path / "assets.json"
    correlations_path = tmp_path / "correlations.json"
    p_values_path = tmp_path / "p_values.json"
    assets_path.write_text(
        """
        [
          {"symbol": "AAA", "sector": "Banks", "market_cap": 100000000000},
          {"symbol": "BBB", "sector": "Banks", "market_cap": 95000000000},
          {"symbol": "CCC", "sector": "Energy", "market_cap": 120000000000}
        ]
        """,
        encoding="utf-8",
    )
    correlations_path.write_text(
        """
        [
          {"asset_a": "AAA", "asset_b": "BBB", "correlation": 0.93},
          {"asset_a": "AAA", "asset_b": "CCC", "correlation": 0.98}
        ]
        """,
        encoding="utf-8",
    )
    p_values_path.write_text(
        """
        [
          {"asset_a": "AAA", "asset_b": "BBB", "p_value": 0.01},
          {"asset_a": "AAA", "asset_b": "CCC", "p_value": 0.01}
        ]
        """,
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        main,
        [
            "hypothesis",
            "generate",
            "--assets-json",
            str(assets_path),
            "--correlations-json",
            str(correlations_path),
            "--p-values-json",
            str(p_values_path),
            "--require-same-sector",
            "--min-abs-correlation",
            "0.85",
            "--min-market-cap",
            "50000000000",
            "--max-market-cap",
            "150000000000",
            "--max-pairs",
            "5",
            "--multiple-testing-method",
            "bonferroni",
            "--candidate-alpha",
            "0.05",
            "--initial-novelty-score",
            "1.0",
            "--initial-status",
            "new",
            "--source",
            "rule_based",
            "--created-by",
            "hypothesis_agent",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Hypotheses generated: 1" in result.output
    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        stored = session.query(Hypothesis).one()
        assert stored.asset_a == "AAA"
        assert stored.asset_b == "BBB"
        assert stored.source == "rule_based"
        assert stored.created_by == "hypothesis_agent"
    finally:
        session.close()
        engine.dispose()


def test_hypothesis_generate_accepts_utf8_bom_json_inputs(tmp_path: Path) -> None:
    """hypothesis generate should accept JSON files commonly written by Windows tools."""
    db_path = tmp_path / "registry.db"
    assets_path = tmp_path / "assets.json"
    correlations_path = tmp_path / "correlations.json"
    p_values_path = tmp_path / "p_values.json"
    assets_path.write_text(
        '[{"symbol":"AAA","sector":"Banks","market_cap":100000000000},'
        '{"symbol":"BBB","sector":"Banks","market_cap":95000000000}]',
        encoding="utf-8-sig",
    )
    correlations_path.write_text(
        '[{"asset_a":"AAA","asset_b":"BBB","correlation":0.93}]',
        encoding="utf-8-sig",
    )
    p_values_path.write_text(
        '[{"asset_a":"AAA","asset_b":"BBB","p_value":0.01}]',
        encoding="utf-8-sig",
    )

    result = CliRunner().invoke(
        main,
        [
            "hypothesis",
            "generate",
            "--assets-json",
            str(assets_path),
            "--correlations-json",
            str(correlations_path),
            "--p-values-json",
            str(p_values_path),
            "--require-same-sector",
            "--min-abs-correlation",
            "0.85",
            "--min-market-cap",
            "50000000000",
            "--max-pairs",
            "5",
            "--multiple-testing-method",
            "bonferroni",
            "--candidate-alpha",
            "0.05",
            "--initial-novelty-score",
            "1.0",
            "--initial-status",
            "new",
            "--source",
            "rule_based",
            "--created-by",
            "hypothesis_agent",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Hypotheses generated: 1" in result.output


def test_experiment_list_reads_registry_lifecycle_rows(tmp_path: Path) -> None:
    """experiment list should expose registry lifecycle state without running agents."""
    db_path = tmp_path / "registry.db"
    experiment_id = _seed_cli_experiment(db_path, status="data_validation")

    result = CliRunner().invoke(main, ["experiment", "list", "--db-path", str(db_path)])

    assert result.exit_code == 0, result.output
    assert "Найдено experiments: 1" in result.output
    assert experiment_id in result.output
    assert "data_validation" in result.output
    assert "data_agent" in result.output


def test_experiment_status_shows_single_experiment_and_hypothesis_pair(tmp_path: Path) -> None:
    """experiment status should show one experiment with its hypothesis context."""
    db_path = tmp_path / "registry.db"
    experiment_id = _seed_cli_experiment(db_path, status="backtesting")

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "status",
            "--experiment-id",
            experiment_id,
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert f"Experiment: {experiment_id}" in result.output
    assert "Status: backtesting" in result.output
    assert "Current agent: backtest_agent" in result.output
    assert "Pair: AAA/BBB" in result.output


def test_experiment_advance_uses_coordinator_lifecycle_boundary(tmp_path: Path) -> None:
    """experiment advance should use Coordinator transitions instead of manual status writes."""
    db_path = tmp_path / "registry.db"
    experiment_id = _seed_cli_experiment(db_path, status="new")

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "advance",
            "--experiment-id",
            experiment_id,
            "--target-status",
            "data_validation",
            "--reason",
            "Operator starts validated data stage.",
            "--actor",
            "cli_operator",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Experiment обновлен" in result.output
    assert "new -> data_validation" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        stored = session.get(Experiment, experiment_id)
        assert stored is not None
        assert stored.status == "data_validation"
        assert stored.current_agent == "data_agent"
    finally:
        session.close()
        engine.dispose()


def test_experiment_advance_rejects_invalid_lifecycle_jump(tmp_path: Path) -> None:
    """experiment advance should fail closed on invalid Coordinator transitions."""
    db_path = tmp_path / "registry.db"
    experiment_id = _seed_cli_experiment(db_path, status="new")

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "advance",
            "--experiment-id",
            experiment_id,
            "--target-status",
            "backtesting",
            "--reason",
            "Skipping stages would be unsafe.",
            "--actor",
            "cli_operator",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code != 0
    assert "Invalid lifecycle transition" in result.output


def test_experiment_run_stage_enqueues_task_and_advances_lifecycle(tmp_path: Path) -> None:
    """experiment run-stage should queue explicit stage work through Coordinator contracts."""
    db_path = tmp_path / "registry.db"
    payload_path = tmp_path / "payload.json"
    payload_path.write_text('{"dataset_ids": ["dataset-a", "dataset-b"]}', encoding="utf-8")
    experiment_id = _seed_cli_experiment(db_path, status="data_validation")

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "run-stage",
            "--experiment-id",
            experiment_id,
            "--stage",
            "statistical_testing",
            "--task-type",
            "run_statistical_tests",
            "--agent-name",
            "statistical_testing_agent",
            "--priority",
            "2",
            "--max-attempts",
            "3",
            "--payload-json",
            str(payload_path),
            "--advance-lifecycle",
            "--reason",
            "Queue statistical testing after data validation.",
            "--actor",
            "cli_operator",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Stage task поставлен в очередь" in result.output
    assert "data_validation -> statistical_testing" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        stored_task = session.query(CoordinatorTask).one()
        assert stored_task.experiment_id == experiment_id
        assert stored_task.task_type == "run_statistical_tests"
        assert stored_task.agent_name == "statistical_testing_agent"
        assert stored_task.priority == 2
        assert stored_task.max_attempts == 3
        assert stored_task.status == "pending"
        assert stored_task.payload == {"dataset_ids": ["dataset-a", "dataset-b"]}
        stored_experiment = session.get(Experiment, experiment_id)
        assert stored_experiment is not None
        assert stored_experiment.status == "statistical_testing"
        assert stored_experiment.current_agent == "statistical_testing_agent"
    finally:
        session.close()
        engine.dispose()


def test_experiment_run_stage_can_queue_without_lifecycle_advance(tmp_path: Path) -> None:
    """experiment run-stage should not mutate lifecycle unless explicitly requested."""
    db_path = tmp_path / "registry.db"
    payload_path = tmp_path / "payload.json"
    payload_path.write_text("{}", encoding="utf-8")
    experiment_id = _seed_cli_experiment(db_path, status="backtesting")

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "run-stage",
            "--experiment-id",
            experiment_id,
            "--stage",
            "backtesting",
            "--task-type",
            "run_backtest",
            "--agent-name",
            "backtest_agent",
            "--priority",
            "1",
            "--max-attempts",
            "2",
            "--payload-json",
            str(payload_path),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Lifecycle не изменен" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        assert session.query(CoordinatorTask).count() == 1
        stored_experiment = session.get(Experiment, experiment_id)
        assert stored_experiment is not None
        assert stored_experiment.status == "backtesting"
    finally:
        session.close()
        engine.dispose()


def test_experiment_run_stage_rejects_mismatched_agent_for_stage(tmp_path: Path) -> None:
    """experiment run-stage should not queue work for the wrong agent/stage pairing."""
    db_path = tmp_path / "registry.db"
    payload_path = tmp_path / "payload.json"
    payload_path.write_text("{}", encoding="utf-8")
    experiment_id = _seed_cli_experiment(db_path, status="data_validation")

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "run-stage",
            "--experiment-id",
            experiment_id,
            "--stage",
            "statistical_testing",
            "--task-type",
            "run_statistical_tests",
            "--agent-name",
            "backtest_agent",
            "--priority",
            "1",
            "--max-attempts",
            "1",
            "--payload-json",
            str(payload_path),
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code != 0
    assert "agent-name не соответствует stage" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        assert session.query(CoordinatorTask).count() == 0
        stored_experiment = session.get(Experiment, experiment_id)
        assert stored_experiment is not None
        assert stored_experiment.status == "data_validation"
    finally:
        session.close()
        engine.dispose()


def test_experiment_execute_stage_runs_statistical_testing_and_completes_task(
    tmp_path: Path,
) -> None:
    """experiment execute-stage should run a queued statistical_testing task through service."""
    db_path = tmp_path / "registry.db"
    task_id = _seed_statistical_testing_task(db_path)

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "execute-stage",
            "--task-id",
            task_id,
            "--stage",
            "statistical_testing",
            "--max-running-tasks",
            "1",
            "--max-running-tasks-per-agent",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Stage выполнен: statistical_testing" in result.output
    assert "Task completed" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        stored_task = session.get(CoordinatorTask, task_id)
        assert stored_task is not None
        assert stored_task.status == "completed"
        assert stored_task.attempt_count == 1
        assert stored_task.completed_at is not None
        stored_result = session.query(StatisticalTestResult).one()
        assert isinstance(stored_result.passed, bool)
        assert stored_result.hypothesis_id == stored_task.payload["hypothesis_id"]
    finally:
        session.close()
        engine.dispose()


def test_experiment_execute_stage_rejects_report_stage_without_factual_artifacts(
    tmp_path: Path,
) -> None:
    """experiment execute-stage should not create reports from aggregate-only inputs."""
    db_path = tmp_path / "registry.db"
    task_id = _seed_reporting_task(db_path, output_dir=tmp_path / "reports", with_series=False)

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "execute-stage",
            "--task-id",
            task_id,
            "--stage",
            "reporting",
            "--max-running-tasks",
            "1",
            "--max-running-tasks-per-agent",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code != 0
    assert "matching backtest_series sidecar is required" in result.output


def test_experiment_execute_stage_runs_reporting_with_factual_sidecar(
    tmp_path: Path,
) -> None:
    """experiment execute-stage should run Report Agent only from factual sidecars."""
    db_path = tmp_path / "registry.db"
    task_id = _seed_reporting_task(db_path, output_dir=tmp_path / "reports", with_series=True)

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "execute-stage",
            "--task-id",
            task_id,
            "--stage",
            "reporting",
            "--max-running-tasks",
            "1",
            "--max-running-tasks-per-agent",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Stage выполнен: reporting" in result.output
    assert "Task completed" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        stored_task = session.get(CoordinatorTask, task_id)
        assert stored_task is not None
        assert stored_task.status == "completed"
        artifact_types = {row.artifact_type for row in session.query(ReportArtifact).all()}
        assert "backtest_series" in artifact_types
        assert "backtest_report" in artifact_types
        assert "equity_curve" in artifact_types
        assert "z_score_signals" in artifact_types
    finally:
        session.close()
        engine.dispose()


def test_experiment_execute_stage_runs_backtesting_and_completes_task(
    tmp_path: Path,
) -> None:
    """experiment execute-stage should run a queued backtesting task through service."""
    db_path = tmp_path / "registry.db"
    lock_path = tmp_path / "uv.lock"
    lock_path.write_text("package==1.0\n", encoding="utf-8")
    task_id = _seed_backtesting_task(db_path, lock_path=lock_path)

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "execute-stage",
            "--task-id",
            task_id,
            "--stage",
            "backtesting",
            "--max-running-tasks",
            "1",
            "--max-running-tasks-per-agent",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Stage выполнен: backtesting" in result.output
    assert "Task completed" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        stored_task = session.get(CoordinatorTask, task_id)
        assert stored_task is not None
        assert stored_task.status == "completed"
        assert stored_task.attempt_count == 1
        stored_result = session.query(BacktestResult).one()
        assert stored_result.test_id == stored_task.payload["test_id"]
        assert stored_result.execution_command == ["stat-arb", "experiment", "execute-stage"]
        stored_artifact = session.query(ReportArtifact).one()
        assert stored_artifact.experiment_id == stored_task.experiment_id
        assert stored_artifact.artifact_type == "backtest_series"
        assert stored_artifact.format == "json"
        assert Path(stored_artifact.file_path).exists()
    finally:
        session.close()
        engine.dispose()


def test_experiment_run_pipeline_executes_backtesting_then_reporting_from_sidecar(
    tmp_path: Path,
) -> None:
    """experiment run-pipeline should chain backtesting sidecar into reporting."""
    db_path = tmp_path / "registry.db"
    lock_path = tmp_path / "uv.lock"
    lock_path.write_text("package==1.0\n", encoding="utf-8")
    task_id = _seed_backtesting_task(db_path, lock_path=lock_path)

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        task = session.get(CoordinatorTask, task_id)
        assert task is not None
        experiment_id = task.experiment_id
    finally:
        session.close()
        engine.dispose()

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "run-pipeline",
            "--experiment-id",
            experiment_id,
            "--stages",
            "backtesting,reporting",
            "--report-output-dir",
            str(tmp_path / "reports"),
            "--max-running-tasks",
            "1",
            "--max-running-tasks-per-agent",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Pipeline stage выполнен: backtesting" in result.output
    assert "Pipeline stage выполнен: reporting" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        tasks = session.query(CoordinatorTask).order_by(CoordinatorTask.created_at.asc()).all()
        assert [task.status for task in tasks] == ["completed", "completed"]
        assert [task.task_type for task in tasks] == ["run_backtest", "write_report"]
        artifact_types = {row.artifact_type for row in session.query(ReportArtifact).all()}
        assert "backtest_series" in artifact_types
        assert "backtest_report" in artifact_types
        assert "equity_curve" in artifact_types
    finally:
        session.close()
        engine.dispose()


def test_experiment_run_pipeline_stops_before_reporting_without_sidecar(
    tmp_path: Path,
) -> None:
    """experiment run-pipeline should fail closed if backtesting leaves no sidecar."""
    db_path = tmp_path / "registry.db"
    lock_path = tmp_path / "uv.lock"
    lock_path.write_text("package==1.0\n", encoding="utf-8")
    task_id = _seed_backtesting_task(db_path, lock_path=lock_path)

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        task = session.get(CoordinatorTask, task_id)
        assert task is not None
        experiment_id = task.experiment_id
        payload = dict(task.payload)
        del payload["artifact_output_dir"]
        del payload["series"]
        task.payload = payload
        session.commit()
    finally:
        session.close()
        engine.dispose()

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "run-pipeline",
            "--experiment-id",
            experiment_id,
            "--stages",
            "backtesting,reporting",
            "--report-output-dir",
            str(tmp_path / "reports"),
            "--max-running-tasks",
            "1",
            "--max-running-tasks-per-agent",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code != 0
    assert "backtest_series sidecar is required before reporting pipeline stage" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        tasks = session.query(CoordinatorTask).all()
        assert len(tasks) == 1
        assert tasks[0].status == "completed"
        artifact_types = {row.artifact_type for row in session.query(ReportArtifact).all()}
        assert "backtest_series" not in artifact_types
        assert "backtest_report" not in artifact_types
    finally:
        session.close()
        engine.dispose()


def test_experiment_execute_stage_runs_critic_review_and_completes_task(
    tmp_path: Path,
) -> None:
    """experiment execute-stage should run a queued critic_review task through service."""
    db_path = tmp_path / "registry.db"
    task_id = _seed_critic_review_task(db_path)

    result = CliRunner().invoke(
        main,
        [
            "experiment",
            "execute-stage",
            "--task-id",
            task_id,
            "--stage",
            "critic_review",
            "--max-running-tasks",
            "1",
            "--max-running-tasks-per-agent",
            "1",
            "--db-path",
            str(db_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Stage выполнен: critic_review" in result.output
    assert "Task completed" in result.output

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        stored_task = session.get(CoordinatorTask, task_id)
        assert stored_task is not None
        assert stored_task.status == "completed"
        assert stored_task.attempt_count == 1
        stored_review = session.query(CriticReview).one()
        assert stored_review.backtest_id == stored_task.payload["backtest_id"]
        assert stored_review.status == "rejected"
        assert stored_review.lookahead_bias_detected is True
        assert stored_review.overfitting_indicators == ["sharpe_degradation: unstable"]
        assert stored_review.weak_assumptions == [
            "cointegration_p_value_proximity: near alpha"
        ]
        assert stored_review.insufficient_testing == [
            "minimum_walk_forward_windows: too few"
        ]
        assert stored_review.cost_concerns == ["negative_net_pnl_after_costs: loss"]
        assert stored_review.operational_concerns == ["manual review required"]
        assert "signal_lookahead" in stored_review.objections
    finally:
        session.close()
        engine.dispose()


def _seed_cli_experiment(db_path: Path, *, status: str) -> str:
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    hypothesis_id = str(uuid4())
    experiment_id = str(uuid4())
    try:
        session.add(
            Hypothesis(
                hypothesis_id=hypothesis_id,
                asset_a="AAA",
                asset_b="BBB",
                rationale="Synthetic CLI experiment pair",
                source="unit-test",
                created_by="pytest",
                created_at=datetime(2024, 1, 1, tzinfo=UTC).replace(tzinfo=None),
            )
        )
        session.add(
            Experiment(
                experiment_id=experiment_id,
                hypothesis_id=hypothesis_id,
                status=status,
                current_agent=_agent_for_cli_status(status),
            )
        )
        session.commit()
        return experiment_id
    finally:
        session.close()
        engine.dispose()


def _agent_for_cli_status(status: str) -> str | None:
    return {
        "new": None,
        "data_validation": "data_agent",
        "statistical_testing": "statistical_testing_agent",
        "backtesting": "backtest_agent",
        "critic_review": "critic_agent",
        "reporting": "report_agent",
        "final_decision": None,
    }[status]


def _seed_cli_task(
    db_path: Path,
    *,
    experiment_id: str,
    task_type: str,
    agent_name: str,
    payload: dict[str, object],
) -> str:
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    task_id = str(uuid4())
    try:
        session.add(
            CoordinatorTask(
                task_id=task_id,
                experiment_id=experiment_id,
                task_type=task_type,
                agent_name=agent_name,
                priority=1,
                status="pending",
                attempt_count=0,
                max_attempts=2,
                payload=payload,
            )
        )
        session.commit()
        return task_id
    finally:
        session.close()
        engine.dispose()


def _seed_statistical_testing_task(db_path: Path) -> str:
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    start = datetime(2024, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    hypothesis_id = str(uuid4())
    dataset_a_id = str(uuid4())
    dataset_b_id = str(uuid4())
    experiment_id = str(uuid4())
    task_id = str(uuid4())
    prices_a, prices_b, timestamps = _cli_cointegrated_pair(start)
    try:
        session.add(
            Hypothesis(
                hypothesis_id=hypothesis_id,
                asset_a="AAA",
                asset_b="BBB",
                rationale="Synthetic statistical testing pair",
                source="unit-test",
                created_by="pytest",
                created_at=start,
            )
        )
        session.add_all(
            [
                Dataset(
                    dataset_id=dataset_a_id,
                    symbol="AAA",
                    source="unit-test",
                    timeframe="15m",
                    start_date=start,
                    end_date=timestamps[-1],
                    bar_count=len(timestamps),
                    adjustment_mode="none",
                    file_path="/tmp/aaa.parquet",
                ),
                Dataset(
                    dataset_id=dataset_b_id,
                    symbol="BBB",
                    source="unit-test",
                    timeframe="15m",
                    start_date=start,
                    end_date=timestamps[-1],
                    bar_count=len(timestamps),
                    adjustment_mode="none",
                    file_path="/tmp/bbb.parquet",
                ),
            ]
        )
        session.add_all(
            [
                _cli_quality_report(dataset_a_id, "AAA", start, timestamps[-1], len(timestamps)),
                _cli_quality_report(dataset_b_id, "BBB", start, timestamps[-1], len(timestamps)),
            ]
        )
        session.add(
            Experiment(
                experiment_id=experiment_id,
                hypothesis_id=hypothesis_id,
                status="statistical_testing",
                current_agent="statistical_testing_agent",
            )
        )
        session.add(
            CoordinatorTask(
                task_id=task_id,
                experiment_id=experiment_id,
                task_type="run_statistical_tests",
                agent_name="statistical_testing_agent",
                priority=1,
                status="pending",
                attempt_count=0,
                max_attempts=2,
                payload={
                    "hypothesis_id": hypothesis_id,
                    "dataset_a_id": dataset_a_id,
                    "dataset_b_id": dataset_b_id,
                    "prices_a": prices_a,
                    "prices_b": prices_b,
                    "aligned_timestamps": [
                        timestamp.isoformat() for timestamp in timestamps
                    ],
                    "train_fraction": 0.7,
                    "alpha": 0.05,
                    "adf_regression": "c",
                    "adf_autolag": "AIC",
                    "periods_per_day": 96.0,
                    "residual_diagnostics_lags": 10,
                    "regime_window": 60,
                    "regime_mean_shift_threshold": 3.0,
                    "regime_volatility_ratio_threshold": 2.5,
                },
            )
        )
        session.commit()
        return task_id
    finally:
        session.close()
        engine.dispose()


def _seed_backtesting_task(db_path: Path, *, lock_path: Path) -> str:
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    start = datetime(2024, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    hypothesis_id = str(uuid4())
    dataset_a_id = str(uuid4())
    dataset_b_id = str(uuid4())
    experiment_id = str(uuid4())
    test_id = str(uuid4())
    task_id = str(uuid4())
    prices_a, prices_b, timestamps = _cli_backtest_pair(start)
    try:
        session.add(
            Hypothesis(
                hypothesis_id=hypothesis_id,
                asset_a="AAA",
                asset_b="BBB",
                rationale="Synthetic backtesting pair",
                source="unit-test",
                created_by="pytest",
                created_at=start,
            )
        )
        session.add_all(
            [
                Dataset(
                    dataset_id=dataset_a_id,
                    symbol="AAA",
                    source="unit-test",
                    timeframe="15m",
                    start_date=start,
                    end_date=timestamps[-1],
                    bar_count=len(timestamps),
                    adjustment_mode="none",
                    file_path="/tmp/aaa.parquet",
                ),
                Dataset(
                    dataset_id=dataset_b_id,
                    symbol="BBB",
                    source="unit-test",
                    timeframe="15m",
                    start_date=start,
                    end_date=timestamps[-1],
                    bar_count=len(timestamps),
                    adjustment_mode="none",
                    file_path="/tmp/bbb.parquet",
                ),
            ]
        )
        session.add_all(
            [
                _cli_quality_report(dataset_a_id, "AAA", start, timestamps[-1], len(timestamps)),
                _cli_quality_report(dataset_b_id, "BBB", start, timestamps[-1], len(timestamps)),
            ]
        )
        session.add(
            StatisticalTestResult(
                test_id=test_id,
                hypothesis_id=hypothesis_id,
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
                train_start=start,
                train_end=start + timedelta(days=1),
                test_start=start + timedelta(days=1),
                test_end=timestamps[-1],
                cointegration_statistic=-3.5,
                cointegration_p_value=0.01,
                adf_statistic=-4.0,
                adf_p_value=0.01,
                hedge_ratio=1.0,
                hedge_ratio_r_squared=0.9,
                half_life_days=2.0,
                residual_ljung_box_p_value=0.5,
                residual_jarque_bera_p_value=0.5,
                residual_excess_kurtosis=0.1,
                residual_diagnostics_lags=10,
                regime_changes_detected=False,
                passed=True,
            )
        )
        session.add(
            Experiment(
                experiment_id=experiment_id,
                hypothesis_id=hypothesis_id,
                status="backtesting",
                current_agent="backtest_agent",
            )
        )
        session.add(
            CoordinatorTask(
                task_id=task_id,
                experiment_id=experiment_id,
                task_type="run_backtest",
                agent_name="backtest_agent",
                priority=1,
                status="pending",
                attempt_count=0,
                max_attempts=2,
                payload={
                    "hypothesis_id": hypothesis_id,
                    "test_id": test_id,
                    "dataset_a_id": dataset_a_id,
                    "dataset_b_id": dataset_b_id,
                    "prices_a": prices_a,
                    "prices_b": prices_b,
                    "z_scores": [0.0, 2.2, 1.2, 0.2, -2.1, 0.0],
                    "aligned_timestamps": [
                        timestamp.isoformat() for timestamp in timestamps
                    ],
                    "hedge_ratio": 1.0,
                    "entry_threshold": 2.0,
                    "exit_threshold": 0.5,
                    "exit_policy": None,
                    "risk_exit_policy_disabled_reason": "unit test uses convergence-only exits",
                    "cost_config": {
                        "commission_rate": 0.001,
                        "spread_cost_rate": 0.0005,
                        "slippage_rate": 0.0002,
                        "funding_rate_daily": 0.0001,
                        "borrow_rate_annual": 0.005,
                        "status": "verified",
                        "source": "unit-test",
                        "verified_at": "2024-01-01T00:00:00+00:00",
                        "venue": "test-exchange",
                        "market_type": "perpetual",
                        "notes": "synthetic CLI fixture",
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
                        "execution_command": [
                            "stat-arb",
                            "experiment",
                            "execute-stage",
                        ],
                        "run_timestamp": "2024-01-02T00:00:00+00:00",
                        "lock_file_path": str(lock_path),
                    },
                    "train_window_days": 60,
                    "test_window_days": 30,
                    "num_windows": 2,
                    "artifact_output_dir": str(lock_path.parent / "backtest-artifacts"),
                    "series": {
                        "timestamps": [
                            timestamp.isoformat() for timestamp in timestamps
                        ],
                        "equity_curve": [100.0, 102.0, 100.98, 102.49, 103.0, 103.25],
                        "drawdown_curve": [0.0, 0.0, 0.01, 0.0, 0.0, 0.0],
                        "z_scores": [0.0, 2.2, 1.2, 0.2, -2.1, 0.0],
                        "entry_markers": [1, 4],
                        "exit_markers": [3, 5],
                        "rolling_sharpe": [0.0, 0.1, 0.2, 0.3, 0.2, 0.4],
                        "trade_pnls": [5.0, -2.0],
                    },
                },
            )
        )
        session.commit()
        return task_id
    finally:
        session.close()
        engine.dispose()


def _seed_critic_review_task(db_path: Path) -> str:
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    start = datetime(2024, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    hypothesis_id = str(uuid4())
    dataset_a_id = str(uuid4())
    dataset_b_id = str(uuid4())
    test_id = str(uuid4())
    backtest_id = str(uuid4())
    experiment_id = str(uuid4())
    task_id = str(uuid4())
    try:
        session.add(
            Hypothesis(
                hypothesis_id=hypothesis_id,
                asset_a="AAA",
                asset_b="BBB",
                rationale="Synthetic critic review pair",
                source="unit-test",
                created_by="pytest",
                created_at=start,
            )
        )
        session.add_all(
            [
                Dataset(
                    dataset_id=dataset_a_id,
                    symbol="AAA",
                    source="unit-test",
                    timeframe="15m",
                    start_date=start,
                    end_date=start + timedelta(days=2),
                    bar_count=240,
                    adjustment_mode="none",
                    file_path="/tmp/aaa.parquet",
                ),
                Dataset(
                    dataset_id=dataset_b_id,
                    symbol="BBB",
                    source="unit-test",
                    timeframe="15m",
                    start_date=start,
                    end_date=start + timedelta(days=2),
                    bar_count=240,
                    adjustment_mode="none",
                    file_path="/tmp/bbb.parquet",
                ),
            ]
        )
        session.flush()
        session.add(
            StatisticalTestResult(
                test_id=test_id,
                hypothesis_id=hypothesis_id,
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
                train_start=start,
                train_end=start + timedelta(days=1),
                test_start=start + timedelta(days=1),
                test_end=start + timedelta(days=2),
                cointegration_statistic=-3.5,
                cointegration_p_value=0.01,
                adf_statistic=-4.0,
                adf_p_value=0.01,
                hedge_ratio=1.0,
                hedge_ratio_r_squared=0.9,
                half_life_days=2.0,
                residual_ljung_box_p_value=0.5,
                residual_jarque_bera_p_value=0.5,
                residual_excess_kurtosis=0.1,
                residual_diagnostics_lags=10,
                regime_changes_detected=False,
                passed=True,
            )
        )
        session.flush()
        session.add(
            BacktestResult(
                backtest_id=backtest_id,
                hypothesis_id=hypothesis_id,
                test_id=test_id,
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
                git_commit_hash="abcdef1",
                config_hash="a" * 64,
                dataset_ids=[dataset_a_id, dataset_b_id],
                random_seed=12345,
                execution_command=["uv", "run", "stat-arb", "backtest"],
                run_timestamp=start,
                lock_file_hash="f" * 64,
                execution_time_seconds=12.5,
                train_window_days=60,
                test_window_days=30,
                num_windows=2,
                entry_threshold=2.0,
                exit_threshold=0.5,
                hedge_ratio=1.0,
                gross_pnl=100.0,
                net_pnl=80.0,
                commission_cost=5.0,
                spread_cost=3.0,
                slippage_cost=2.0,
                funding_cost=1.0,
                borrow_cost=1.0,
                num_trades=4,
                turnover=1.2,
                avg_holding_time_hours=12.0,
                median_holding_time_hours=10.0,
                sharpe_ratio=1.1,
                sortino_ratio=1.3,
                volatility=0.2,
                max_drawdown=0.1,
                win_rate=0.6,
                profit_factor=1.5,
                net_pnl_2x_costs=60.0,
                net_pnl_half_costs=90.0,
                baseline_sharpe=0.5,
                tested_at=start,
            )
        )
        session.add(
            Experiment(
                experiment_id=experiment_id,
                hypothesis_id=hypothesis_id,
                status="critic_review",
                current_agent="critic_agent",
            )
        )
        session.add(
            CoordinatorTask(
                task_id=task_id,
                experiment_id=experiment_id,
                task_type="run_critic_review",
                agent_name="critic_agent",
                priority=1,
                status="pending",
                attempt_count=0,
                max_attempts=2,
                payload={
                    "backtest_id": backtest_id,
                    "lookahead": {
                        "lookahead_bias_detected": True,
                        "issues": ["signal_lookahead: future bar used"],
                        "checked_rules": ["strictly_past_signals"],
                    },
                    "overfitting": {
                        "overfitting_detected": True,
                        "indicators": ["sharpe_degradation: unstable"],
                        "checked_rules": ["sharpe_degradation"],
                    },
                    "weak_assumptions": {
                        "weak_assumptions_detected": True,
                        "indicators": [
                            "cointegration_p_value_proximity: near alpha"
                        ],
                        "checked_rules": ["cointegration_p_value_proximity"],
                    },
                    "insufficient_testing": {
                        "insufficient_testing_detected": True,
                        "indicators": ["minimum_walk_forward_windows: too few"],
                        "checked_rules": ["minimum_walk_forward_windows"],
                    },
                    "cost_realism": {
                        "cost_realism_concerns_detected": True,
                        "indicators": ["negative_net_pnl_after_costs: loss"],
                        "checked_rules": ["negative_net_pnl_after_costs"],
                    },
                    "decision": {
                        "status": "rejected",
                        "recommendation": "Reject",
                        "objections": ["signal_lookahead: future bar used"],
                    },
                    "operational_concerns": ["manual review required"],
                },
            )
        )
        session.commit()
        return task_id
    finally:
        session.close()
        engine.dispose()


def _seed_reporting_task(db_path: Path, *, output_dir: Path, with_series: bool) -> str:
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    start = datetime(2024, 1, 1, tzinfo=UTC).replace(tzinfo=None)
    hypothesis_id = str(uuid4())
    dataset_a_id = str(uuid4())
    dataset_b_id = str(uuid4())
    test_id = str(uuid4())
    backtest_id = str(uuid4())
    experiment_id = str(uuid4())
    task_id = str(uuid4())
    try:
        session.add(
            Hypothesis(
                hypothesis_id=hypothesis_id,
                asset_a="AAA",
                asset_b="BBB",
                rationale="Synthetic reporting pair",
                source="unit-test",
                created_by="pytest",
                created_at=start,
            )
        )
        session.add_all(
            [
                Dataset(
                    dataset_id=dataset_a_id,
                    symbol="AAA",
                    source="unit-test",
                    timeframe="15m",
                    start_date=start,
                    end_date=start + timedelta(days=2),
                    bar_count=192,
                    adjustment_mode="none",
                    file_path="/tmp/a.parquet",
                ),
                Dataset(
                    dataset_id=dataset_b_id,
                    symbol="BBB",
                    source="unit-test",
                    timeframe="15m",
                    start_date=start,
                    end_date=start + timedelta(days=2),
                    bar_count=192,
                    adjustment_mode="none",
                    file_path="/tmp/b.parquet",
                ),
            ]
        )
        session.add_all(
            [
                _cli_quality_report(dataset_a_id, "AAA", start, start + timedelta(days=2), 192),
                _cli_quality_report(dataset_b_id, "BBB", start, start + timedelta(days=2), 192),
            ]
        )
        session.add(
            StatisticalTestResult(
                test_id=test_id,
                hypothesis_id=hypothesis_id,
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
                train_start=start,
                train_end=start + timedelta(days=1),
                test_start=start + timedelta(days=1),
                test_end=start + timedelta(days=2),
                cointegration_statistic=-3.5,
                cointegration_p_value=0.01,
                adf_statistic=-4.0,
                adf_p_value=0.02,
                hedge_ratio=1.2,
                hedge_ratio_r_squared=0.9,
                half_life_days=12.0,
                residual_ljung_box_p_value=0.5,
                residual_jarque_bera_p_value=0.5,
                residual_excess_kurtosis=0.1,
                residual_diagnostics_lags=10,
                regime_changes_detected=False,
                passed=True,
            )
        )
        session.flush()
        session.add(
            BacktestResult(
                backtest_id=backtest_id,
                hypothesis_id=hypothesis_id,
                test_id=test_id,
                dataset_a_id=dataset_a_id,
                dataset_b_id=dataset_b_id,
                git_commit_hash="abcdef1",
                config_hash="b" * 64,
                dataset_ids=[dataset_a_id, dataset_b_id],
                random_seed=12345,
                execution_command=["stat-arb", "experiment", "execute-stage"],
                run_timestamp=start,
                lock_file_hash="f" * 64,
                execution_time_seconds=12.5,
                train_window_days=60,
                test_window_days=30,
                num_windows=2,
                entry_threshold=2.0,
                exit_threshold=0.5,
                hedge_ratio=1.2,
                gross_pnl=10.0,
                net_pnl=8.5,
                commission_cost=0.5,
                spread_cost=0.5,
                slippage_cost=0.3,
                funding_cost=0.1,
                borrow_cost=0.1,
                num_trades=4,
                turnover=2.0,
                avg_holding_time_hours=12.0,
                median_holding_time_hours=10.0,
                sharpe_ratio=1.1,
                sortino_ratio=1.3,
                volatility=0.2,
                max_drawdown=0.02,
                win_rate=0.6,
                profit_factor=1.8,
                net_pnl_2x_costs=7.0,
                net_pnl_half_costs=9.2,
                baseline_sharpe=0.2,
                tested_at=start,
            )
        )
        session.add(
            Experiment(
                experiment_id=experiment_id,
                hypothesis_id=hypothesis_id,
                status="reporting",
                current_agent="report_agent",
            )
        )
        session.add(
            CoordinatorTask(
                task_id=task_id,
                experiment_id=experiment_id,
                task_type="write_report",
                agent_name="report_agent",
                priority=1,
                status="pending",
                attempt_count=0,
                max_attempts=2,
                payload={"backtest_id": backtest_id, "output_dir": str(output_dir)},
            )
        )
        if with_series:
            series_path = output_dir.parent / "series" / f"backtest-{backtest_id}.series.json"
            series_path.parent.mkdir(parents=True, exist_ok=True)
            series_path.write_text(
                """
                {
                  "backtest_id": "__BACKTEST_ID__",
                  "timestamps": [
                    "2024-01-01T00:00:00+00:00",
                    "2024-01-01T00:15:00+00:00",
                    "2024-01-01T00:30:00+00:00"
                  ],
                  "equity_curve": [100.0, 101.0, 102.0],
                  "drawdown_curve": [0.0, 0.0, 0.0],
                  "z_scores": [0.0, 2.1, 0.4],
                  "entry_markers": [1],
                  "exit_markers": [2],
                  "rolling_sharpe": [0.0, 0.2, 0.3],
                  "trade_pnls": [2.0]
                }
                """.replace("__BACKTEST_ID__", backtest_id),
                encoding="utf-8",
            )
            session.add(
                ReportArtifact(
                    experiment_id=experiment_id,
                    artifact_type="backtest_series",
                    file_path=str(series_path),
                    format="json",
                    created_at=start,
                )
            )
        session.commit()
        return task_id
    finally:
        session.close()
        engine.dispose()


def _cli_quality_report(
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
        source="unit-test",
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
