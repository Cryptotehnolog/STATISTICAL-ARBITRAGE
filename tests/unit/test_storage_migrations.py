"""Tests for Structured Registry Alembic migration configuration."""

from pathlib import Path

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
