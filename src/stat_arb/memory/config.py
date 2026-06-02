"""Configuration for LightRAG memory system."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LightRAGConfig(BaseSettings):
    """Configuration for LightRAG with embedded vector store.

    This configuration supports minimal infrastructure setup using
    embedded vector stores (FAISS or NanoVectorDB) without requiring Docker
    or separate server processes.
    """

    model_config = SettingsConfigDict(
        env_prefix="LIGHTRAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Vector store backend
    vector_store: Literal["faiss", "nano"] = Field(
        default="faiss",
        description="Vector store backend: 'faiss' or 'nano' (both embedded)",
    )

    cosine_threshold: float = Field(
        default=0.2,
        description="Minimum cosine similarity threshold for vector retrieval",
        ge=0.0,
        le=1.0,
    )

    # Embedding model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence-transformers model for embeddings (384 dimensions)",
    )

    embedding_local_files_only: bool = Field(
        default=False,
        description="Load embedding model only from local cache",
    )

    # LLM provider for LightRAG entity and relationship extraction
    llm_provider: Literal["noop", "openai_compatible"] = Field(
        default="noop",
        description=(
            "LLM provider for LightRAG extraction: 'noop' or 'openai_compatible'"
        ),
    )

    openai_compatible_model: str = Field(
        default="my-ai",
        description="Model or combo name for an OpenAI-compatible LLM gateway",
    )

    openai_compatible_base_url: str = Field(
        default="http://localhost:20128/v1",
        description="Base URL for an OpenAI-compatible LLM gateway",
    )

    openai_compatible_api_key: str = Field(
        default="",
        description="API key for an OpenAI-compatible LLM gateway",
    )

    openai_compatible_timeout: float = Field(
        default=180.0,
        description="Timeout in seconds for OpenAI-compatible generation requests",
        ge=1.0,
    )

    openai_compatible_system_prompt: str = Field(
        default=(
            "Отвечай на русском языке. Сохраняй профессиональные термины, "
            "имена классов, названия моделей, тикеры, команды и пути к файлам "
            "на языке оригинала."
        ),
        description="System prompt for OpenAI-compatible LightRAG LLM calls",
    )

    @property
    def llm_timeout(self) -> float:
        """Return the active LLM provider timeout."""
        return self.openai_compatible_timeout

    # Storage paths
    storage_path: Path = Field(
        default=Path("./data/lightrag"),
        description="Base storage path for LightRAG data",
    )

    vector_store_path: Path = Field(
        default=Path("./data/vector_store"),
        description="Path for embedded vector store metadata and indexes",
    )

    # Chunking configuration
    chunk_size: int = Field(
        default=512,
        description="Chunk size in tokens for document splitting",
        ge=128,
        le=2048,
    )

    chunk_overlap: int = Field(
        default=50,
        description="Overlap in tokens between consecutive chunks",
        ge=0,
        le=256,
    )

    # Embedding dimensions (read-only, determined by model)
    embedding_dim: int = Field(
        default=384,
        description="Embedding dimensions for all-MiniLM-L6-v2",
    )

    # Performance settings
    batch_size: int = Field(
        default=32,
        description="Batch size for embedding generation",
        ge=1,
        le=128,
    )

    max_workers: int = Field(
        default=4,
        description="Maximum worker threads for parallel processing",
        ge=1,
        le=16,
    )

    @property
    def vector_storage_class(self) -> str:
        """LightRAG vector storage class name for the configured backend."""
        return {
            "faiss": "FaissVectorDBStorage",
            "nano": "NanoVectorDBStorage",
        }[self.vector_store]

    @property
    def vector_storage_kwargs(self) -> dict[str, float]:
        """Backend-specific LightRAG vector storage kwargs."""
        if self.vector_store == "faiss":
            return {"cosine_better_than_threshold": self.cosine_threshold}
        return {}

    def ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.vector_store_path.mkdir(parents=True, exist_ok=True)

    @property
    def faiss_index_path(self) -> Path:
        """Path to FAISS index file."""
        return self.vector_store_path / "index.faiss"

    @property
    def faiss_metadata_path(self) -> Path:
        """Path to FAISS metadata file."""
        return self.vector_store_path / "metadata.json"
