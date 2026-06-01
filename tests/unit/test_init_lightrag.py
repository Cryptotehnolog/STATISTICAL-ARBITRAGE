"""Unit tests for the LightRAG initialization entrypoint."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from stat_arb.scripts import init_lightrag as init_lightrag_module


def _config() -> SimpleNamespace:
    """Create a minimal LightRAG config double for init script tests."""
    return SimpleNamespace(
        vector_store="faiss",
        vector_storage_class="FaissVectorDBStorage",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        embedding_dim=384,
        chunk_size=512,
        chunk_overlap=50,
        storage_path=Path("data/lightrag"),
        vector_store_path=Path("data/vector_store"),
        batch_size=32,
        max_workers=4,
        ensure_directories=MagicMock(),
    )


def _health() -> dict[str, object]:
    """Create a representative health-check response."""
    return {
        "status": "healthy",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dim": 384,
        "embedding_checked": False,
        "vector_store": "faiss",
        "vector_storage_class": "FaissVectorDBStorage",
        "storage_path": "data/lightrag",
        "vector_store_path": "data/vector_store",
        "storage_exists": True,
        "vector_store_exists": True,
        "chunk_size": 512,
        "chunk_overlap": 50,
    }


def test_init_lightrag_default_is_lightweight() -> None:
    """Default init should not insert/query or force embedding checks."""
    config = _config()
    client = MagicMock()
    client.health_check.return_value = _health()

    with (
        patch.object(init_lightrag_module, "LightRAGConfig", return_value=config),
        patch.object(init_lightrag_module, "LightRAGClient", return_value=client),
    ):
        result = init_lightrag_module.init_lightrag()

    assert result == 0
    config.ensure_directories.assert_called_once()
    client.health_check.assert_called_once_with(check_embedding=False)
    client.insert.assert_not_called()
    client.query.assert_not_called()


def test_init_lightrag_smoke_test_runs_rag_operations() -> None:
    """Smoke test should explicitly exercise insert/query behavior."""
    config = _config()
    client = MagicMock()
    client.health_check.return_value = {**_health(), "embedding_checked": True}
    client.query.return_value = "LightRAG stores agent decisions."

    with (
        patch.object(init_lightrag_module, "LightRAGConfig", return_value=config),
        patch.object(init_lightrag_module, "LightRAGClient", return_value=client),
    ):
        result = init_lightrag_module.init_lightrag(smoke_test=True)

    assert result == 0
    client.health_check.assert_called_once_with(check_embedding=True)
    client.insert.assert_called_once()
    client.query.assert_called_once_with("What does LightRAG store?", mode="hybrid", top_k=1)
