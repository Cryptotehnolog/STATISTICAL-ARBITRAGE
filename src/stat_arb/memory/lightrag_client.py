"""LightRAG client for long-term memory and knowledge graph operations."""

import asyncio
import inspect
import json
import logging
from typing import Any

import httpx
import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.base import EmbeddingFunc
from sentence_transformers import SentenceTransformer

from stat_arb.memory.config import LightRAGConfig

logger = logging.getLogger(__name__)


def _run_sync(awaitable: Any) -> None:
    """Run an awaitable from synchronous entrypoints."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(awaitable)
        return

    msg = "Cannot synchronously initialize LightRAG while an event loop is already running"
    raise RuntimeError(msg)


async def local_noop_llm_model_func(prompt: str, **_kwargs: Any) -> str:
    """Local fallback LLM function for LightRAG storage-only operations.

    The installed LightRAG build accepts ``llm_model_func=None`` in its
    signature, but internally expects a callable during initialization.
    Returning an empty response keeps local inserts available without requiring
    network access or API credentials. Full generation can be wired later.
    """
    logger.debug("Using local no-op LightRAG LLM fallback for prompt length %s", len(prompt))
    return ""


async def ollama_llm_model_func(
    prompt: str,
    *,
    model: str,
    base_url: str,
    timeout: float,
    system_prompt: str | None = None,
    **_kwargs: Any,
) -> str:
    """Call a local Ollama model using the generate API."""
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
        },
    }
    if system_prompt:
        payload["system"] = system_prompt

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{base_url.rstrip('/')}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
    return str(data.get("response", ""))


def _join_chat_completion_content(data: dict[str, Any]) -> str:
    """Extract text from a non-streaming OpenAI-compatible response."""
    chunks: list[str] = []
    for choice in data.get("choices", []):
        message = choice.get("message") or {}
        content = message.get("content")
        if content:
            chunks.append(str(content))
            continue
        text = choice.get("text")
        if text:
            chunks.append(str(text))
    return "".join(chunks)


def _join_sse_chat_completion_content(text: str) -> str:
    """Extract text from an SSE OpenAI-compatible response."""
    chunks: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line.removeprefix("data:").strip()
        if not payload or payload == "[DONE]":
            continue
        data = json.loads(payload)
        for choice in data.get("choices", []):
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if content:
                chunks.append(str(content))
                continue
            message = choice.get("message") or {}
            message_content = message.get("content")
            if message_content:
                chunks.append(str(message_content))
    return "".join(chunks)


async def openai_compatible_llm_model_func(
    prompt: str,
    *,
    model: str,
    base_url: str,
    api_key: str,
    timeout: float,
    system_prompt: str | None = None,
    history_messages: list[dict[str, Any]] | None = None,
    **_kwargs: Any,
) -> str:
    """Call an OpenAI-compatible chat completions endpoint."""
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    for message in history_messages or []:
        role = str(message.get("role", "user"))
        content = str(message.get("content", ""))
        if content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": prompt})

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "text/event-stream" in content_type or response.text.lstrip().startswith("data:"):
        return _join_sse_chat_completion_content(response.text)
    return _join_chat_completion_content(response.json())


class LightRAGClient:
    """Client for LightRAG with embedded vector store.

    This client provides a simplified interface to LightRAG for storing
    and retrieving agent decisions, development knowledge, and research insights.

    Features:
    - Embedded vector store (FAISS or NanoVectorDB) - no Docker required
    - Local sentence-transformers embeddings
    - Minimal infrastructure setup
    - Knowledge graph for relationship modeling
    """

    def __init__(self, config: LightRAGConfig | None = None) -> None:
        """Initialize LightRAG client.

        Args:
            config: LightRAG configuration. If None, loads from environment.
        """
        self.config = config or LightRAGConfig()
        self.config.ensure_directories()

        self._embedding_model: SentenceTransformer | None = None
        self._rag: LightRAG | None = None

        logger.info(f"Initialized LightRAG client with {self.config.vector_store} backend")

    async def _llm_model_func(self, prompt: str, **kwargs: Any) -> str:
        """Dispatch LightRAG LLM calls to the configured provider."""
        if self.config.llm_provider == "ollama":
            return await ollama_llm_model_func(
                prompt,
                model=self.config.ollama_model,
                base_url=self.config.ollama_base_url,
                timeout=self.config.ollama_timeout,
                **kwargs,
            )
        if self.config.llm_provider == "openai_compatible":
            return await openai_compatible_llm_model_func(
                prompt,
                model=self.config.openai_compatible_model,
                base_url=self.config.openai_compatible_base_url,
                api_key=self.config.openai_compatible_api_key,
                timeout=self.config.openai_compatible_timeout,
                **kwargs,
            )
        return await local_noop_llm_model_func(prompt, **kwargs)

    @property
    def embedding_model(self) -> SentenceTransformer:
        """Lazy-load sentence-transformers embedding model."""
        if self._embedding_model is None:
            logger.info(f"Loading embedding model: {self.config.embedding_model}")
            self._embedding_model = SentenceTransformer(
                self.config.embedding_model,
                local_files_only=self.config.embedding_local_files_only,
            )
            logger.info(f"Embedding model loaded (dim={self.config.embedding_dim})")
        return self._embedding_model

    @property
    def rag(self) -> LightRAG:
        """Lazy-load LightRAG instance."""
        if self._rag is None:
            self._rag = self._initialize_lightrag()
        return self._rag

    def _initialize_lightrag(self) -> LightRAG:
        """Initialize LightRAG with embedded vector store.

        Returns:
            Configured LightRAG instance.
        """
        logger.info("Initializing LightRAG...")

        # Configure working directory
        working_dir = str(self.config.storage_path.absolute())

        # Create async embedding function
        async def embed_texts(texts: list[str]) -> np.ndarray:
            """Async wrapper for sentence-transformers embedding."""
            embeddings = self.embedding_model.encode(
                texts,
                batch_size=self.config.batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )
            return embeddings

        # Create EmbeddingFunc wrapper for sentence-transformers
        embedding_func = EmbeddingFunc(
            embedding_dim=self.config.embedding_dim,
            func=embed_texts,
            model_name=self.config.embedding_model,
        )

        # Initialize LightRAG with embedded backend
        # Note: LLM is optional for basic storage/retrieval operations
        rag = LightRAG(
            working_dir=working_dir,
            vector_storage=self.config.vector_storage_class,
            vector_db_storage_cls_kwargs=self.config.vector_storage_kwargs,
            embedding_func=embedding_func,
            llm_model_func=self._llm_model_func,
            embedding_batch_num=self.config.batch_size,
            embedding_func_max_async=self.config.max_workers,
            llm_model_max_async=self.config.max_workers,
            default_llm_timeout=int(self.config.llm_timeout),
            chunk_token_size=self.config.chunk_size,
            chunk_overlap_token_size=self.config.chunk_overlap,
        )
        initialize_result = rag.initialize_storages()
        if inspect.isawaitable(initialize_result):
            _run_sync(initialize_result)

        logger.info(
            f"LightRAG initialized at {working_dir} "
            f"(chunk_size={self.config.chunk_size}, "
            f"overlap={self.config.chunk_overlap})"
        )

        return rag

    async def _embed_func_async(self, texts: list[str]) -> np.ndarray:
        """Async embedding function for LightRAG using sentence-transformers.

        Args:
            texts: List of text strings to embed.

        Returns:
            Numpy array of embedding vectors.
        """
        embeddings = self.embedding_model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings

    def _embed_func(self, texts: list[str]) -> list[list[float]]:
        """Synchronous embedding helper for direct tests and non-async callers.

        LightRAG uses the async wrapper, but keeping the core encoding path
        accessible makes it easy to unit test without initializing LightRAG.
        """
        embeddings = self.embedding_model.encode(
            texts,
            batch_size=self.config.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return embeddings.astype(float).tolist()

    def insert(self, text: str, metadata: dict[str, Any] | None = None) -> None:
        """Insert text into LightRAG knowledge base.

        Args:
            text: Text content to store.
            metadata: Optional metadata to associate with the text.
        """
        try:
            # Prepend metadata as structured text if provided
            if metadata:
                metadata_str = json.dumps(metadata, indent=2)
                full_text = f"METADATA:\n{metadata_str}\n\nCONTENT:\n{text}"
            else:
                full_text = text

            self.rag.insert(full_text)
            logger.info(f"Inserted text into LightRAG ({len(text)} chars)")

        except Exception as e:
            logger.error(f"Failed to insert text into LightRAG: {e}")
            raise

    def query(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 5,
    ) -> str:
        """Query LightRAG knowledge base.

        Args:
            query: Query text.
            mode: Query mode - "naive", "local", "global", or "hybrid".
            top_k: Number of results to return.

        Returns:
            Query result as text.
        """
        try:
            result = self.rag.query(
                query,
                param=QueryParam(mode=mode, top_k=top_k),
            )
            logger.info(f"Query completed: '{query[:50]}...' (mode={mode})")
            return result

        except Exception as e:
            logger.error(f"Failed to query LightRAG: {e}")
            raise

    def store_hypothesis(
        self,
        hypothesis_id: str,
        asset_a: str,
        asset_b: str,
        rationale: str,
        source: str,
        similar_hypotheses: list[str] | None = None,
    ) -> None:
        """Store a hypothesis in LightRAG.

        Args:
            hypothesis_id: Unique hypothesis identifier.
            asset_a: First asset symbol.
            asset_b: Second asset symbol.
            rationale: Explanation for why this pair might be cointegrated.
            source: Source of hypothesis (e.g., "llm_generated", "rule_based").
            similar_hypotheses: List of similar hypothesis IDs.
        """
        metadata = {
            "type": "hypothesis",
            "hypothesis_id": hypothesis_id,
            "asset_a": asset_a,
            "asset_b": asset_b,
            "source": source,
            "similar_hypotheses": similar_hypotheses or [],
        }

        text = f"""
