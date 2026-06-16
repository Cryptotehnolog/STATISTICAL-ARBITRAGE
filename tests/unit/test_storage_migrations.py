"""Tests for Structured Registry Alembic migration configuration."""

from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from alembic import command
from stat_arb.storage.migrations import get_alembic_config


def test_default_alembic_configuration_is_available() -> None:
    """Migration helpers should load the committed Alembic baseline."""
    config = get_alembic_config()

    assert Path("alembic/alembic.ini").exists()
    assert Path("alembic/env.py").exists()
    assert Path("alembic/script.py.mako").exists()
    assert Path("alembic/versions").exists()
    assert config.get_main_option("script_location") == "alembic"
    assert config.get_main_option("sqlalchemy.url") == "sqlite:///data/registry.db"


def test_backtest_reproducibility_manifest_migration_is_committed() -> None:
    """Schema migrations should track the full backtest reproducibility manifest."""
    migration = Path("alembic/versions/0001_backtest_reproducibility_manifest.py")

    assert migration.exists()
    text = migration.read_text(encoding="utf-8")
    assert "dataset_ids" in text
    assert "random_seed" in text
    assert "execution_command" in text
    assert "run_timestamp" in text
    assert "lock_file_hash" in text
    assert "execution_time_seconds" in text


def test_alembic_database_url_can_be_overridden() -> None:
    """Tests and deployment scripts should be able to target an explicit DB URL."""
    config = get_alembic_config(db_url="sqlite:///custom.db")

    assert config.get_main_option("sqlalchemy.url") == "sqlite:///custom.db"


def test_provenance_migration_round_trips_on_legacy_schema(tmp_path: Path) -> None:
    """New provenance columns should be applied and reverted on an existing registry."""
    db_path = tmp_path / "registry.db"
    db_url = f"sqlite:///{db_path.as_posix()}"
    engine = create_engine(db_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE statistical_test_results (
                    test_id VARCHAR(36) PRIMARY KEY,
                    half_life_days FLOAT NOT NULL
                )
                """
            )
        )
        connection.execute(
            text(
                """
                CREATE TABLE backtest_results (
                    backtest_id VARCHAR(36) PRIMARY KEY,
                    exit_threshold FLOAT NOT NULL
                )
                """
            )
        )
    engine.dispose()

    config = get_alembic_config(db_url=db_url)
    command.stamp(config, "0001_backtest_reproducibility_manifest")
    command.upgrade(config, "head")

    upgraded_engine = create_engine(db_url)
    inspector = inspect(upgraded_engine)
    statistical_columns = {column["name"] for column in inspector.get_columns("statistical_test_results")}
    backtest_columns = {column["name"] for column in inspector.get_columns("backtest_results")}
    assert "residual_ljung_box_p_value" in statistical_columns
    assert "residual_jarque_bera_p_value" in statistical_columns
    assert "residual_excess_kurtosis" in statistical_columns
    assert "residual_diagnostics_lags" in statistical_columns
    assert "stability_window" in statistical_columns
    assert "stability_step" in statistical_columns
    assert "stability_window_count" in statistical_columns
    assert "hedge_ratio_stability_std" in statistical_columns
    assert "hedge_ratio_stability_max_abs_change" in statistical_columns
    assert "cointegration_stability_pass_ratio" in statistical_columns
    assert "risk_exit_policy" in backtest_columns
    assert "risk_exit_policy_disabled_reason" in backtest_columns
    upgraded_engine.dispose()

    command.downgrade(config, "0001_backtest_reproducibility_manifest")
    downgraded_engine = create_engine(db_url)
    inspector = inspect(downgraded_engine)
    statistical_columns = {column["name"] for column in inspector.get_columns("statistical_test_results")}
    backtest_columns = {column["name"] for column in inspector.get_columns("backtest_results")}
    assert "residual_ljung_box_p_value" not in statistical_columns
    assert "stability_window" not in statistical_columns
    assert "risk_exit_policy" not in backtest_columns
    downgraded_engine.dispose()
