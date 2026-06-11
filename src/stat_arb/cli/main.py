"""Command line interface for local statistical-arbitrage workflows."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from stat_arb.agents import (
    BacktestAgentInput,
    CoordinatorResourcePolicy,
    CoordinatorTaskRequest,
    CoordinatorTransitionRequest,
    ExperimentFinalDecision,
    ExperimentLifecycleStatus,
    HypothesisGenerationConfig,
    HypothesisUniverseAsset,
    StatisticalTestingInput,
    claim_coordinator_task_by_id,
    complete_coordinator_task,
    enqueue_coordinator_task,
    fail_coordinator_task,
    generate_rule_based_hypotheses,
    run_backtest_agent_persistence,
    run_statistical_testing,
    transition_experiment_lifecycle,
)
from stat_arb.backtest import (
    BacktestCostConfig,
    BacktestExitPolicyConfig,
    BaselineAsset,
    BaselineSide,
    BuyAndHoldBaselineConfig,
    CostAssumptionStatus,
    CostSensitivityScenario,
    PerformanceMetricConfig,
    calculate_performance_metrics,
    compare_to_buy_and_hold_baseline,
    create_reproducibility_manifest,
    run_cost_sensitivity_analysis,
    run_pair_backtest_core,
)
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
    Dataset,
    Experiment,
    Hypothesis,
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
@click.option("--db-path", type=click.Path(path_type=Path), required=True)
def advance_experiment(
    experiment_id: str,
    target_status: str,
    reason: str,
    actor: str,
    final_decision: str | None,
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
    supported_stages = {
        ExperimentLifecycleStatus.STATISTICAL_TESTING,
        ExperimentLifecycleStatus.BACKTESTING,
    }
    if target_status not in supported_stages:
        raise click.ClickException(
            "stage executor пока поддерживает только statistical_testing и backtesting"
        )

    engine = create_database_engine(db_path)
    session_factory = create_session_factory(engine)
    session = session_factory()
    try:
        task = claim_coordinator_task_by_id(
            task_id=task_id,
            policy=CoordinatorResourcePolicy(
                max_running_tasks=max_running_tasks,
                max_running_tasks_per_agent={
                    "statistical_testing_agent": max_running_tasks_per_agent,
                    "backtest_agent": max_running_tasks_per_agent,
                },
            ),
            session=session,
        )
        if task is None:
            raise click.ClickException("Coordinator resource policy blocked task claim")
        try:
            if target_status == ExperimentLifecycleStatus.STATISTICAL_TESTING:
                if task.task_type != "run_statistical_tests":
                    raise ValueError("task_type must be run_statistical_tests")
                if task.agent_name != "statistical_testing_agent":
                    raise ValueError("agent_name must be statistical_testing_agent")
                _execute_statistical_testing_task(task.payload, session=session)
            elif target_status == ExperimentLifecycleStatus.BACKTESTING:
                if task.task_type != "run_backtest":
                    raise ValueError("task_type must be run_backtest")
                if task.agent_name != "backtest_agent":
                    raise ValueError("agent_name must be backtest_agent")
                _execute_backtesting_task(task.payload, session=session)
            complete_coordinator_task(task_id=task.task_id, session=session)
        except Exception as exc:
            fail_coordinator_task(
                task_id=task.task_id,
                error_summary=str(exc),
                session=session,
            )
            session.commit()
            raise click.ClickException(str(exc)) from exc
        session.commit()
    finally:
        session.close()
        engine.dispose()

    click.echo(f"Stage выполнен: {target_status.value}")
    click.echo(f"Task completed: {task_id}")


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
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise click.BadParameter(f"{path} должен содержать JSON array")
    if not all(isinstance(row, dict) for row in payload):
        raise click.BadParameter(f"{path} должен содержать JSON objects")
    return payload


def _read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise click.BadParameter(f"{path} должен содержать JSON object")
    return payload


def _execute_statistical_testing_task(payload: dict[str, object], *, session: Any) -> None:
    run_statistical_testing(
        StatisticalTestingInput(
            hypothesis_id=_payload_uuid(payload, "hypothesis_id"),
            dataset_a_id=_payload_uuid(payload, "dataset_a_id"),
            dataset_b_id=_payload_uuid(payload, "dataset_b_id"),
            prices_a=_payload_float_list(payload, "prices_a"),
            prices_b=_payload_float_list(payload, "prices_b"),
            aligned_timestamps=_payload_datetimes(payload, "aligned_timestamps"),
            train_fraction=_payload_float(payload, "train_fraction"),
            alpha=_payload_float(payload, "alpha"),
            adf_regression=_payload_string(payload, "adf_regression"),
            adf_autolag=_payload_optional_string(payload, "adf_autolag"),
            periods_per_day=_payload_float(payload, "periods_per_day"),
            residual_diagnostics_lags=_payload_int(payload, "residual_diagnostics_lags"),
            regime_window=_payload_int(payload, "regime_window"),
            regime_mean_shift_threshold=_payload_float(
                payload,
                "regime_mean_shift_threshold",
            ),
            regime_volatility_ratio_threshold=_payload_float(
                payload,
                "regime_volatility_ratio_threshold",
            ),
        ),
        session=session,
        memory_service=None,
    )


def _execute_backtesting_task(payload: dict[str, object], *, session: Any) -> None:
    prices_a = _payload_float_list(payload, "prices_a")
    prices_b = _payload_float_list(payload, "prices_b")
    aligned_timestamps = _payload_datetimes(payload, "aligned_timestamps")
    z_scores = _payload_float_list(payload, "z_scores")
    core = run_pair_backtest_core(
        prices_a=prices_a,
        prices_b=prices_b,
        z_scores=z_scores,
        aligned_timestamps=aligned_timestamps,
        hedge_ratio=_payload_float(payload, "hedge_ratio"),
        entry_threshold=_payload_float(payload, "entry_threshold"),
        exit_threshold=_payload_float(payload, "exit_threshold"),
        exit_policy=_payload_exit_policy(payload),
        risk_exit_policy_disabled_reason=_payload_optional_string(
            payload,
            "risk_exit_policy_disabled_reason",
        ),
    )
    cost_config = _payload_cost_config(_payload_object(payload, "cost_config"))
    periods_per_day = _payload_float(payload, "periods_per_day")
    average_portfolio_value = _payload_optional_float(payload, "average_portfolio_value")
    sensitivity_scenarios = tuple(
        CostSensitivityScenario(
            name=_object_string(item, "name", context="payload.sensitivity_scenarios[]"),
            cost_multiplier=_object_float(
                item,
                "cost_multiplier",
                context="payload.sensitivity_scenarios[]",
            ),
        )
        for item in _payload_object_list(payload, "sensitivity_scenarios")
    )
    sensitivity = run_cost_sensitivity_analysis(
        core,
        base_cost_config=cost_config,
        periods_per_day=periods_per_day,
        average_portfolio_value=average_portfolio_value,
        scenarios=sensitivity_scenarios,
    )
    metric_config = _payload_metric_config(_payload_object(payload, "metric_config"))
    metrics = calculate_performance_metrics(
        equity_curve=_payload_float_list(payload, "equity_curve"),
        period_returns=_payload_float_list(payload, "period_returns"),
        trade_pnls=_payload_float_list(payload, "trade_pnls"),
        core_result=core,
        config=metric_config,
    )
    baseline = compare_to_buy_and_hold_baseline(
        strategy_period_returns=_payload_float_list(payload, "period_returns"),
        prices_a=prices_a,
        prices_b=prices_b,
        aligned_timestamps=aligned_timestamps,
        baseline_config=_payload_buy_and_hold_baseline_config(
            _payload_object(payload, "baseline_config")
        ),
        metric_config=metric_config,
    )
    reproducibility_payload = _payload_object(payload, "reproducibility")
    reproducibility = create_reproducibility_manifest(
        git_commit_hash=_object_string(
            reproducibility_payload,
            "git_commit_hash",
            context="payload.reproducibility",
        ),
        config_components={
            "core": {
                "hedge_ratio": core.hedge_ratio,
                "entry_threshold": core.entry_threshold,
                "exit_threshold": core.exit_threshold,
                "exit_policy": core.exit_policy,
                "risk_exit_policy_disabled_reason": core.risk_exit_policy_disabled_reason,
            },
            "cost_config": cost_config,
            "metric_config": metric_config,
            "baseline_config": _payload_buy_and_hold_baseline_config(
                _payload_object(payload, "baseline_config")
            ),
            "sensitivity_scenarios": sensitivity_scenarios,
        },
        dataset_ids=_object_string_list(
            reproducibility_payload,
            "dataset_ids",
            context="payload.reproducibility",
        ),
        random_seed=_object_optional_int(
            reproducibility_payload,
            "random_seed",
            context="payload.reproducibility",
        ),
        execution_command=_object_string_list(
            reproducibility_payload,
            "execution_command",
            context="payload.reproducibility",
        ),
        run_timestamp=_object_datetime(
            reproducibility_payload,
            "run_timestamp",
            context="payload.reproducibility",
        ),
        lock_file_path=_object_string(
            reproducibility_payload,
            "lock_file_path",
            context="payload.reproducibility",
        ),
    )
    run_backtest_agent_persistence(
        BacktestAgentInput(
            hypothesis_id=_payload_uuid(payload, "hypothesis_id"),
            test_id=_payload_uuid(payload, "test_id"),
            dataset_a_id=_payload_uuid(payload, "dataset_a_id"),
            dataset_b_id=_payload_uuid(payload, "dataset_b_id"),
            core_result=core,
            pnl=sensitivity.base,
            metrics=metrics,
            baseline=baseline,
            sensitivity=sensitivity,
            reproducibility=reproducibility,
            train_window_days=_payload_int(payload, "train_window_days"),
            test_window_days=_payload_int(payload, "test_window_days"),
            num_windows=_payload_int(payload, "num_windows"),
        ),
        session=session,
        memory_service=None,
    )


def _payload_uuid(payload: dict[str, object], key: str) -> Any:
    from uuid import UUID

    return UUID(_payload_string(payload, key))


def _payload_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"payload.{key} must be a non-empty string")
    return value


def _payload_optional_string(payload: dict[str, object], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"payload.{key} must be a string or null")
    return value


def _payload_float(payload: dict[str, object], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"payload.{key} must be a number")
    return float(value)


def _payload_optional_float(payload: dict[str, object], key: str) -> float | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"payload.{key} must be a number or null")
    return float(value)


def _payload_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"payload.{key} must be an integer")
    return value


def _payload_object(payload: dict[str, object], key: str) -> dict[str, object]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"payload.{key} must be an object")
    return value


def _payload_object_list(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    value = payload.get(key)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"payload.{key} must be a list of objects")
    return value


def _payload_float_list(payload: dict[str, object], key: str) -> list[float]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"payload.{key} must be a list")
    result: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int | float):
            raise ValueError(f"payload.{key} must contain only numbers")
        result.append(float(item))
    return result


def _payload_exit_policy(payload: dict[str, object]) -> BacktestExitPolicyConfig | None:
    value = payload.get("exit_policy")
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("payload.exit_policy must be an object or null")
    return BacktestExitPolicyConfig(
        max_holding_bars=_object_optional_int(
            value,
            "max_holding_bars",
            context="payload.exit_policy",
        ),
        emergency_z_score=_object_optional_float(
            value,
            "emergency_z_score",
            context="payload.exit_policy",
        ),
    )


def _payload_cost_config(value: dict[str, object]) -> BacktestCostConfig:
    return BacktestCostConfig(
        commission_rate=_object_float(value, "commission_rate", context="payload.cost_config"),
        spread_cost_rate=_object_float(value, "spread_cost_rate", context="payload.cost_config"),
        slippage_rate=_object_float(value, "slippage_rate", context="payload.cost_config"),
        funding_rate_daily=_object_float(
            value,
            "funding_rate_daily",
            context="payload.cost_config",
        ),
        borrow_rate_annual=_object_float(
            value,
            "borrow_rate_annual",
            context="payload.cost_config",
        ),
        status=CostAssumptionStatus(
            _object_string(value, "status", context="payload.cost_config")
        ),
        source=_object_string(value, "source", context="payload.cost_config"),
        verified_at=_object_datetime(value, "verified_at", context="payload.cost_config"),
        venue=_object_string(value, "venue", context="payload.cost_config"),
        market_type=_object_string(value, "market_type", context="payload.cost_config"),
        notes=_object_optional_string(value, "notes", context="payload.cost_config") or "",
    )


def _payload_metric_config(value: dict[str, object]) -> PerformanceMetricConfig:
    return PerformanceMetricConfig(
        periods_per_year=_object_int(value, "periods_per_year", context="payload.metric_config"),
        risk_free_rate_per_period=_object_float(
            value,
            "risk_free_rate_per_period",
            context="payload.metric_config",
        ),
        var_confidence=_object_float(value, "var_confidence", context="payload.metric_config"),
        cvar_confidence=_object_float(value, "cvar_confidence", context="payload.metric_config"),
    )


def _payload_buy_and_hold_baseline_config(
    value: dict[str, object],
) -> BuyAndHoldBaselineConfig:
    kind = _object_string(value, "kind", context="payload.baseline_config")
    if kind != "buy_and_hold":
        raise ValueError("payload.baseline_config.kind must be buy_and_hold")
    return BuyAndHoldBaselineConfig(
        name=_object_string(value, "name", context="payload.baseline_config"),
        asset=BaselineAsset(_object_string(value, "asset", context="payload.baseline_config")),
        side=BaselineSide(_object_string(value, "side", context="payload.baseline_config")),
        units=_object_float(value, "units", context="payload.baseline_config"),
        initial_capital=_object_float(
            value,
            "initial_capital",
            context="payload.baseline_config",
        ),
    )


def _object_string(value: dict[str, object], key: str, *, context: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{context}.{key} must be a non-empty string")
    return item


def _object_optional_string(
    value: dict[str, object],
    key: str,
    *,
    context: str,
) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str):
        raise ValueError(f"{context}.{key} must be a string or null")
    return item


def _object_float(value: dict[str, object], key: str, *, context: str) -> float:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, int | float):
        raise ValueError(f"{context}.{key} must be a number")
    return float(item)


def _object_optional_float(
    value: dict[str, object],
    key: str,
    *,
    context: str,
) -> float | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, int | float):
        raise ValueError(f"{context}.{key} must be a number or null")
    return float(item)


def _object_int(value: dict[str, object], key: str, *, context: str) -> int:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError(f"{context}.{key} must be an integer")
    return item


def _object_optional_int(
    value: dict[str, object],
    key: str,
    *,
    context: str,
) -> int | None:
    item = value.get(key)
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, int):
        raise ValueError(f"{context}.{key} must be an integer or null")
    return item


def _object_string_list(
    value: dict[str, object],
    key: str,
    *,
    context: str,
) -> list[str]:
    item = value.get(key)
    if not isinstance(item, list) or not all(isinstance(entry, str) for entry in item):
        raise ValueError(f"{context}.{key} must be a list of strings")
    return item


def _object_datetime(value: dict[str, object], key: str, *, context: str) -> datetime:
    item = value.get(key)
    if not isinstance(item, str):
        raise ValueError(f"{context}.{key} must be an ISO datetime string")
    parsed = _parse_datetime(item)
    if parsed is None:
        raise ValueError(f"{context}.{key} must not be empty")
    return parsed


def _payload_datetimes(payload: dict[str, object], key: str) -> list[datetime]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"payload.{key} must be a list")
    result: list[datetime] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"payload.{key} must contain ISO datetime strings")
        parsed = _parse_datetime(item)
        if parsed is None:
            raise ValueError(f"payload.{key} contains an empty datetime")
        result.append(parsed)
    return result


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