HYPOTHESIS: {asset_a} / {asset_b}

RATIONALE:
{rationale}

SOURCE: {source}

SIMILAR HYPOTHESES: {", ".join(similar_hypotheses or [])}
"""

        self.insert(text, metadata)
        logger.info(f"Stored hypothesis {hypothesis_id}: {asset_a}/{asset_b}")

    def store_test_summary(
        self,
        test_id: str,
        hypothesis_id: str,
        passed: bool,
        summary: str,
    ) -> None:
        """Store statistical test summary in LightRAG.

        Args:
            test_id: Unique test identifier.
            hypothesis_id: Associated hypothesis ID.
            passed: Whether the test passed.
            summary: Human-readable test summary.
        """
        metadata = {
            "type": "statistical_test",
            "test_id": test_id,
            "hypothesis_id": hypothesis_id,
            "passed": passed,
        }

        text = f"""
STATISTICAL TEST RESULT

Test ID: {test_id}
Hypothesis ID: {hypothesis_id}
Status: {"PASSED" if passed else "FAILED"}

SUMMARY:
{summary}
"""

        self.insert(text, metadata)
        logger.info(f"Stored test summary {test_id} (passed={passed})")

    def store_backtest_summary(
        self,
        backtest_id: str,
        hypothesis_id: str,
        conclusion: str,
        lessons_learned: str,
    ) -> None:
        """Store backtest summary in LightRAG.

        Args:
            backtest_id: Unique backtest identifier.
            hypothesis_id: Associated hypothesis ID.
            conclusion: High-level conclusion.
            lessons_learned: Lessons learned from the backtest.
        """
        metadata = {
            "type": "backtest",
            "backtest_id": backtest_id,
            "hypothesis_id": hypothesis_id,
        }

        text = f"""
