"""Unit tests for LightRAG configuration."""

from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from stat_arb.memory.config import LightRAGConfig


class TestLightRAGConfig:
    """Test LightRAG configuration."""

    def _test_dir(self, name: str) -> Path:
        """Return an ignored project-local path for filesystem tests."""
        return Path("data/test_tmp") / f"{name}-{uuid4()}"

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = LightRAGConfig()

        assert config.vector_store in ["faiss", "nano"]
        assert config.vector_storage_class == "FaissVectorDBStorage"
        assert config.vector_storage_kwargs == {"cosine_better_than_threshold": 0.2}
        assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.embedding_local_files_only is False
        assert config.llm_provider == "noop"
        assert config.ollama_model == "qwen2.5:3b"
        assert config.ollama_base_url == "http://localhost:11434"
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.embedding_dim == 384
        assert config.batch_size == 32
        assert config.max_workers == 4

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        test_dir = self._test_dir("config")
        storage_path = test_dir / "lightrag"
        vector_store_path = test_dir / "vector_store"

        config = LightRAGConfig(
            vector_store="nano",
            chunk_size=256,
            chunk_overlap=25,
            storage_path=storage_path,
            vector_store_path=vector_store_path,
        )

        assert config.vector_store == "nano"
        assert config.vector_storage_class == "NanoVectorDBStorage"
        assert config.vector_storage_kwargs == {}
        assert config.chunk_size == 256
        assert config.chunk_overlap == 25
        assert config.storage_path == storage_path
        assert config.vector_store_path == vector_store_path

    def test_ensure_directories(self) -> None:
        """Test directory creation."""
        test_dir = self._test_dir("directories")
        storage_path = test_dir / "lightrag"
        vector_store_path = test_dir / "vector_store"

        config = LightRAGConfig(
            storage_path=storage_path,
            vector_store_path=vector_store_path,
        )

        # Directories should not exist yet
        assert not storage_path.exists()
        assert not vector_store_path.exists()

        # Create directories
        config.ensure_directories()

        # Directories should now exist
        assert storage_path.exists()
        assert storage_path.is_dir()
        assert vector_store_path.exists()
        assert vector_store_path.is_dir()

    def test_faiss_paths(self) -> None:
        """Test FAISS-specific paths."""
        vector_store_path = self._test_dir("faiss") / "vector_store"

        config = LightRAGConfig(
            vector_store="faiss",
            vector_store_path=vector_store_path,
        )

        assert config.faiss_index_path == vector_store_path / "index.faiss"
        assert config.faiss_metadata_path == vector_store_path / "metadata.json"

    def test_cosine_threshold_validation(self) -> None:
        """Test cosine threshold validation."""
        config = LightRAGConfig(cosine_threshold=0.0)
        assert config.cosine_threshold == 0.0

        config = LightRAGConfig(cosine_threshold=1.0)
        assert config.cosine_threshold == 1.0

        with pytest.raises(ValidationError):
            LightRAGConfig(cosine_threshold=-0.1)

        with pytest.raises(ValidationError):
            LightRAGConfig(cosine_threshold=1.1)

    def test_chunk_size_validation(self) -> None:
        """Test chunk size validation."""
        # Valid chunk sizes
        config = LightRAGConfig(chunk_size=128)
        assert config.chunk_size == 128

        config = LightRAGConfig(chunk_size=2048)
        assert config.chunk_size == 2048

        # Invalid chunk sizes should raise validation error
        with pytest.raises(ValidationError):
            LightRAGConfig(chunk_size=64)  # Too small

        with pytest.raises(ValidationError):
            LightRAGConfig(chunk_size=4096)  # Too large

    def test_chunk_overlap_validation(self) -> None:
        """Test chunk overlap validation."""
        # Valid overlaps
        config = LightRAGConfig(chunk_overlap=0)
        assert config.chunk_overlap == 0

        config = LightRAGConfig(chunk_overlap=256)
        assert config.chunk_overlap == 256

        # Invalid overlaps should raise validation error
        with pytest.raises(ValidationError):
            LightRAGConfig(chunk_overlap=-1)  # Negative

        with pytest.raises(ValidationError):
            LightRAGConfig(chunk_overlap=512)  # Too large
