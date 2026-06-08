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


def test_alembic_database_url_can_be_overridden() -> None:
    """Tests and deployment scripts should be able to target an explicit DB URL."""
    config = get_alembic_config(db_url="sqlite:///custom.db")

    assert config.get_main_option("sqlalchemy.url") == "sqlite:///custom.db"
