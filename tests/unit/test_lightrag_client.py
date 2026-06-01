"""Unit tests for LightRAG client."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest

from stat_arb.memory.config import LightRAGConfig
from stat_arb.memory.lightrag_client import LightRAGClient


class TestLightRAGClient:
    """Test LightRAG client."""

    def _mock_embedding_model(self, embedding_dim: int) -> MagicMock:
        """Create a deterministic embedding model mock."""
        model = MagicMock()

        def encode(texts, **_kwargs):
            return np.ones((len(texts), embedding_dim), dtype=float)

        model.encode.side_effect = encode
        return model

    @pytest.fixture
    def temp_config(self) -> LightRAGConfig:
        """Create temporary configuration for testing."""
        test_dir = Path("data/test_tmp") / f"lightrag-client-{uuid4()}"
        return LightRAGConfig(
            storage_path=test_dir / "lightrag",
            vector_store_path=test_dir / "vector_store",
            vector_store="faiss",
        )

    def test_client_initialization(self, temp_config: LightRAGConfig) -> None:
        """Test client initialization."""
        client = LightRAGClient(temp_config)

        assert client.config == temp_config
        assert client.config.storage_path.exists()
        assert client.config.vector_store_path.exists()

    def test_embedding_model_lazy_loading(self, temp_config: LightRAGConfig) -> None:
        """Test embedding model is lazy-loaded."""
        client = LightRAGClient(temp_config)

        # Model should not be loaded yet
        assert client._embedding_model is None

        with patch(
            "stat_arb.memory.lightrag_client.SentenceTransformer",
            return_value=self._mock_embedding_model(temp_config.embedding_dim),
        ) as sentence_transformer:
            # Access model property
            model = client.embedding_model

        # Model should now be loaded
        sentence_transformer.assert_called_once_with(temp_config.embedding_model)
        assert model is not None
        assert client._embedding_model is not None

    def test_embedding_function(self, temp_config: LightRAGConfig) -> None:
        """Test embedding function."""
        client = LightRAGClient(temp_config)

        texts = ["test document 1", "test document 2"]
        with patch(
            "stat_arb.memory.lightrag_client.SentenceTransformer",
            return_value=self._mock_embedding_model(temp_config.embedding_dim),
        ):
            embeddings = client._embed_func(texts)

        assert len(embeddings) == 2
        assert len(embeddings[0]) == temp_config.embedding_dim
        assert len(embeddings[1]) == temp_config.embedding_dim
        assert all(isinstance(x, float) for x in embeddings[0])

    def test_initialize_lightrag_uses_configured_vector_storage(
        self, temp_config: LightRAGConfig
    ) -> None:
        """Test LightRAG receives the configured vector storage backend."""
        client = LightRAGClient(temp_config)

        with patch("stat_arb.memory.lightrag_client.LightRAG") as lightrag:
            rag = client._initialize_lightrag()

        assert rag == lightrag.return_value
        _, kwargs = lightrag.call_args
        assert kwargs["vector_storage"] == "FaissVectorDBStorage"
        assert kwargs["vector_db_storage_cls_kwargs"] == {
            "cosine_better_than_threshold": temp_config.cosine_threshold
        }
        assert kwargs["embedding_batch_num"] == temp_config.batch_size
        assert kwargs["embedding_func_max_async"] == temp_config.max_workers

    def test_health_check(self, temp_config: LightRAGConfig) -> None:
        """Test lightweight health check."""
        client = LightRAGClient(temp_config)

        health = client.health_check()

        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert health["embedding_checked"] is False
        assert health["embedding_model"] == temp_config.embedding_model
        assert health["embedding_dim"] == temp_config.embedding_dim
        assert health["vector_store"] == temp_config.vector_store
        assert health["vector_storage_class"] == temp_config.vector_storage_class
        assert health["chunk_size"] == temp_config.chunk_size
        assert health["chunk_overlap"] == temp_config.chunk_overlap
        assert client._embedding_model is None

    def test_health_check_with_embedding(self, temp_config: LightRAGConfig) -> None:
        """Test optional embedding health check."""
        client = LightRAGClient(temp_config)

        with patch(
            "stat_arb.memory.lightrag_client.SentenceTransformer",
            return_value=self._mock_embedding_model(temp_config.embedding_dim),
        ):
            health = client.health_check(check_embedding=True)

        assert "status" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        assert health["embedding_checked"] is True
        assert health["embedding_model"] == temp_config.embedding_model
        assert health["embedding_dim"] == temp_config.embedding_dim
        assert health["vector_store"] == temp_config.vector_store
        assert health["chunk_size"] == temp_config.chunk_size
        assert health["chunk_overlap"] == temp_config.chunk_overlap

    @pytest.mark.slow
    def test_insert_and_query(self, temp_config: LightRAGConfig) -> None:
        """Test inserting and querying documents.

        Note: This test is marked as slow because it initializes
        the full LightRAG system and performs actual operations.
        """
        client = LightRAGClient(temp_config)

        # Insert test document
        test_text = """
        This is a test document about statistical arbitrage.
        Statistical arbitrage involves trading pairs of cointegrated assets.
        The strategy aims to profit from mean reversion of the spread.
        """

        client.insert(test_text)

        # Query for the document
        result = client.query("What is statistical arbitrage?", mode="naive", top_k=1)

        # Result should contain relevant information
        assert isinstance(result, str)
        assert len(result) > 0

    def test_store_hypothesis(self, temp_config: LightRAGConfig) -> None:
        """Test storing hypothesis."""
        client = LightRAGClient(temp_config)

        with patch.object(client, "insert") as insert:
            client.store_hypothesis(
                hypothesis_id="test-hyp-001",
                asset_a="AAPL",
                asset_b="MSFT",
                rationale="Both are large-cap tech companies",
                source="test",
                similar_hypotheses=["test-hyp-000"],
            )

        insert.assert_called_once()
        text, metadata = insert.call_args.args
        assert "AAPL / MSFT" in text
        assert metadata["type"] == "hypothesis"
        assert metadata["hypothesis_id"] == "test-hyp-001"

    def test_store_test_summary(self, temp_config: LightRAGConfig) -> None:
        """Test storing test summary."""
        client = LightRAGClient(temp_config)

        with patch.object(client, "insert") as insert:
            client.store_test_summary(
                test_id="test-001",
                hypothesis_id="hyp-001",
                passed=True,
                summary="Cointegration test passed with p-value < 0.05",
            )

        insert.assert_called_once()
        text, metadata = insert.call_args.args
        assert "PASSED" in text
        assert metadata["type"] == "statistical_test"
        assert metadata["passed"] is True

    def test_store_backtest_summary(self, temp_config: LightRAGConfig) -> None:
        """Test storing backtest summary."""
        client = LightRAGClient(temp_config)

        with patch.object(client, "insert") as insert:
            client.store_backtest_summary(
                backtest_id="bt-001",
                hypothesis_id="hyp-001",
                conclusion="Strategy shows positive net PnL after costs",
                lessons_learned="Transaction costs significantly impact profitability",
            )

        insert.assert_called_once()
        text, metadata = insert.call_args.args
        assert "BACKTEST SUMMARY" in text
        assert metadata["type"] == "backtest"
        assert metadata["backtest_id"] == "bt-001"

    def test_store_critic_review(self, temp_config: LightRAGConfig) -> None:
        """Test storing critic review."""
        client = LightRAGClient(temp_config)

        with patch.object(client, "insert") as insert:
            client.store_critic_review(
                review_id="rev-001",
                backtest_id="bt-001",
                objections="No critical issues detected",
                recommendation="Approved for human review",
            )

        insert.assert_called_once()
        text, metadata = insert.call_args.args
        assert "CRITIC REVIEW" in text
        assert metadata["type"] == "critic_review"
        assert metadata["review_id"] == "rev-001"

    def test_store_architecture_decision(self, temp_config: LightRAGConfig) -> None:
        """Test storing architecture decision."""
        client = LightRAGClient(temp_config)

        with patch.object(client, "insert") as insert:
            client.store_architecture_decision(
                decision_id="dec-001",
                title="Use embedded vector store",
                decision="Use FAISS for v1 MVP",
                rationale="Minimal infrastructure, no Docker required",
                alternatives="Chroma server, Neo4j",
                risks="May need to migrate later for better performance",
            )

        insert.assert_called_once()
        text, metadata = insert.call_args.args
        assert "ARCHITECTURE DECISION" in text
        assert metadata["type"] == "architecture_decision"
        assert metadata["decision_id"] == "dec-001"

    def test_insert_with_metadata(self, temp_config: LightRAGConfig) -> None:
        """Test inserting document with metadata."""
        client = LightRAGClient(temp_config)
        client._rag = MagicMock()

        metadata = {
            "type": "test",
            "category": "unit_test",
            "tags": ["testing", "metadata"],
        }

        client.insert("Test document with metadata", metadata=metadata)

        client._rag.insert.assert_called_once()
        inserted_text = client._rag.insert.call_args.args[0]
        assert "METADATA:" in inserted_text
        assert '"type": "test"' in inserted_text
        assert "CONTENT:\nTest document with metadata" in inserted_text
