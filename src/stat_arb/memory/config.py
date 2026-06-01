"""Configuration for LightRAG memory system."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LightRAGConfig(BaseSettings):
    """Configuration for LightRAG with embedded vector store.

    This configuration supports minimal infrastructure setup using
    embedded vector stores (FAISS or Chroma) without requiring Docker
    or separate server processes.
    """

    model_config = SettingsConfigDict(
        env_prefix="LIGHTRAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Vector store backend
    vector_store: Literal["faiss", "chroma"] = Field(
        default="faiss",
        description="Vector store backend: 'faiss' or 'chroma' (both embedded)",
    )

    # Embedding model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Sentence-transformers model for embeddings (384 dimensions)",
    )

    # Storage paths
    storage_path: Path = Field(
        default=Path("./data/lightrag"),
        description="Base storage path for LightRAG data",
    )

    vector_store_path: Path = Field(
        default=Path("./data/vector_store"),
        description="Path for embedded vector store (FAISS index or Chroma DB)",
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

    @property
    def chroma_db_path(self) -> Path:
        """Path to Chroma database directory."""
        return self.vector_store_path / "chroma_db"
