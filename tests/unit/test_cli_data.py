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
    Base,
    Dataset,
    Hypothesis,
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
