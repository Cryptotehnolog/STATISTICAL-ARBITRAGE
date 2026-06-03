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


def test_discover_source_paths_accepts_custom_patterns() -> None:
    """Discovery should support curated-only source patterns."""
    test_dir = _test_dir("seed-custom-pattern")
    (test_dir / "docs" / "knowledge").mkdir(parents=True)
    (test_dir / ".kiro" / "specs" / "quant").mkdir(parents=True)
    (test_dir / "README.md").write_text("# Readme\n", encoding="utf-8")
    (test_dir / "docs" / "knowledge" / "future_ideas.md").write_text(
        "# Future Ideas\n",
        encoding="utf-8",
    )
    (test_dir / ".kiro" / "specs" / "quant" / "tasks.md").write_text(
        "# Tasks\n",
        encoding="utf-8",
    )

    paths = seed_lightrag_module.discover_source_paths(
        test_dir,
        patterns=("docs/knowledge/*.md",),
    )
    relative_paths = {path.relative_to(test_dir).as_posix() for path in paths}

    assert relative_paths == {"docs/knowledge/future_ideas.md"}


def test_curated_seed_wrapper_uses_bounded_but_large_enough_limits() -> None:
    """Curated seed wrapper should fit current curated shards without unbounded seeding."""
    script = Path("scripts/seed_lightrag_curated.ps1").read_text(encoding="utf-8")

    assert "[int]$MaxDocumentChars = 12000" in script
    assert "[int]$MaxTotalChars = 50000" in script
    assert '"docs/knowledge/*.md"' in script


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


def test_limit_documents_skips_large_documents() -> None:
    """Per-document limits should skip oversized sources."""
    test_dir = _test_dir("seed-limit-document")
    small = test_dir / "small.md"
    large = test_dir / "large.md"
    small.write_text("# Small\nok\n", encoding="utf-8")
    large.write_text("# Large\n" + ("x" * 20), encoding="utf-8")
    documents = [
        seed_lightrag_module.load_document(small, test_dir),
        seed_lightrag_module.load_document(large, test_dir),
    ]

    selected, skipped = seed_lightrag_module.limit_documents(
        documents,
        max_document_chars=15,
    )

    assert [document.source_id for document in selected] == ["small.md"]
    assert [item.document.source_id for item in skipped] == ["large.md"]
    assert "exceeds max document" in skipped[0].reason


def test_limit_documents_respects_total_limit() -> None:
    """Total limits should keep the first fitting documents and skip the rest."""
    test_dir = _test_dir("seed-limit-total")
    first = test_dir / "first.md"
    second = test_dir / "second.md"
    first.write_text("# First\n12345\n", encoding="utf-8")
    second.write_text("# Second\n12345\n", encoding="utf-8")
    documents = [
        seed_lightrag_module.load_document(first, test_dir),
        seed_lightrag_module.load_document(second, test_dir),
    ]

    selected, skipped = seed_lightrag_module.limit_documents(
        documents,
        max_total_chars=len(documents[0].content),
    )

    assert [document.source_id for document in selected] == ["first.md"]
    assert [item.document.source_id for item in skipped] == ["second.md"]
    assert "total would exceed" in skipped[0].reason


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


def test_seed_lightrag_force_inserts_unchanged_documents() -> None:
    """Force mode should seed matching documents even when hashes are unchanged."""
    test_dir = _test_dir("seed-force")
    (test_dir / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (test_dir / "docs" / "knowledge").mkdir(parents=True)
    source = test_dir / "docs" / "knowledge" / "future_ideas.md"
    source.write_text("# Future Ideas\nAutomate memory upkeep.\n", encoding="utf-8")
    document = seed_lightrag_module.load_document(source, test_dir)
    manifest_path = test_dir / "data" / "lightrag_seed_manifest.json"
    seed_lightrag_module.save_manifest(
        manifest_path,
        {
            "version": 1,
            "documents": {
                document.source_id: {
                    "hash": document.content_hash,
                    "title": document.title,
                }
            },
        },
    )
    client = MagicMock()
    client.health_check.return_value = {"status": "healthy"}

    with patch.object(seed_lightrag_module, "LightRAGClient", return_value=client):
        result = seed_lightrag_module.seed_lightrag(
            repo_root=test_dir,
            source_patterns=("docs/knowledge/*.md",),
            force=True,
        )

    assert result == 0
    client.insert.assert_called_once()


def test_seed_lightrag_passes_max_workers_to_config() -> None:
    """Seeding should allow callers to reduce LightRAG concurrency."""
    test_dir = _test_dir("seed-max-workers")
    (test_dir / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (test_dir / "README.md").write_text("# Project\n", encoding="utf-8")
    client = MagicMock()
    client.health_check.return_value = {"status": "healthy"}

    with (
        patch.object(seed_lightrag_module, "LightRAGClient", return_value=client),
        patch.object(seed_lightrag_module, "LightRAGConfig") as config_cls,
    ):
        result = seed_lightrag_module.seed_lightrag(
            repo_root=test_dir,
            max_workers=1,
        )

    assert result == 0
    assert config_cls.call_args.kwargs["max_workers"] == 1


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