BACKTEST SUMMARY

Backtest ID: {backtest_id}
Hypothesis ID: {hypothesis_id}

CONCLUSION:
{conclusion}

LESSONS LEARNED:
{lessons_learned}
"""

        self.insert(text, metadata)
        logger.info(f"Stored backtest summary {backtest_id}")

    def store_critic_review(
        self,
        review_id: str,
        backtest_id: str,
        objections: str,
        recommendation: str,
    ) -> None:
        """Store critic review in LightRAG.

        Args:
            review_id: Unique review identifier.
            backtest_id: Associated backtest ID.
            objections: Detected issues and objections.
            recommendation: Final recommendation.
        """
        metadata = {
            "type": "critic_review",
            "review_id": review_id,
            "backtest_id": backtest_id,
        }

        text = f"""
CRITIC REVIEW

Review ID: {review_id}
Backtest ID: {backtest_id}

OBJECTIONS:
{objections}

RECOMMENDATION:
{recommendation}
"""

        self.insert(text, metadata)
        logger.info(f"Stored critic review {review_id}")

    def store_architecture_decision(
        self,
        decision_id: str,
        title: str,
        decision: str,
        rationale: str,
        alternatives: str,
        risks: str,
    ) -> None:
        """Store architecture decision in LightRAG.

        Args:
            decision_id: Unique decision identifier.
            title: Decision title.
            decision: The decision made.
            rationale: Reasoning behind the decision.
            alternatives: Alternatives considered.
            risks: Known risks and trade-offs.
        """
        metadata = {
            "type": "architecture_decision",
            "decision_id": decision_id,
        }

        text = f"""
