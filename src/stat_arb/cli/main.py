"""Command line interface for local statistical-arbitrage workflows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import click

from stat_arb.data_quality import OHLCVQualityConfig, validate_ohlcv_batch
from stat_arb.domain import AdjustmentMode
from stat_arb.ingestion import (
    CCXTOHLCVSource as _CCXTOHLCVSource,
)
from stat_arb.ingestion import (
    OHLCVQualityError,
    fetch_validate_write_ohlcv,
)
from stat_arb.storage import (
    Base,
    Dataset,
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
