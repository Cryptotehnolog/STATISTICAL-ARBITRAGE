"""Policy layer for safe Memory Agent writes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from stat_arb.memory.aperag_client import (
    ApeRAGError,
    ApeRAGGraphSummary,
    ApeRAGSearchResult,
    MemoryQueryRequest,
    MemoryQueryResult,
    MemoryQueryType,
    MemoryRecordType,
    MemoryWriteRequest,
)


class MemoryPolicyViolation(ValueError):
    """Raised when a memory write violates the Memory Agent policy."""


@dataclass(frozen=True)
class MemoryWriteResult:
    """Result of a policy-approved memory write."""

    document_ids: tuple[str, ...]
    filename: str
    queued: bool = False
    queue_path: Path | None = None


class MemoryBackend(Protocol):
    """Backend adapter boundary used by agent-facing Memory Agent code."""

    @property
    def project_collection_title(self) -> str:
        """Return the project knowledge collection title."""

    @property
    def agent_collection_title(self) -> str:
        """Return the operational agent memory collection title."""

    def write_markdown_document(
        self,
        *,
        filename: str,
        content: str,
        collection_title: str,
    ) -> list[str]:
        """Write one Markdown document to the selected backend collection."""

    def search(
        self,
        query: str,
        *,
        collection_title: str,
        keywords: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[ApeRAGSearchResult]:
        """Search the selected backend collection."""

    def query_relationships(
        self,
        entity: str,
        *,
        collection_title: str,
        relationship: str | None = None,
        max_depth: int | None = None,
    ) -> list[ApeRAGSearchResult]:
        """Query graph relationships from the selected backend collection."""

    def get_graph_summary(self, *, collection_title: str) -> ApeRAGGraphSummary:
        """Return graph readiness for the selected backend collection."""


class MemoryWriteAheadQueue:
    """Durable JSONL queue for policy-approved writes when backend writes fail."""

    def __init__(self, path: Path | str) -> None:
        """Create a write-ahead queue at a stable local path."""
        self.path = Path(path)

    def append(
        self,
        *,
        request: MemoryWriteRequest,
        collection_title: str,
        filename: str,
        error: Exception,
    ) -> Path:
        """Append one safe write request for later operator-controlled replay."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "queued_at": datetime.now(UTC).isoformat(),
            "collection_title": collection_title,
            "filename": filename,
            "error_type": type(error).__name__,
            "error": str(error),
            "request": request.model_dump(mode="json"),
        }
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            file.write("\n")
        return self.path


class MemoryReadThroughCache:
    """Small JSON cache for degraded memory reads when ApeRAG is temporarily unavailable."""

    def __init__(self, path: Path | str) -> None:
        """Create a read-through cache at a stable local path."""
        self.path = Path(path)

    def store(self, *, request: MemoryQueryRequest, result: MemoryQueryResult) -> None:
        """Store the latest successful result for a normalized query request."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load_all()
        data[self._key_for(request)] = result.model_dump(mode="json")
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8",
        )

    def load(self, *, request: MemoryQueryRequest, error: Exception) -> MemoryQueryResult | None:
        """Return a cached degraded result for a query request, if one exists."""
        payload = self._load_all().get(self._key_for(request))
        if payload is None:
            return None
        result = MemoryQueryResult.model_validate(payload)
        return result.model_copy(
            update={
                "degraded": True,
                "degraded_reason": f"{type(error).__name__}: {error}",
            }
        )

    def _load_all(self) -> dict[str, object]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ApeRAGError(f"Memory read cache must contain a JSON object: {self.path}")
        return data

    @staticmethod
    def _key_for(request: MemoryQueryRequest) -> str:
        return json.dumps(request.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)


class MemoryAgentPolicy:
    """Validate agent-facing memory writes before they reach ApeRAG."""

    secret_patterns = (
        re.compile(r"(?i)\b(api[_-]?key|client[_-]?secret|access[_-]?token)\b\s*[:=]\s*\S+"),
        re.compile(r"(?i)\bbearer\s+[a-z0-9._\-]{12,}"),
        re.compile(r"(?i)-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----"),
    )
    raw_prompt_patterns = (
        re.compile(r"(?im)^\s*(system|assistant|user)\s*:\s*"),
        re.compile(r"(?i)\b(raw prompt|full prompt|prompt dump|chat transcript)\b"),
    )
    raw_log_patterns = (
        re.compile(r"(?im)^\s*\d{4}-\d{2}-\d{2}[ t]\d{2}:\d{2}:\d{2}.*\b(error|warn|info|debug)\b"),
        re.compile(r"(?i)\b(traceback|stack trace|exception dump|raw log)\b"),
    )
    large_dataset_patterns = (
        re.compile(r"(?im)^timestamp,open,high,low,close,volume\s*$"),
        re.compile(r"(?i)\b(raw dataset|dataframe dump|parquet dump|csv dump)\b"),
    )

    def __init__(
        self,
        *,
        max_body_chars: int = 5000,
        max_numeric_tokens: int = 40,
    ) -> None:
        """Create policy with bounded content thresholds."""
        self.max_body_chars = max_body_chars
        self.max_numeric_tokens = max_numeric_tokens

    def validate(self, request: MemoryWriteRequest) -> None:
        """Validate a memory write request and raise on policy violations."""
        text = request.to_markdown()
        if len(request.body) > self.max_body_chars:
            raise MemoryPolicyViolation("Memory body is too large for long-term memory")
        if self._contains_secret(text):
            raise MemoryPolicyViolation("Memory write appears to contain a secret")
        if self._contains_raw_prompt(text):
            raise MemoryPolicyViolation("Memory write appears to contain raw prompt text")
        if self._contains_raw_log(text):
            raise MemoryPolicyViolation("Memory write appears to contain raw log text")
        if self._contains_large_dataset(request.body):
            raise MemoryPolicyViolation("Memory write appears to contain a large dataset")
        if self._numeric_token_count(request.body) > self.max_numeric_tokens:
            raise MemoryPolicyViolation("Memory write is too metric-heavy for ApeRAG")
        if request.record_type == MemoryRecordType.DATA_QUALITY_FAILURE and not request.registry_reference:
            raise MemoryPolicyViolation("Data quality failure memory requires a registry reference")

    def filename_for(self, request: MemoryWriteRequest) -> str:
        """Return a stable safe filename for a memory write."""
        safe_source = re.sub(r"[^a-zA-Z0-9._-]+", "-", request.source_id).strip("-")
        safe_type = str(request.record_type).replace("_", "-")
        return f"{safe_type}-{safe_source}.md"

    def _contains_secret(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self.secret_patterns)

    def _contains_raw_prompt(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self.raw_prompt_patterns)

    def _contains_raw_log(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self.raw_log_patterns)

    def _contains_large_dataset(self, text: str) -> bool:
        if any(pattern.search(text) for pattern in self.large_dataset_patterns):
            return True
        return len([line for line in text.splitlines() if line.count(",") >= 5]) >= 10

    @staticmethod
    def _numeric_token_count(text: str) -> int:
        return len(re.findall(r"(?<![A-Za-z])-?\d+(?:\.\d+)?(?![A-Za-z])", text))


class MemoryAgentService:
    """Policy-enforced write boundary for future agents."""

    def __init__(
        self,
        client: MemoryBackend,
        policy: MemoryAgentPolicy | None = None,
        *,
        collection_title: str | None = None,
        project_collection_title: str | None = None,
        write_ahead_queue: MemoryWriteAheadQueue | None = None,
        read_through_cache: MemoryReadThroughCache | None = None,
    ) -> None:
        """Create a Memory Agent service backed by ApeRAG."""
        self.client = client
        self.policy = policy or MemoryAgentPolicy()
        self.collection_title = collection_title or self._agent_collection_title(client)
        self.project_collection_title = project_collection_title or self._project_collection_title(client)
        self.write_ahead_queue = write_ahead_queue
        self.read_through_cache = read_through_cache

    def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        """Validate and write a memory record into the operational agent memory layer."""
        self.policy.validate(request)
        filename = self.policy.filename_for(request)
        collection_title = self._collection_title_for_write(request)
        try:
            document_ids = self.client.write_markdown_document(
                filename=filename,
                content=request.to_markdown(),
                collection_title=collection_title,
            )
            return MemoryWriteResult(document_ids=tuple(document_ids), filename=filename)
        except ApeRAGError as exc:
            if self.write_ahead_queue is None:
                raise
            queue_path = self.write_ahead_queue.append(
                request=request,
                collection_title=collection_title,
                filename=filename,
                error=exc,
            )
            return MemoryWriteResult(
                document_ids=(),
                filename=filename,
                queued=True,
                queue_path=queue_path,
            )

    def query(self, request: MemoryQueryRequest) -> MemoryQueryResult:
        """Query project or operational memory through the backend boundary."""
        try:
            result = self._query_backend(request)
        except ApeRAGError as exc:
            if self.read_through_cache is None:
                raise
            cached = self.read_through_cache.load(request=request, error=exc)
            if cached is None:
                raise
            return cached
        if self.read_through_cache is not None:
            self.read_through_cache.store(request=request, result=result)
        return result

    def _query_backend(self, request: MemoryQueryRequest) -> MemoryQueryResult:
        collection_title = self._collection_title_for_scope(request.scope)
        if request.query_type == MemoryQueryType.RELATIONSHIP:
            results = self.client.query_relationships(
                request.query,
                collection_title=collection_title,
                relationship=request.relationship,
                max_depth=request.max_depth,
            )
            graph_summary = self.client.get_graph_summary(collection_title=collection_title)
        else:
            keywords = request.keywords
            if request.query_type == MemoryQueryType.ENTITY and not keywords:
                keywords = [request.query]
            results = self.client.search(
                request.query,
                collection_title=collection_title,
                keywords=keywords,
                top_k=request.top_k,
            )
            graph_summary = None
        text = "\n".join(result.text for result in results)
        missing_markers = tuple(marker for marker in request.expected_markers if marker not in text)
        return MemoryQueryResult(
            results=tuple(results),
            missing_markers=missing_markers,
            graph_summary=graph_summary,
        )

    def _collection_title_for_write(self, request: MemoryWriteRequest) -> str:
        project_types = {
            MemoryRecordType.MARKET_KNOWLEDGE,
            MemoryRecordType.DEVELOPMENT_KNOWLEDGE,
            MemoryRecordType.MANUAL_NOTE,
            MemoryRecordType.DECISION,
        }
        if request.record_type in project_types:
            return self.project_collection_title
        return self.collection_title

    def _collection_title_for_scope(self, scope: str) -> str:
        if scope == "project":
            return self.project_collection_title
        return self.collection_title

    @staticmethod
    def _agent_collection_title(client: MemoryBackend) -> str:
        title = getattr(client, "agent_collection_title", None)
        if title:
            return str(title)
        config = getattr(client, "config", None)
        return str(getattr(config, "agent_collection_title", "stat-arb-agent-memory"))

    @staticmethod
    def _project_collection_title(client: MemoryBackend) -> str:
        title = getattr(client, "project_collection_title", None)
        if title:
            return str(title)
        config = getattr(client, "config", None)
        return str(getattr(config, "collection_title", "stat-arb-project-knowledge"))
