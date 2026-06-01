"""Unit tests for LightRAG knowledge seeding."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from stat_arb.scripts import seed_lightrag as seed_lightrag_module


def _test_dir(name: str) -> Path:
    path = (Path("data/test_tmp") / f"{name}-{uuid4()}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_discover_source_paths_includes_curated_markdown() -> None:
    """Discovery should include docs, README, and Kiro spec markdown."""
    test_dir = _test_dir("seed-discovery")
    (test_dir / "docs" / "knowledge").mkdir(parents=True)
    (test_dir / ".kiro" / "specs" / "quant").mkdir(parents=True)
    (test_dir / "data").mkdir()
    (test_dir / "README.md").write_text("# Readme\n", encoding="utf-8")
    (test_dir / "docs" / "knowledge" / "future_ideas.md").write_text(
        "# Future Ideas\n",
        encoding="utf-8",
    )
    (test_dir / ".kiro" / "specs" / "quant" / "tasks.md").write_text(
        "# Tasks\n",
        encoding="utf-8",
    )
    (test_dir / "data" / "ignored.md").write_text("# Ignored\n", encoding="utf-8")

    paths = seed_lightrag_module.discover_source_paths(test_dir)
    relative_paths = {path.relative_to(test_dir).as_posix() for path in paths}

    assert relative_paths == {
        "README.md",
        "docs/knowledge/future_ideas.md",
        ".kiro/specs/quant/tasks.md",
    }


def test_changed_documents_uses_manifest_hash() -> None:
    """Only documents with new content hashes should be selected."""
    test_dir = _test_dir("seed-manifest")
    source = test_dir / "README.md"
    source.write_text("# Project\n", encoding="utf-8")
    document = seed_lightrag_module.load_document(source, test_dir)

    unchanged_manifest = {
        "documents": {
            "README.md": {
                "hash": document.content_hash,
            }
        }
    }
    changed_manifest = {"documents": {"README.md": {"hash": "old"}}}

    assert seed_lightrag_module.changed_documents([document], unchanged_manifest) == []
    assert seed_lightrag_module.changed_documents([document], changed_manifest) == [document]


def test_seed_lightrag_dry_run_does_not_insert_or_write_manifest() -> None:
    """Dry run should report changed sources without touching LightRAG."""
    test_dir = _test_dir("seed-dry-run")
    (test_dir / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (test_dir / "README.md").write_text("# Project\n", encoding="utf-8")

    with patch.object(seed_lightrag_module, "LightRAGClient") as client_cls:
        result = seed_lightrag_module.seed_lightrag(dry_run=True, repo_root=test_dir)

    assert result == 0
    client_cls.assert_not_called()
    assert not (test_dir / "data" / "lightrag_seed_manifest.json").exists()


def test_seed_lightrag_inserts_changed_documents_and_updates_manifest() -> None:
    """Changed documents should be inserted and recorded in the manifest."""
    test_dir = _test_dir("seed-write")
    (test_dir / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (test_dir / "docs").mkdir()
    (test_dir / "README.md").write_text("# Project\nImportant decision.\n", encoding="utf-8")
    (test_dir / "docs" / "notes.md").write_text("# Notes\nFuture idea.\n", encoding="utf-8")
    client = MagicMock()
    client.health_check.return_value = {"status": "healthy"}

    with patch.object(seed_lightrag_module, "LightRAGClient", return_value=client):
        result = seed_lightrag_module.seed_lightrag(repo_root=test_dir)

    assert result == 0
    assert client.insert.call_count == 2
    manifest_path = test_dir / "data" / "lightrag_seed_manifest.json"
    manifest = seed_lightrag_module.load_manifest(manifest_path)
    assert set(manifest["documents"]) == {"README.md", "docs/notes.md"}


def test_seed_lightrag_fails_before_insert_when_embedding_check_fails() -> None:
    """Seeding should not update manifest if embeddings are unavailable."""
    test_dir = _test_dir("seed-preflight")
    (test_dir / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (test_dir / "README.md").write_text("# Project\nImportant decision.\n", encoding="utf-8")
    client = MagicMock()
    client.health_check.return_value = {"status": "unhealthy", "error": "model missing"}

    with (
        patch.object(seed_lightrag_module, "LightRAGClient", return_value=client),
        patch.object(seed_lightrag_module.console, "print"),
        pytest.raises(RuntimeError, match="embedding preflight failed"),
    ):
        seed_lightrag_module.seed_lightrag(repo_root=test_dir)

    client.insert.assert_not_called()
    assert not (test_dir / "data" / "lightrag_seed_manifest.json").exists()
