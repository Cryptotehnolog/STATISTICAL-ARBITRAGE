"""Command line interface for local statistical-arbitrage workflows."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID

import click

from stat_arb.agents import (
    AgentAuditJsonlWriter,
    CoordinatorResourcePolicy,
    CoordinatorTaskRequest,
    CoordinatorTransitionRequest,
    ExperimentFinalDecision,
    ExperimentLifecycleStatus,
    HypothesisGenerationConfig,
    HypothesisUniverseAsset,
    claim_coordinator_task_by_id,
    complete_coordinator_task,
    enqueue_coordinator_task,
    fail_coordinator_task,
    generate_rule_based_hypotheses,
    run_backtest_agent_persistence,
    run_critic_agent_persistence,
    run_report_agent,
    run_statistical_testing,
    transition_experiment_lifecycle,
)
from stat_arb.cli.stage_payloads import (
    build_backtest_agent_input,
    build_critic_agent_input,
    build_report_agent_input,
    build_statistical_testing_input,
)
from stat_arb.cli.stage_support import execute_stage_spec, supported_execute_stages
from stat_arb.data_quality import OHLCVQualityConfig, validate_ohlcv_batch
from stat_arb.domain import AdjustmentMode
from stat_arb.ingestion import (
    CCXTOHLCVSource as _CCXTOHLCVSource,
)
from stat_arb.ingestion import (
    OHLCVQualityError,
    fetch_validate_write_ohlcv,
)
from stat_arb.statistical import MultipleTestingMethod
from stat_arb.storage import (
    Base,
    CoordinatorTask,
    Dataset,
    Experiment,
    Hypothesis,
    ReportArtifact,
    create_database_engine,
    create_session_factory,
    persist_ohlcv_ingestion_result,
)

CCXTOHLCVSource = _CCXTOHLCVSource


@click.group()
def main() -> None:
    """Локальные команды Statistical Arbitrage."""


@main.group()
def data() -> None:
    """Команды ingestion и data quality."""


@data.command("list")
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def list_datasets(db_path: Path) -> None:
    """Показать datasets из Structured Registry."""
    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        rows = session.query(Dataset).order_by(Dataset.downloaded_at.desc()).all()
        click.echo(f"Найдено datasets: {len(rows)}")
        for row in rows:
            click.echo(
                " | ".join(
                    (
                        row.dataset_id,
                        row.symbol,
                        row.source,
                        row.timeframe,
                        f"bars={row.bar_count}",
                        f"quality={row.quality_score:.6f}",
                        row.file_path,
                    )
                )
            )
    finally:
        session.close()
        engine.dispose()


@data.command("validate")
@click.option("--exchange", required=True)
@click.option("--symbol", required=True)
@click.option("--timeframe", required=True)
@click.option("--since", callback=lambda _ctx, _param, value: _parse_datetime(value))
@click.option("--limit", type=int)
@click.option("--max-missing-bar-ratio", type=float, required=True)
@click.option("--max-abnormal-volume-ratio", type=float, required=True)
@click.option("--volume-spike-multiplier", type=float, required=True)
def validate_data(
    exchange: str,
    symbol: str,
    timeframe: str,
    since: datetime | None,
    limit: int | None,
    max_missing_bar_ratio: float,
    max_abnormal_volume_ratio: float,
    volume_spike_multiplier: float,
) -> None:
    """Проверить качество OHLCV sample без записи в registry."""
    source = CCXTOHLCVSource(exchange_id=exchange)
    batch = source.fetch_ohlcv_batch(
        symbol=symbol,
        timeframe=timeframe,
        since=since,
        limit=limit,
    )
    report = validate_ohlcv_batch(
        batch,
        config=_quality_config(
            max_missing_bar_ratio=max_missing_bar_ratio,
            max_abnormal_volume_ratio=max_abnormal_volume_ratio,
            volume_spike_multiplier=volume_spike_multiplier,
        ),
    )
    if report.passed:
        click.echo(
            f"Качество данных пройдено: symbol={report.symbol}, "
            f"bars={report.bar_count}, quality={report.quality_score:.6f}"
        )
        return

    issue_codes = ", ".join(issue.code for issue in report.issues)
    raise click.ClickException(
        f"Качество данных не пройдено: symbol={report.symbol}, issues={issue_codes}"
    )


@data.command("download")
@click.option("--exchange", required=True)
@click.option("--symbol", required=True)
@click.option("--timeframe", required=True)
@click.option("--since", callback=lambda _ctx, _param, value: _parse_datetime(value))
@click.option("--limit", type=int)
@click.option("--raw-output-root", type=click.Path(path_type=Path), required=True)
@click.option("--metadata-root", type=click.Path(path_type=Path), required=True)
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
@click.option("--max-missing-bar-ratio", type=float, required=True)
@click.option("--max-abnormal-volume-ratio", type=float, required=True)
@click.option("--volume-spike-multiplier", type=float, required=True)
def download_data(
    exchange: str,
    symbol: str,
    timeframe: str,
    since: datetime | None,
    limit: int | None,
    raw_output_root: Path,
    metadata_root: Path,
    db_path: Path,
    max_missing_bar_ratio: float,
    max_abnormal_volume_ratio: float,
    volume_spike_multiplier: float,
) -> None:
    """Скачать OHLCV, проверить качество и сохранить registry records."""
    source = CCXTOHLCVSource(exchange_id=exchange)
    try:
        result = fetch_validate_write_ohlcv(
            source,
            symbol=symbol,
            timeframe=timeframe,
            output_root=raw_output_root,
            since=since,
            limit=limit,
            quality_config=_quality_config(
                max_missing_bar_ratio=max_missing_bar_ratio,
                max_abnormal_volume_ratio=max_abnormal_volume_ratio,
                volume_spike_multiplier=volume_spike_multiplier,
            ),
        )
    except OHLCVQualityError as exc:
        issue_codes = ", ".join(issue.code for issue in exc.report.issues)
        raise click.ClickException(
            f"Качество данных не пройдено: symbol={symbol}, issues={issue_codes}"
        ) from exc

    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        stored = persist_ohlcv_ingestion_result(
            session,
            result,
            metadata_root,
            adjustment_mode=AdjustmentMode.NONE,
            extra_metadata={
                "cli_command": "data download",
                "exchange": exchange,
                "limit": limit,
                "since": since.isoformat() if since is not None else None,
            },
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    click.echo(f"Dataset сохранен: {stored.dataset.dataset_id}")
    click.echo(f"Quality report сохранен: {stored.quality_report.report_id}")
    click.echo(f"Parquet files: {len(result.parquet_paths)}")


@main.group()
def hypothesis() -> None:
    """Команды управления hypotheses."""


@hypothesis.command("list")
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def list_hypotheses(db_path: Path) -> None:
    """Показать hypotheses из Structured Registry."""
    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        rows = session.query(Hypothesis).order_by(Hypothesis.created_at.desc()).all()
        click.echo(f"Найдено hypotheses: {len(rows)}")
        for row in rows:
            click.echo(
                " | ".join(
                    (
                        row.hypothesis_id,
                        f"{row.asset_a}/{row.asset_b}",
                        row.status,
                        row.source,
                        f"novelty={row.novelty_score:.6f}",
                    )
                )
            )
    finally:
        session.close()
        engine.dispose()


@hypothesis.command("add")
@click.option("--asset-a", required=True)
@click.option("--asset-b", required=True)
@click.option("--rationale", required=True)
@click.option("--source", required=True)
@click.option("--created-by", required=True)
@click.option("--novelty-score", type=float, required=True)
@click.option("--status", required=True)
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def add_hypothesis(
    asset_a: str,
    asset_b: str,
    rationale: str,
    source: str,
    created_by: str,
    novelty_score: float,
    status: str,
    db_path: Path,
) -> None:
    """Добавить manual hypothesis в registry."""
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        hypothesis_row = Hypothesis(
            asset_a=asset_a,
            asset_b=asset_b,
            rationale=rationale,
            source=source,
            created_by=created_by,
            novelty_score=novelty_score,
            status=status,
        )
        session.add(hypothesis_row)
        session.commit()
        click.echo(f"Hypothesis сохранена: {hypothesis_row.hypothesis_id}")
    finally:
        session.close()
        engine.dispose()


@hypothesis.command("generate")
@click.option("--assets-json", type=click.Path(path_type=Path), required=True)
@click.option("--correlations-json", type=click.Path(path_type=Path), required=True)
@click.option("--p-values-json", type=click.Path(path_type=Path), required=True)
@click.option("--require-same-sector/--allow-cross-sector", default=False)
@click.option("--min-abs-correlation", type=float, required=True)
@click.option("--min-market-cap", type=int, required=True)
@click.option("--max-market-cap", type=int)
@click.option("--max-pairs", type=int, required=True)
@click.option("--multiple-testing-method", required=True)
@click.option("--candidate-alpha", type=float, required=True)
@click.option("--initial-novelty-score", type=float, required=True)
@click.option("--initial-status", required=True)
@click.option("--source", required=True)
@click.option("--created-by", required=True)
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def generate_hypotheses(
    assets_json: Path,
    correlations_json: Path,
    p_values_json: Path,
    require_same_sector: bool,
    min_abs_correlation: float,
    min_market_cap: int,
    max_market_cap: int | None,
    max_pairs: int,
    multiple_testing_method: str,
    candidate_alpha: float,
    initial_novelty_score: float,
    initial_status: str,
    source: str,
    created_by: str,
    db_path: Path,
) -> None:
    """Сгенерировать rule-based hypotheses из JSON universe/contracts."""
    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        result = generate_rule_based_hypotheses(
            assets=_load_assets(assets_json),
            correlations=_load_pair_metric(correlations_json, value_key="correlation"),
            candidate_p_values=_load_pair_metric(p_values_json, value_key="p_value"),
            config=HypothesisGenerationConfig(
                require_same_sector=require_same_sector,
                min_abs_correlation=min_abs_correlation,
                min_market_cap=min_market_cap,
                max_market_cap=max_market_cap,
                max_pairs=max_pairs,
                multiple_testing_method=MultipleTestingMethod(multiple_testing_method),
                candidate_alpha=candidate_alpha,
                initial_novelty_score=initial_novelty_score,
                initial_status=initial_status,
                source=source,
                created_by=created_by,
            ),
            session=session,
        )
        session.commit()
        click.echo(f"Hypotheses generated: {result.generated_count}")
        click.echo(f"Hypotheses skipped: {result.skipped_count}")
    finally:
        session.close()
        engine.dispose()


@main.group()
def experiment() -> None:
    """Команды управления experiments."""


@experiment.command("list")
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def list_experiments(db_path: Path) -> None:
    """Показать experiments из Structured Registry."""
    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        rows = session.query(Experiment).order_by(Experiment.created_at.desc()).all()
        click.echo(f"Найдено experiments: {len(rows)}")
        for row in rows:
            click.echo(
                " | ".join(
                    (
                        row.experiment_id,
                        f"hypothesis={row.hypothesis_id}",
                        f"status={row.status}",
                        f"agent={row.current_agent or '-'}",
                        f"decision={row.final_decision or '-'}",
                    )
                )
            )
    finally:
        session.close()
        engine.dispose()


@experiment.command("status")
@click.option("--experiment-id", required=True)
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def experiment_status(experiment_id: str, db_path: Path) -> None:
    """Показать статус одного experiment из registry."""
    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        row = session.get(Experiment, experiment_id)
        if row is None:
            raise click.ClickException(f"Experiment не найден: {experiment_id}")
        hypothesis_row = session.get(Hypothesis, row.hypothesis_id)
        pair = (
            f"{hypothesis_row.asset_a}/{hypothesis_row.asset_b}"
            if hypothesis_row is not None
            else "-"
        )
        click.echo(f"Experiment: {row.experiment_id}")
        click.echo(f"Hypothesis: {row.hypothesis_id}")
        click.echo(f"Pair: {pair}")
        click.echo(f"Status: {row.status}")
        click.echo(f"Current agent: {row.current_agent or '-'}")
        click.echo(f"Final decision: {row.final_decision or '-'}")
        click.echo(f"Completed at: {row.completed_at.isoformat() if row.completed_at else '-'}")
    finally:
        session.close()
        engine.dispose()


@experiment.command("advance")
@click.option("--experiment-id", required=True)
@click.option("--target-status", required=True)
@click.option("--reason", required=True)
@click.option("--actor", required=True)
@click.option("--final-decision")
@click.option("--audit-log-path", type=click.Path(path_type=Path))
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def advance_experiment(
    experiment_id: str,
    target_status: str,
    reason: str,
    actor: str,
    final_decision: str | None,
    audit_log_path: Path | None,
    db_path: Path,
) -> None:
    """Перевести experiment в следующий lifecycle status через Coordinator."""
    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        try:
            result = transition_experiment_lifecycle(
                CoordinatorTransitionRequest(
                    experiment_id=experiment_id,
                    target_status=ExperimentLifecycleStatus(target_status),
                    reason=reason,
                    actor=actor,
                    final_decision=(
                        ExperimentFinalDecision(final_decision)
                        if final_decision is not None
                        else None
                    ),
                ),
                session=session,
                audit_writer=(
                    AgentAuditJsonlWriter(audit_log_path)
                    if audit_log_path is not None
                    else None
                ),
            )
        except ValueError as exc:
            session.rollback()
            raise click.ClickException(str(exc)) from exc
        session.commit()
    finally:
        session.close()
        engine.dispose()

    click.echo(
        "Experiment обновлен: "
        f"{result.experiment.experiment_id} "
        f"{result.previous_status.value} -> {result.current_status.value}"
    )
    if audit_log_path is not None and result.audit_written:
        click.echo(f"Audit записан: {audit_log_path}")


@experiment.command("run-stage")
@click.option("--experiment-id", required=True)
@click.option("--stage", required=True)
@click.option("--task-type", required=True)
@click.option("--agent-name", required=True)
@click.option("--priority", type=int, required=True)
@click.option("--max-attempts", type=int, required=True)
@click.option("--payload-json", type=click.Path(path_type=Path), required=True)
@click.option("--advance-lifecycle", is_flag=True)
@click.option("--reason")
@click.option("--actor")
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def run_experiment_stage(
    experiment_id: str,
    stage: str,
    task_type: str,
    agent_name: str,
    priority: int,
    max_attempts: int,
    payload_json: Path,
    advance_lifecycle: bool,
    reason: str | None,
    actor: str | None,
    db_path: Path,
) -> None:
    """Поставить stage task в Coordinator queue без прямого запуска агента."""
    try:
        target_status = ExperimentLifecycleStatus(stage)
        _validate_stage_agent(target_status=target_status, agent_name=agent_name)
        payload = _read_json_object(payload_json)
        if advance_lifecycle and (not reason or not actor):
            raise click.ClickException(
                "--reason и --actor обязательны вместе с --advance-lifecycle"
            )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    engine = create_database_engine(db_path)
    Base.metadata.create_all(engine)
    session_factory = create_session_factory(engine)
    session = session_factory()
    transition_text = "Lifecycle не изменен"
    try:
        try:
            task = enqueue_coordinator_task(
                CoordinatorTaskRequest(
                    experiment_id=experiment_id,
                    task_type=task_type,
                    agent_name=agent_name,
                    priority=priority,
                    max_attempts=max_attempts,
                    payload=payload,
                ),
                session=session,
            )
            if advance_lifecycle:
                transition_result = transition_experiment_lifecycle(
                    CoordinatorTransitionRequest(
                        experiment_id=experiment_id,
                        target_status=target_status,
                        reason=reason or "",
                        actor=actor or "",
                    ),
                    session=session,
                )
                transition_text = (
                    f"{transition_result.previous_status.value} -> "
                    f"{transition_result.current_status.value}"
                )
        except ValueError as exc:
            session.rollback()
            raise click.ClickException(str(exc)) from exc
        session.commit()
    finally:
        session.close()
        engine.dispose()

    click.echo(f"Stage task поставлен в очередь: {task.task_id}")
    click.echo(f"Experiment: {task.experiment_id}")
    click.echo(f"Stage: {target_status.value}")
    click.echo(f"Task type: {task.task_type}")
    click.echo(f"Agent: {task.agent_name}")
    click.echo(transition_text)


@experiment.command("execute-stage")
@click.option("--task-id", required=True)
@click.option("--stage", required=True)
@click.option("--max-running-tasks", type=int, required=True)
@click.option("--max-running-tasks-per-agent", type=int, required=True)
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def execute_experiment_stage(
    task_id: str,
    stage: str,
    max_running_tasks: int,
    max_running_tasks_per_agent: int,
    db_path: Path,
) -> None:
    """Выполнить один queued stage через поддерживаемый agent service."""
    try:
        target_status = ExperimentLifecycleStatus(stage)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    try:
        execute_stage_spec(target_status)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        _claim_execute_and_complete_stage(
            session=session,
            task_id=task_id,
            target_status=target_status,
            max_running_tasks=max_running_tasks,
            max_running_tasks_per_agent=max_running_tasks_per_agent,
        )
        session.commit()
    finally:
        session.close()
        engine.dispose()

    click.echo(f"Stage выполнен: {target_status.value}")
    click.echo(f"Task completed: {task_id}")


@experiment.command("run-pipeline")
@click.option("--experiment-id", required=True)
@click.option("--stages", required=True)
@click.option("--report-output-dir", type=click.Path(path_type=Path), required=True)
@click.option("--max-running-tasks", type=int, required=True)
@click.option("--max-running-tasks-per-agent", type=int, required=True)
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def run_experiment_pipeline(
    experiment_id: str,
    stages: str,
    report_output_dir: Path,
    max_running_tasks: int,
    max_running_tasks_per_agent: int,
    db_path: Path,
) -> None:
    """Выполнить маленький guarded pipeline из mature queued stages."""
    target_stages = _parse_pipeline_stages(stages)
    if target_stages != (
        ExperimentLifecycleStatus.BACKTESTING,
        ExperimentLifecycleStatus.REPORTING,
    ):
        raise click.ClickException(
            "run-pipeline сейчас поддерживает только stages=backtesting,reporting"
        )

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    completed: list[str] = []
    try:
        backtesting_task = _pending_task_for_stage(
            session,
            experiment_id=experiment_id,
            stage=ExperimentLifecycleStatus.BACKTESTING,
        )
        _claim_execute_and_complete_stage(
            session,
            task_id=backtesting_task.task_id,
            target_status=ExperimentLifecycleStatus.BACKTESTING,
            max_running_tasks=max_running_tasks,
            max_running_tasks_per_agent=max_running_tasks_per_agent,
        )
        session.commit()
        completed.append(ExperimentLifecycleStatus.BACKTESTING.value)

        backtest_id = _latest_backtest_id_from_series_sidecar(
            session,
            experiment_id=UUID(experiment_id),
        )
        reporting_task = enqueue_coordinator_task(
            CoordinatorTaskRequest(
                experiment_id=experiment_id,
                task_type=execute_stage_spec(ExperimentLifecycleStatus.REPORTING).task_type,
                agent_name=execute_stage_spec(ExperimentLifecycleStatus.REPORTING).agent_name,
                priority=backtesting_task.priority + 1,
                max_attempts=backtesting_task.max_attempts,
                payload={
                    "backtest_id": backtest_id,
                    "output_dir": str(report_output_dir),
                },
            ),
            session=session,
        )
        session.commit()

        _claim_execute_and_complete_stage(
            session,
            task_id=reporting_task.task_id,
            target_status=ExperimentLifecycleStatus.REPORTING,
            max_running_tasks=max_running_tasks,
            max_running_tasks_per_agent=max_running_tasks_per_agent,
        )
        session.commit()
        completed.append(ExperimentLifecycleStatus.REPORTING.value)
    except Exception as exc:
        session.rollback()
        raise click.ClickException(str(exc)) from exc
    finally:
        session.close()
        engine.dispose()

    for stage_name in completed:
        click.echo(f"Pipeline stage выполнен: {stage_name}")


def _quality_config(
    *,
    max_missing_bar_ratio: float,
    max_abnormal_volume_ratio: float,
    volume_spike_multiplier: float,
) -> OHLCVQualityConfig:
    return OHLCVQualityConfig(
        max_missing_bar_ratio=max_missing_bar_ratio,
        max_abnormal_volume_ratio=max_abnormal_volume_ratio,
        volume_spike_multiplier=volume_spike_multiplier,
    )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise click.BadParameter("ожидается ISO datetime, например 2024-01-01T00:00:00+00:00") from exc


def _load_assets(path: Path) -> tuple[HypothesisUniverseAsset, ...]:
    rows = _read_json_list(path)
    return tuple(
        HypothesisUniverseAsset(
            symbol=str(row["symbol"]),
            sector=str(row["sector"]),
            market_cap=int(row["market_cap"]),
        )
        for row in rows
    )


def _load_pair_metric(path: Path, *, value_key: str) -> dict[tuple[str, str], float]:
    rows = _read_json_list(path)
    return {
        (str(row["asset_a"]), str(row["asset_b"])): float(row[value_key])
        for row in rows
    }


def _read_json_list(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise click.BadParameter(f"{path} должен содержать JSON array")
    if not all(isinstance(row, dict) for row in payload):
        raise click.BadParameter(f"{path} должен содержать JSON objects")
    return payload


def _read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise click.BadParameter(f"{path} должен содержать JSON object")
    return payload


def _execute_statistical_testing_task(payload: dict[str, object], *, session: Any) -> None:
    run_statistical_testing(
        build_statistical_testing_input(payload),
        session=session,
        memory_service=None,
    )


def _parse_pipeline_stages(stages: str) -> tuple[ExperimentLifecycleStatus, ...]:
    try:
        return tuple(
            ExperimentLifecycleStatus(stage.strip())
            for stage in stages.split(",")
            if stage.strip()
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _pending_task_for_stage(
    session: Any,
    *,
    experiment_id: str,
    stage: ExperimentLifecycleStatus,
) -> CoordinatorTask:
    spec = execute_stage_spec(stage)
    task = (
        session.query(CoordinatorTask)
        .filter(
            CoordinatorTask.experiment_id == str(experiment_id),
            CoordinatorTask.task_type == spec.task_type,
            CoordinatorTask.agent_name == spec.agent_name,
            CoordinatorTask.status == "pending",
        )
        .order_by(CoordinatorTask.priority.asc(), CoordinatorTask.created_at.asc())
        .first()
    )
    if task is None:
        raise ValueError(f"pending task is required for pipeline stage {stage.value}")
    return cast(CoordinatorTask, task)


def _claim_execute_and_complete_stage(
    session: Any,
    *,
    task_id: str,
    target_status: ExperimentLifecycleStatus,
    max_running_tasks: int,
    max_running_tasks_per_agent: int,
) -> None:
    stage_spec = execute_stage_spec(target_status)
    task = claim_coordinator_task_by_id(
        task_id=task_id,
        policy=_coordinator_resource_policy(
            max_running_tasks=max_running_tasks,
            max_running_tasks_per_agent=max_running_tasks_per_agent,
        ),
        session=session,
    )
    if task is None:
        raise click.ClickException("Coordinator resource policy blocked task claim")
    try:
        if task.task_type != stage_spec.task_type:
            raise ValueError(f"task_type must be {stage_spec.task_type}")
        if task.agent_name != stage_spec.agent_name:
            raise ValueError(f"agent_name must be {stage_spec.agent_name}")
        _execute_claimed_stage(
            target_status,
            task.payload,
            experiment_id=UUID(task.experiment_id),
            session=session,
        )
        complete_coordinator_task(task_id=task.task_id, session=session)
    except Exception as exc:
        fail_coordinator_task(
            task_id=task.task_id,
            error_summary=str(exc),
            session=session,
        )
        session.commit()
        raise click.ClickException(str(exc)) from exc


def _coordinator_resource_policy(
    *,
    max_running_tasks: int,
    max_running_tasks_per_agent: int,
) -> CoordinatorResourcePolicy:
    return CoordinatorResourcePolicy(
        max_running_tasks=max_running_tasks,
        max_running_tasks_per_agent={
            spec.agent_name: max_running_tasks_per_agent
            for spec in (execute_stage_spec(stage) for stage in supported_execute_stages())
        },
    )


def _execute_claimed_stage(
    target_status: ExperimentLifecycleStatus,
    payload: dict[str, object],
    *,
    experiment_id: UUID,
    session: Any,
) -> None:
    if target_status == ExperimentLifecycleStatus.STATISTICAL_TESTING:
        _execute_statistical_testing_task(payload, session=session)
    elif target_status == ExperimentLifecycleStatus.BACKTESTING:
        _execute_backtesting_task(payload, experiment_id=experiment_id, session=session)
    elif target_status == ExperimentLifecycleStatus.CRITIC_REVIEW:
        _execute_critic_review_task(payload, session=session)
    elif target_status == ExperimentLifecycleStatus.REPORTING:
        _execute_reporting_task(payload, experiment_id=experiment_id, session=session)
    else:
        raise ValueError(f"stage не поддерживает queued execution: {target_status.value}")


def _latest_backtest_id_from_series_sidecar(session: Any, *, experiment_id: UUID) -> str:
    artifact = (
        session.query(ReportArtifact)
        .filter(
            ReportArtifact.experiment_id == str(experiment_id),
            ReportArtifact.artifact_type == "backtest_series",
            ReportArtifact.format == "json",
        )
        .order_by(ReportArtifact.created_at.desc())
        .first()
    )
    if artifact is None:
        raise ValueError("backtest_series sidecar is required before reporting pipeline stage")
    payload = json.loads(Path(artifact.file_path).read_text(encoding="utf-8"))
    backtest_id = payload.get("backtest_id")
    if not isinstance(backtest_id, str) or not backtest_id.strip():
        raise ValueError("backtest_series sidecar must contain backtest_id")
    return backtest_id


def _execute_backtesting_task(
    payload: dict[str, object],
    *,
    experiment_id: UUID,
    session: Any,
) -> None:
    run_backtest_agent_persistence(
        build_backtest_agent_input(payload, experiment_id=experiment_id),
        session=session,
        memory_service=None,
    )


def _execute_critic_review_task(payload: dict[str, object], *, session: Any) -> None:
    run_critic_agent_persistence(
        build_critic_agent_input(payload),
        session=session,
        memory_service=None,
    )


def _execute_reporting_task(
    payload: dict[str, object],
    *,
    experiment_id: UUID,
    session: Any,
) -> None:
    request = build_report_agent_input(payload, experiment_id=experiment_id)
    _require_matching_backtest_series_sidecar(
        session,
        experiment_id=request.experiment_id,
        backtest_id=request.backtest_id,
    )
    run_report_agent(request, session=session, memory_service=None)


def _require_matching_backtest_series_sidecar(
    session: Any,
    *,
    experiment_id: UUID,
    backtest_id: UUID,
) -> None:
    artifacts = (
        session.query(ReportArtifact)
        .filter(
            ReportArtifact.experiment_id == str(experiment_id),
            ReportArtifact.artifact_type == "backtest_series",
            ReportArtifact.format == "json",
        )
        .all()
    )
    for artifact in artifacts:
        payload = json.loads(Path(artifact.file_path).read_text(encoding="utf-8"))
        if payload.get("backtest_id") == str(backtest_id):
            return
    raise ValueError(
        "matching backtest_series sidecar is required before reporting stage execution"
    )


def _validate_stage_agent(
    *,
    target_status: ExperimentLifecycleStatus,
    agent_name: str,
) -> None:
    expected_agents = {
        ExperimentLifecycleStatus.DATA_VALIDATION: "data_agent",
        ExperimentLifecycleStatus.STATISTICAL_TESTING: "statistical_testing_agent",
        ExperimentLifecycleStatus.BACKTESTING: "backtest_agent",
        ExperimentLifecycleStatus.CRITIC_REVIEW: "critic_agent",
        ExperimentLifecycleStatus.REPORTING: "report_agent",
    }
    expected_agent = expected_agents.get(target_status)
    if expected_agent is None:
        raise ValueError(f"stage не поддерживает queued execution: {target_status.value}")
    if agent_name != expected_agent:
        raise ValueError(
            f"agent-name не соответствует stage: expected {expected_agent}, got {agent_name}"
        )
