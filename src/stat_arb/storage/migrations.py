"""
Database migration utilities for the Structured Registry.

This module provides utilities for managing database schema migrations
using Alembic. It supports:
- Generating migration scripts from model changes
- Applying migrations (upgrade)
- Reverting migrations (downgrade)
- Checking migration status

Requirements: 9.1-9.11, 27.14
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


# Default Alembic configuration directory
DEFAULT_ALEMBIC_DIR = Path("alembic")


def get_alembic_config(alembic_dir: Path | None = None, db_url: str | None = None) -> Config:
    """
    Get Alembic configuration.

    Args:
        alembic_dir: Path to the Alembic directory. If None, uses DEFAULT_ALEMBIC_DIR.
        db_url: Database URL to use. If None, uses the URL from alembic.ini.

    Returns:
        Alembic Config instance.
    """
    if alembic_dir is None:
        alembic_dir = DEFAULT_ALEMBIC_DIR

    alembic_ini = alembic_dir / "alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(
            f"Alembic configuration not found at {alembic_ini}. "
            "Run 'alembic init alembic' to initialize."
        )

    config = Config(str(alembic_ini))

    # Override database URL if provided
    if db_url:
        config.set_main_option("sqlalchemy.url", db_url)

    return config


def create_migration(
    message: str,
    alembic_dir: Path | None = None,
    db_url: str | None = None,
    autogenerate: bool = True,
) -> None:
    """
    Create a new migration script.

    Args:
        message: Migration message (e.g., "add_user_table").
        alembic_dir: Path to the Alembic directory. If None, uses DEFAULT_ALEMBIC_DIR.
        db_url: Database URL to use. If None, uses the URL from alembic.ini.
        autogenerate: If True, automatically detect model changes.
    """
    config = get_alembic_config(alembic_dir, db_url)

    logger.info(f"Creating migration: {message}")

    if autogenerate:
        command.revision(config, message=message, autogenerate=True)
    else:
        command.revision(config, message=message)

    logger.info("Migration created successfully.")


def upgrade_database(
    revision: str = "head",
    alembic_dir: Path | None = None,
    db_url: str | None = None,
) -> None:
    """
    Upgrade the database to a specific revision.

    Args:
        revision: Target revision (default: "head" for latest).
        alembic_dir: Path to the Alembic directory. If None, uses DEFAULT_ALEMBIC_DIR.
        db_url: Database URL to use. If None, uses the URL from alembic.ini.
    """
    config = get_alembic_config(alembic_dir, db_url)

    logger.info(f"Upgrading database to revision: {revision}")
    command.upgrade(config, revision)
    logger.info("Database upgrade complete.")


def downgrade_database(
    revision: str = "-1",
    alembic_dir: Path | None = None,
    db_url: str | None = None,
) -> None:
    """
    Downgrade the database to a specific revision.

    Args:
        revision: Target revision (default: "-1" for previous revision).
        alembic_dir: Path to the Alembic directory. If None, uses DEFAULT_ALEMBIC_DIR.
        db_url: Database URL to use. If None, uses the URL from alembic.ini.
    """
    config = get_alembic_config(alembic_dir, db_url)

    logger.info(f"Downgrading database to revision: {revision}")
    command.downgrade(config, revision)
    logger.info("Database downgrade complete.")


def show_current_revision(alembic_dir: Path | None = None, db_url: str | None = None) -> None:
    """
    Show the current database revision.

    Args:
        alembic_dir: Path to the Alembic directory. If None, uses DEFAULT_ALEMBIC_DIR.
        db_url: Database URL to use. If None, uses the URL from alembic.ini.
    """
    config = get_alembic_config(alembic_dir, db_url)

    logger.info("Current database revision:")
    command.current(config)


def show_migration_history(alembic_dir: Path | None = None, db_url: str | None = None) -> None:
    """
    Show the migration history.

    Args:
        alembic_dir: Path to the Alembic directory. If None, uses DEFAULT_ALEMBIC_DIR.
        db_url: Database URL to use. If None, uses the URL from alembic.ini.
    """
    config = get_alembic_config(alembic_dir, db_url)

    logger.info("Migration history:")
    command.history(config)


def stamp_database(
    revision: str = "head",
    alembic_dir: Path | None = None,
    db_url: str | None = None,
) -> None:
    """
    Stamp the database with a specific revision without running migrations.

    Useful for marking an existing database as being at a specific revision.

    Args:
        revision: Target revision (default: "head" for latest).
        alembic_dir: Path to the Alembic directory. If None, uses DEFAULT_ALEMBIC_DIR.
        db_url: Database URL to use. If None, uses the URL from alembic.ini.
    """
    config = get_alembic_config(alembic_dir, db_url)

    logger.info(f"Stamping database with revision: {revision}")
    command.stamp(config, revision)
    logger.info("Database stamped successfully.")


class MigrationManager:
    """
    Migration manager for the Structured Registry.

    Provides a high-level interface for database migrations using Alembic.
    """

    def __init__(self, alembic_dir: Path | None = None, db_url: str | None = None):
        """
        Initialize the migration manager.

        Args:
            alembic_dir: Path to the Alembic directory. If None, uses DEFAULT_ALEMBIC_DIR.
            db_url: Database URL to use. If None, uses the URL from alembic.ini.
        """
        self.alembic_dir = alembic_dir or DEFAULT_ALEMBIC_DIR
        self.db_url = db_url
        self.config = get_alembic_config(alembic_dir, db_url)

    def create_migration(self, message: str, autogenerate: bool = True) -> None:
        """
        Create a new migration script.

        Args:
            message: Migration message (e.g., "add_user_table").
            autogenerate: If True, automatically detect model changes.
        """
        create_migration(message, self.alembic_dir, self.db_url, autogenerate)

    def upgrade(self, revision: str = "head") -> None:
        """
        Upgrade the database to a specific revision.

        Args:
            revision: Target revision (default: "head" for latest).
        """
        upgrade_database(revision, self.alembic_dir, self.db_url)

    def downgrade(self, revision: str = "-1") -> None:
        """
        Downgrade the database to a specific revision.

        Args:
            revision: Target revision (default: "-1" for previous revision).
        """
        downgrade_database(revision, self.alembic_dir, self.db_url)

    def current(self) -> None:
        """Show the current database revision."""
        show_current_revision(self.alembic_dir, self.db_url)

    def history(self) -> None:
        """Show the migration history."""
        show_migration_history(self.alembic_dir, self.db_url)

    def stamp(self, revision: str = "head") -> None:
        """
        Stamp the database with a specific revision without running migrations.

        Args:
            revision: Target revision (default: "head" for latest).
        """
        stamp_database(revision, self.alembic_dir, self.db_url)


# Export public API
__all__ = [
    "get_alembic_config",
    "create_migration",
    "upgrade_database",
    "downgrade_database",
    "show_current_revision",
    "show_migration_history",
    "stamp_database",
    "MigrationManager",
    "DEFAULT_ALEMBIC_DIR",
]
