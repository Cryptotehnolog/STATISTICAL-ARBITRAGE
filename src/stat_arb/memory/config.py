"""Configuration for memory backends."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApeRAGConfig(BaseSettings):
    """Configuration for the active ApeRAG memory backend."""

    model_config = SettingsConfigDict(
        env_prefix="APERAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_base_url: str = Field(
        default="http://127.0.0.1:18000",
        description="Base URL for the ApeRAG API service",
    )
    api_key: str = Field(
        default="",
        description="Bearer API key for ApeRAG",
    )
    collection_title: str = Field(
        default="stat-arb-project-knowledge",
        description="Default ApeRAG collection used for project memory",
    )
    agent_collection_title: str = Field(
        default="stat-arb-agent-memory",
        description="ApeRAG collection used for operational agent memory writes",
    )
    timeout_seconds: float = Field(
        default=60.0,
        description="HTTP timeout in seconds for ApeRAG requests",
        ge=1.0,
    )
    search_top_k: int = Field(
        default=5,
        description="Default top-k for vector and full-text search",
        ge=1,
        le=50,
    )
    search_similarity: float = Field(
        default=0.1,
        description="Default minimum vector similarity for ApeRAG search",
        ge=0.0,
        le=1.0,
    )
    embedding_provider: str = Field(
        default="stat-arb-local-embeddings",
        description="ApeRAG model service provider for embeddings",
    )
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="ApeRAG embedding model",
    )
    completion_provider: str = Field(
        default="stat-arb-omniroute",
        description="ApeRAG model service provider for completion",
    )
    completion_model: str = Field(
        default="my-ai",
        description="ApeRAG completion model or combo",
    )

    @property
    def normalized_api_base_url(self) -> str:
        """Return the ApeRAG API URL without a trailing slash."""
        return self.api_base_url.rstrip("/")
