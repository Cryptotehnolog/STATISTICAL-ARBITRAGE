"""Unit tests for Structured Registry database lifecycle helpers."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from stat_arb.storage.database import (
    DatabaseManager,
    create_database_engine,
    create_session_factory,
    get_database_url,
    get_session,
    init_database,
)


def test_get_database_url_creates_parent_directory(tmp_path) -> None:
    """SQLite URL helper should create parent directories for local registry files."""
    db_path = tmp_path / "nested" / "registry.db"

    url = get_database_url(db_path)

    assert db_path.parent.exists()
    assert url.startswith("sqlite:///")
    assert str(db_path.resolve()) in url


def test_init_database_creates_registry_tables(tmp_path) -> None:
    """Database initialization should create mapped registry tables."""
    engine = init_database(tmp_path / "registry.db")
    try:
        with engine.connect() as connection:
            count = connection.execute(
                text("select count(*) from sqlite_master where type = 'table'")
            ).scalar_one()
        assert count > 0
    finally:
        engine.dispose()


def test_get_session_commits_and_rolls_back(tmp_path) -> None:
    """Session context manager should commit successes and roll back SQLAlchemy failures."""
    engine = create_database_engine(tmp_path / "registry.db")
    try:
        with engine.begin() as connection:
            connection.execute(text("create table sample (id integer primary key, name text unique)"))

        with get_session(engine=engine) as session:
            session.execute(text("insert into sample (name) values ('ok')"))

        with pytest.raises(SQLAlchemyError), get_session(engine=engine) as session:
            session.execute(text("insert into sample (name) values ('duplicate')"))
            session.execute(text("insert into sample (name) values ('duplicate')"))

        with engine.connect() as connection:
            rows = connection.execute(text("select name from sample order by id")).fetchall()
        assert [row[0] for row in rows] == ["ok"]
    finally:
        engine.dispose()


def test_database_manager_session_and_close(tmp_path) -> None:
    """DatabaseManager should expose session lifecycle and dispose cleanly."""
    manager = DatabaseManager(tmp_path / "registry.db")
    try:
        with manager.engine.begin() as connection:
            connection.execute(text("create table sample (id integer primary key, name text)"))

        with manager.session() as session:
            session.execute(text("insert into sample (name) values ('manager')"))

        session_factory = create_session_factory(manager.engine)
        with session_factory() as session:
            count = session.execute(text("select count(*) from sample")).scalar_one()
        assert count == 1
    finally:
        manager.close()
