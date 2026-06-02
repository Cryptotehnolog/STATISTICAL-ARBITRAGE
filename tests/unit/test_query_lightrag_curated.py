"""Unit tests for curated LightRAG query smoke."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from stat_arb.scripts import query_lightrag_curated as query_module


def _repo_root(name: str) -> Path:
    path = (Path("data/test_tmp") / f"{name}-{uuid4()}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    (path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    return path


def test_query_lightrag_curated_passes_when_expected_terms_are_returned() -> None:
    """Query smoke should pass when the answer includes required terms."""
    client = MagicMock()
    client.health_check.return_value = {"status": "healthy"}
    client.query.return_value = "Use OmniRoute and seed docs/knowledge curated shards."

    with patch.object(query_module, "LightRAGClient", return_value=client):
        result = query_module.query_lightrag_curated(
            repo_root=_repo_root("query-smoke-pass")
        )

    assert result == 0
    client.query.assert_called_once()


def test_query_lightrag_curated_fails_when_expected_terms_are_missing() -> None:
    """Query smoke should fail when the answer misses required project terms."""
    client = MagicMock()
    client.health_check.return_value = {"status": "healthy"}
    client.query.return_value = "No relevant project memory found."

    with patch.object(query_module, "LightRAGClient", return_value=client):
        result = query_module.query_lightrag_curated(
            repo_root=_repo_root("query-smoke-missing")
        )

    assert result == 1


def test_query_lightrag_curated_fails_when_embedding_preflight_fails() -> None:
    """Query smoke should fail before querying if embeddings are unavailable."""
    client = MagicMock()
    client.health_check.return_value = {"status": "unhealthy"}

    with patch.object(query_module, "LightRAGClient", return_value=client):
        result = query_module.query_lightrag_curated(
            repo_root=_repo_root("query-smoke-preflight")
        )

    assert result == 1
    client.query.assert_not_called()
