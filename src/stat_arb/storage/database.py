"""
Database initialization and session management for the Structured Registry.

This module provides utilities for:
- Creating and initializing the SQLite database
- Managing database sessions
- Database connection configuration

Requirements: 9.1-9.11, 27.14
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

logger = logging.getLogger(__name__)


# Default database path (can be overridden via environment variable)
DEFAULT_DB_PATH = Path("data/registry.db")


def get_database_url(db_path: Path | None = None) -> str:
    """
    Get the database URL for SQLite.

    Args:
        db_path: Path to the SQLite database file. If None, uses DEFAULT_DB_PATH.

    Returns:
        SQLAlchemy database URL string.
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to absolute path for SQLite
    abs_path = db_path.resolve()

    return f"sqlite:///{abs_path}"


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, _connection_record):
    """
    Enable foreign key constraints for SQLite.

    SQLite has foreign keys disabled by default. This event listener
    enables them for every connection.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_database_engine(db_path: Path | None = None, echo: bool = False) -> Engine:
    """
    Create a SQLAlchemy engine for the database.

    Args:
        db_path: Path to the SQLite database file. If None, uses DEFAULT_DB_PATH.
        echo: If True, log all SQL statements (useful for debugging).

    Returns:
        SQLAlchemy Engine instance.
    """
    database_url = get_database_url(db_path)
    logger.info(f"Creating database engine: {database_url}")

    engine = create_engine(
        database_url,
        echo=echo,
        # SQLite-specific settings
        connect_args={"check_same_thread": False},  # Allow multi-threaded access
        pool_pre_ping=True,  # Verify connections before using
    )

    return engine


def init_database(db_path: Path | None = None, drop_existing: bool = False) -> Engine:
    """
    Initialize the database by creating all tables.

    Args:
        db_path: Path to the SQLite database file. If None, uses DEFAULT_DB_PATH.
        drop_existing: If True, drop all existing tables before creating new ones.
                      WARNING: This will delete all data!

    Returns:
        SQLAlchemy Engine instance.
    """
    engine = create_database_engine(db_path)

    if drop_existing:
        logger.warning("Dropping all existing tables!")
        Base.metadata.drop_all(engine)

    logger.info("Creating database tables...")
    Base.metadata.create_all(engine)
    logger.info("Database initialization complete.")

    return engine


def create_session_factory(engine: Engine) -> sessionmaker:
    """
    Create a session factory for the given engine.

    Args:
        engine: SQLAlchemy Engine instance.

    Returns:
        Session factory (sessionmaker instance).
    """
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session(
    db_path: Path | None = None, engine: Engine | None = None
) -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_session() as session:
            hypothesis = session.query(Hypothesis).first()
            print(hypothesis.asset_a)

    Args:
        db_path: Path to the SQLite database file. If None, uses DEFAULT_DB_PATH.
        engine: Existing SQLAlchemy Engine. If provided, db_path is ignored.

    Yields:
        SQLAlchemy Session instance.
    """
    if engine is None:
        engine = create_database_engine(db_path)

    SessionFactory = create_session_factory(engine)
    session = SessionFactory()

    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


class DatabaseManager:
    """
    Database manager for the Structured Registry.

    Provides a high-level interface for database operations with
    connection pooling and session management.
    """

    def __init__(self, db_path: Path | None = None, echo: bool = False):
        """
        Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file. If None, uses DEFAULT_DB_PATH.
            echo: If True, log all SQL statements (useful for debugging).
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.engine = create_database_engine(db_path, echo=echo)
        self.SessionFactory = create_session_factory(self.engine)

    def init_database(self, drop_existing: bool = False) -> None:
        """
        Initialize the database by creating all tables.

        Args:
            drop_existing: If True, drop all existing tables before creating new ones.
                          WARNING: This will delete all data!
        """
        if drop_existing:
            logger.warning("Dropping all existing tables!")
            Base.metadata.drop_all(self.engine)

        logger.info("Creating database tables...")
        Base.metadata.create_all(self.engine)
        logger.info("Database initialization complete.")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.

        Usage:
            db = DatabaseManager()
            with db.session() as session:
                hypothesis = session.query(Hypothesis).first()
                print(hypothesis.asset_a)

        Yields:
            SQLAlchemy Session instance.
        """
        session = self.SessionFactory()

        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def close(self) -> None:
        """Close the database engine and all connections."""
        self.engine.dispose()
        logger.info("Database connections closed.")


# Export public API
__all__ = [
    "get_database_url",
    "create_database_engine",
    "init_database",
    "create_session_factory",
    "get_session",
    "DatabaseManager",
    "DEFAULT_DB_PATH",
]
