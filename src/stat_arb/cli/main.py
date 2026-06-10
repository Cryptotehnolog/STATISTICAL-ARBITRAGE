"""Command line interface for local statistical-arbitrage workflows."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from stat_arb.agents import (
    CoordinatorTransitionRequest,
    ExperimentFinalDecision,
    ExperimentLifecycleStatus,
    HypothesisGenerationConfig,
    HypothesisUniverseAsset,
    generate_rule_based_hypotheses,
    transition_experiment_lifecycle,
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