ARCHITECTURE DECISION: {title}

Decision ID: {decision_id}

DECISION:
{decision}

RATIONALE:
{rationale}

ALTERNATIVES CONSIDERED:
{alternatives}

RISKS AND TRADE-OFFS:
{risks}
"""

        self.insert(text, metadata)
        logger.info(f"Stored architecture decision {decision_id}: {title}")

    def search_similar_hypotheses(
        self,
        asset_a: str,
        asset_b: str,
        rationale: str,
        top_k: int = 5,
    ) -> str:
        """Search for similar hypotheses in LightRAG.

        Args:
            asset_a: First asset symbol.
            asset_b: Second asset symbol.
            rationale: Hypothesis rationale.
            top_k: Number of similar hypotheses to return.

        Returns:
            Similar hypotheses as text.
        """
        query = f"""
Find similar hypotheses to:
Asset pair: {asset_a} / {asset_b}
Rationale: {rationale}
"""
        return self.query(query, mode="hybrid", top_k=top_k)

    def get_experiment_history(self, hypothesis_id: str) -> str:
        """Get complete history for a hypothesis.

        Args:
            hypothesis_id: Hypothesis identifier.

        Returns:
            Complete experiment history as text.
        """
        query = f"Show all information related to hypothesis {hypothesis_id}"
        return self.query(query, mode="global", top_k=10)

    def health_check(self, check_embedding: bool = False) -> dict[str, Any]:
        """Check LightRAG health and configuration.

        Args:
            check_embedding: If True, load the embedding model and encode a
                small sample. Keep False for fast config/storage checks.

        Returns:
            Health check results.
        """
        try:
            # Check storage paths
            storage_exists = self.config.storage_path.exists()
            vector_store_exists = self.config.vector_store_path.exists()

            result: dict[str, Any] = {
                "status": "healthy" if storage_exists and vector_store_exists else "degraded",
                "embedding_model": self.config.embedding_model,
                "embedding_dim": self.config.embedding_dim,
                "embedding_checked": False,
                "vector_store": self.config.vector_store,
                "vector_storage_class": self.config.vector_storage_class,
                "storage_path": str(self.config.storage_path),
                "vector_store_path": str(self.config.vector_store_path),
                "storage_exists": storage_exists,
                "vector_store_exists": vector_store_exists,
                "chunk_size": self.config.chunk_size,
                "chunk_overlap": self.config.chunk_overlap,
            }

            if check_embedding:
                test_embedding = self.embedding_model.encode(["test"])
                embedding_ok = len(test_embedding) > 0
                result["embedding_checked"] = True
                result["status"] = (
                    "healthy"
                    if embedding_ok and storage_exists and vector_store_exists
                    else "degraded"
                )

            return result

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }
