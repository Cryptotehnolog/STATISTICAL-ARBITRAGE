"""ApeRAG client boundary for project memory operations."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from stat_arb.memory.config import ApeRAGConfig


class ApeRAGError(RuntimeError):
    """Raised when ApeRAG returns an error or an expected resource is missing."""


class MemoryRecordType(StrEnum):
    """Types of high-level records that may be written through the Memory Agent."""

    DECISION = "decision"
    LESSON = "lesson"
    MARKET_KNOWLEDGE = "market_knowledge"
    DEVELOPMENT_KNOWLEDGE = "development_knowledge"
    AGENT_DECISION = "agent_decision"
    HYPOTHESIS = "hypothesis"
    DATA_QUALITY_FAILURE = "data_quality_failure"
    CRITIC_REVIEW = "critic_review"
    REPORT_SUMMARY = "report_summary"
    MANUAL_NOTE = "manual_note"


class MemoryQueryType(StrEnum):
    """High-level query patterns supported by the Memory Agent."""

    TOPIC = "topic"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"


class MemoryModel(BaseModel):
    """Base model for memory boundary contracts."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, use_enum_values=True)


class MemoryWriteRequest(MemoryModel):
    """Contract for policy-controlled Memory Agent writes into ApeRAG.

    Runtime writes should go through the Memory Agent so agent code cannot push arbitrary
    raw logs, secrets, or metrics into the long-term memory collection.
    """

    record_type: MemoryRecordType
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    source_id: str = Field(min_length=1, max_length=200)
    registry_reference: str | None = Field(default=None, min_length=1, max_length=300)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        """Normalize tags for stable matching."""
        normalized = [tag.strip().lower() for tag in value if tag.strip()]
        return sorted(dict.fromkeys(normalized))

    def to_markdown(self) -> str:
        """Render a stable Markdown representation for ApeRAG document writes."""
        lines = [
            f"# {self.title}",
            "",
            f"Record type: {self.record_type}",
            f"Source ID: {self.source_id}",
        ]
        if self.registry_reference:
            lines.append(f"Registry reference: {self.registry_reference}")
        if self.tags:
            lines.append(f"Tags: {', '.join(self.tags)}")
        if self.metadata:
            lines.append("Metadata:")
            for key in sorted(self.metadata):
                lines.append(f"- {key}: {self.metadata[key]}")
        lines.extend(["", self.body.strip(), ""])
        return "\n".join(lines)


class MemoryQueryRequest(MemoryModel):
    """Contract for agent-facing memory queries."""

    query_type: MemoryQueryType
    query: str = Field(min_length=1, max_length=500)
    scope: Literal["project", "agent"] = "agent"
    keywords: list[str] = Field(default_factory=list)
    expected_markers: list[str] = Field(default_factory=list)
    relationship: str | None = Field(default=None, min_length=1, max_length=100)
    top_k: int | None = Field(default=None, ge=1, le=50)
    max_depth: int | None = Field(default=None, ge=1, le=5)

    @field_validator("keywords", "expected_markers")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        """Normalize query helper lists for stable matching."""
        normalized = [item.strip() for item in value if item.strip()]
        return list(dict.fromkeys(normalized))


class ApeRAGCollection(MemoryModel):
    """ApeRAG collection summary."""

    id: str
    title: str
    description: str | None = None
    enable_vector: bool = False
    enable_fulltext: bool = False
    enable_knowledge_graph: bool = False


class ApeRAGDocumentStatus(MemoryModel):
    """Index status for one ApeRAG document."""

    id: str
    name: str
    status: str
    vector_index_status: str | None = None
    fulltext_index_status: str | None = None
    graph_index_status: str | None = None

    @property
    def is_ready(self) -> bool:
        """Return True when the document is fully indexed for active memory reads."""
        return (
            self.status == "COMPLETE"
            and self.vector_index_status == "ACTIVE"
            and self.fulltext_index_status == "ACTIVE"
        )


class ApeRAGSearchResult(MemoryModel):
    """Single ApeRAG search result."""

    text: str
    score: float | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApeRAGGraphSummary(MemoryModel):
    """Human- and test-friendly graph status summary."""

    labels: int = Field(ge=0)
    nodes: int = Field(ge=0)
    edges: int = Field(ge=0)

    @property
    def is_non_empty(self) -> bool:
        """Return True when ApeRAG exposes a usable knowledge graph."""
        return self.labels > 0 and self.nodes > 0 and self.edges > 0


class MemoryQueryResult(MemoryModel):
    """Result of a Memory Agent query with retrieval-quality markers."""

    results: tuple[ApeRAGSearchResult, ...]
    missing_markers: tuple[str, ...] = ()
    graph_summary: ApeRAGGraphSummary | None = None

    @property
    def ready(self) -> bool:
        """Return True when query results contain all required markers."""
        return len(self.missing_markers) == 0


class ApeRAGMemoryClient:
    """Small HTTP client for the active ApeRAG memory backend."""

    def __init__(
        self,
        config: ApeRAGConfig | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        """Create an ApeRAG memory client."""
        self.config = config or ApeRAGConfig()
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=self.config.timeout_seconds)

    def close(self) -> None:
        """Close the underlying HTTP client when owned by this wrapper."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> ApeRAGMemoryClient:
        """Return self for context manager usage."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Close the client on context manager exit."""
        self.close()

    @property
    def headers(self) -> dict[str, str]:
        """Return ApeRAG request headers."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    @property
    def project_collection_title(self) -> str:
        """Return the project knowledge collection title."""
        return self.config.collection_title

    @property
    def agent_collection_title(self) -> str:
        """Return the operational agent memory collection title."""
        return self.config.agent_collection_title

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a JSON request to ApeRAG and wrap failures."""
        url = f"{self.config.normalized_api_base_url}{path}"
        try:
            response = self._client.request(method, url, headers=self.headers, json=json_body)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ApeRAGError(f"ApeRAG HTTP {exc.response.status_code}: {path}") from exc
        except httpx.HTTPError as exc:
            raise ApeRAGError(f"ApeRAG request failed: {path}") from exc
        if not isinstance(data, dict):
            raise ApeRAGError(f"ApeRAG returned non-object JSON: {path}")
        return data

    def _request_files(
        self,
        method: str,
        path: str,
        *,
        files: dict[str, tuple[str, bytes, str]],
    ) -> dict[str, Any]:
        """Send a multipart request to ApeRAG and wrap failures."""
        url = f"{self.config.normalized_api_base_url}{path}"
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        try:
            response = self._client.request(method, url, headers=headers, files=files)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            raise ApeRAGError(f"ApeRAG HTTP {exc.response.status_code}: {path}") from exc
        except httpx.HTTPError as exc:
            raise ApeRAGError(f"ApeRAG request failed: {path}") from exc
        if not isinstance(data, dict):
            raise ApeRAGError(f"ApeRAG returned non-object JSON: {path}")
        return data

    def health_check(self) -> dict[str, Any]:
        """Return ApeRAG API health payload."""
        return self._request("GET", "/api/v1/health")

    def ensure_collection(
        self,
        *,
        title: str,
        description: str,
        enable_knowledge_graph: bool = False,
    ) -> ApeRAGCollection:
        """Create a collection when missing and return its effective config."""
        try:
            return self.get_collection(title)
        except ApeRAGError:
            pass

        config = {
            "source": "system",
            "enable_vector": True,
            "enable_fulltext": True,
            "enable_knowledge_graph": enable_knowledge_graph,
            "enable_summary": False,
            "enable_vision": False,
            "language": "en-US",
            "embedding": {
                "model": self.config.embedding_model,
                "model_service_provider": self.config.embedding_provider,
                "custom_llm_provider": "openai",
                "timeout": 60,
            },
            "completion": {
                "model": self.config.completion_model,
                "model_service_provider": self.config.completion_provider,
                "custom_llm_provider": "openai",
                "temperature": 0.1,
                "max_tokens": 2048,
                "timeout": 120,
            },
        }
        created = self._request(
            "POST",
            "/api/v1/collections",
            json_body={
                "title": title,
                "description": description,
                "type": "document",
                "config": config,
            },
        )
        return ApeRAGCollection(
            id=str(created["id"]),
            title=str(created["title"]),
            description=created.get("description"),
            enable_vector=True,
            enable_fulltext=True,
            enable_knowledge_graph=enable_knowledge_graph,
        )

    def get_collection(self, title: str | None = None) -> ApeRAGCollection:
        """Find a collection by title and return its effective memory config."""
        collection_title = title or self.config.collection_title
        data = self._request("GET", "/api/v1/collections?page=1&page_size=100")
        for item in data.get("items", []):
            if item.get("title") != collection_title:
                continue
            detail = self._request("GET", f"/api/v1/collections/{item['id']}")
            config = detail.get("config") or {}
            return ApeRAGCollection(
                id=str(detail["id"]),
                title=str(detail["title"]),
                description=detail.get("description"),
                enable_vector=bool(config.get("enable_vector")),
                enable_fulltext=bool(config.get("enable_fulltext")),
                enable_knowledge_graph=bool(config.get("enable_knowledge_graph")),
            )
        raise ApeRAGError(f"ApeRAG collection not found: {collection_title}")

    def list_documents(self, collection_id: str | None = None) -> list[ApeRAGDocumentStatus]:
        """List documents and index statuses for a collection."""
        resolved_collection_id = collection_id or self.get_collection().id
        data = self._request(
            "GET",
            f"/api/v1/collections/{resolved_collection_id}/documents?page=1&page_size=100",
        )
        return [
            ApeRAGDocumentStatus(
                id=str(item["id"]),
                name=str(item["name"]),
                status=str(item["status"]),
                vector_index_status=item.get("vector_index_status"),
                fulltext_index_status=item.get("fulltext_index_status"),
                graph_index_status=item.get("graph_index_status"),
            )
            for item in data.get("items", [])
        ]

    def delete_document(self, *, collection_id: str, document_id: str) -> None:
        """Delete one ApeRAG document from a collection."""
        self._request("DELETE", f"/api/v1/collections/{collection_id}/documents/{document_id}")

    def search(
        self,
        query: str,
        *,
        collection_title: str | None = None,
        collection_id: str | None = None,
        keywords: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[ApeRAGSearchResult]:
        """Search active ApeRAG memory with vector and full-text retrieval."""
        resolved_collection_id = collection_id or self.get_collection(collection_title).id
        resolved_top_k = top_k or self.config.search_top_k
        payload: dict[str, Any] = {
            "query": query,
            "vector_search": {
                "topk": resolved_top_k,
                "similarity": self.config.search_similarity,
            },
            "fulltext_search": {
                "topk": resolved_top_k,
                "keywords": keywords or [],
            },
            "save_to_history": False,
            "rerank": False,
        }
        data = self._request(
            "POST",
            f"/api/v1/collections/{resolved_collection_id}/searches",
            json_body=payload,
        )
        return [self._parse_search_result(item) for item in data.get("items", [])]

    def get_graph_summary(
        self,
        *,
        collection_title: str | None = None,
        collection_id: str | None = None,
    ) -> ApeRAGGraphSummary:
        """Return label/node/edge counts from ApeRAG graph endpoints."""
        resolved_collection_id = collection_id or self.get_collection(collection_title).id
        labels = self._request("GET", f"/api/v1/collections/{resolved_collection_id}/graphs/labels")
        graph = self._request(
            "GET",
            f"/api/v1/collections/{resolved_collection_id}/graphs?max_nodes=1000&max_depth=3",
        )
        return ApeRAGGraphSummary(
            labels=len(labels.get("labels") or []),
            nodes=len(graph.get("nodes") or []),
            edges=len(graph.get("edges") or []),
        )

    def query_relationships(
        self,
        entity: str,
        *,
        collection_title: str | None = None,
        relationship: str | None = None,
        max_depth: int | None = None,
    ) -> list[ApeRAGSearchResult]:
        """Query ApeRAG graph relationships around an entity."""
        resolved_collection_id = self.get_collection(collection_title).id
        depth = max_depth or 2
        graph = self._request(
            "GET",
            f"/api/v1/collections/{resolved_collection_id}/graphs?max_nodes=1000&max_depth={depth}",
        )
        entity_lower = entity.lower()
        relationship_lower = relationship.lower() if relationship else None
        results: list[ApeRAGSearchResult] = []
        for edge in graph.get("edges") or []:
            edge_text = " ".join(str(edge.get(key, "")) for key in sorted(edge))
            if entity_lower not in edge_text.lower():
                continue
            if relationship_lower and relationship_lower not in edge_text.lower():
                continue
            results.append(
                ApeRAGSearchResult(
                    text=edge_text,
                    source="graph",
                    metadata={"edge": edge},
                )
            )
        if results:
            return results
        for node in graph.get("nodes") or []:
            node_text = " ".join(str(node.get(key, "")) for key in sorted(node))
            if entity_lower in node_text.lower():
                results.append(
                    ApeRAGSearchResult(
                        text=node_text,
                        source="graph",
                        metadata={"node": node},
                    )
                )
        return results

    def write_markdown_document(
        self,
        *,
        filename: str,
        content: str,
        collection_title: str | None = None,
        collection_id: str | None = None,
    ) -> list[str]:
        """Upload and confirm one Markdown document through ApeRAG.

        Agent code should not call this directly. Use the Memory Agent policy layer so
        writes are screened before they reach long-term memory.
        """
        resolved_collection_id = collection_id or self.get_collection(
            collection_title or self.config.agent_collection_title
        ).id
        upload = self._request_files(
            "POST",
            f"/api/v1/collections/{resolved_collection_id}/documents",
            files={"files": (filename, content.encode("utf-8"), "text/markdown")},
        )
        document_ids = [str(item["id"]) for item in upload.get("items", []) if item.get("id")]
        if not document_ids:
            raise ApeRAGError(f"ApeRAG did not return document IDs for {filename}")
        self._request(
            "POST",
            f"/api/v1/collections/{resolved_collection_id}/documents/confirm",
            json_body={"document_ids": document_ids},
        )
        return document_ids

    @staticmethod
    def _parse_search_result(item: dict[str, Any]) -> ApeRAGSearchResult:
        """Normalize ApeRAG search response shapes into a stable result."""
        text = (
            item.get("text")
            or item.get("content")
            or item.get("chunk_text")
            or item.get("document_text")
            or ""
        )
        source = item.get("source") or item.get("document_name") or item.get("filename")
        score_value = item.get("score") or item.get("similarity") or item.get("rank_score")
        score = float(score_value) if score_value is not None else None
        metadata = {
            key: value
            for key, value in item.items()
            if key
            not in {
                "text",
                "content",
                "chunk_text",
                "document_text",
                "source",
                "document_name",
                "filename",
                "score",
                "similarity",
                "rank_score",
            }
        }
        return ApeRAGSearchResult(text=str(text), score=score, source=source, metadata=metadata)
