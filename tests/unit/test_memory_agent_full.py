"""Unit tests for the full Memory Agent boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stat_arb.memory import (
    ApeRAGError,
    ApeRAGGraphSummary,
    ApeRAGSearchResult,
    MemoryAgentPolicy,
    MemoryAgentService,
    MemoryPolicyViolation,
    MemoryQueryRequest,
    MemoryQueryType,
    MemoryRecordType,
    MemoryWriteAheadQueue,
    MemoryWriteRequest,
)


class FakeMemoryBackend:
    """Fake backend that records Memory Agent calls without touching ApeRAG."""

    def __init__(self, *, fail_writes: bool = False) -> None:
        self.project_collection_title = "stat-arb-project-knowledge"
        self.agent_collection_title = "stat-arb-agent-memory"
        self.fail_writes = fail_writes
        self.writes: list[dict[str, str]] = []
        self.searches: list[dict[str, object]] = []
        self.relationship_queries: list[dict[str, object]] = []

    def write_markdown_document(
        self,
        *,
        filename: str,
        content: str,
        collection_title: str,
    ) -> list[str]:
        if self.fail_writes:
            raise ApeRAGError("backend unavailable")
        self.writes.append(
            {
                "filename": filename,
                "content": content,
                "collection_title": collection_title,
            }
        )
        return ["doc-1"]

    def search(
        self,
        query: str,
        *,
        collection_title: str,
        keywords: list[str] | None = None,
        top_k: int | None = None,
    ) -> list[ApeRAGSearchResult]:
        self.searches.append(
            {
                "query": query,
                "collection_title": collection_title,
                "keywords": keywords or [],
                "top_k": top_k,
            }
        )
        return [
            ApeRAGSearchResult(
                text="DEC-0001 says ApeRAG is the active memory backend.",
                score=0.91,
                source="decisions_memory_aperag.md",
            )
        ]

    def query_relationships(
        self,
        entity: str,
        *,
        collection_title: str,
        relationship: str | None = None,
        max_depth: int | None = None,
    ) -> list[ApeRAGSearchResult]:
        self.relationship_queries.append(
            {
                "entity": entity,
                "collection_title": collection_title,
                "relationship": relationship,
                "max_depth": max_depth,
            }
        )
        return [
            ApeRAGSearchResult(
                text="BTC/USDT hypothesis links to ETH/USDT retest evidence.",
                score=None,
                source="graph",
                metadata={"entity": entity, "relationship": relationship},
            )
        ]

    def get_graph_summary(self, *, collection_title: str) -> ApeRAGGraphSummary:
        return ApeRAGGraphSummary(labels=1, nodes=2, edges=1)


def make_request(**overrides: object) -> MemoryWriteRequest:
    """Create a valid memory write request."""
    data = {
        "record_type": MemoryRecordType.AGENT_DECISION,
        "title": "Critic quarantined hypothesis",
        "body": "Critic quarantined the spread because weak assumptions require a retest.",
        "source_id": "critic-review-1",
        "registry_reference": "registry:critic_reviews/review-1",
        "tags": ["critic", "decision"],
    }
    data.update(overrides)
    return MemoryWriteRequest(**data)


def test_memory_agent_writes_agent_decisions_to_operational_collection() -> None:
    """Agent decisions should go to operational memory through the backend boundary."""
    backend = FakeMemoryBackend()
    service = MemoryAgentService(backend)

    result = service.write(make_request())

    assert result.document_ids == ("doc-1",)
    assert result.queued is False
    assert backend.writes[0]["collection_title"] == "stat-arb-agent-memory"
    assert "Critic quarantined hypothesis" in backend.writes[0]["content"]


@pytest.mark.parametrize(
    "record_type",
    [
        MemoryRecordType.MARKET_KNOWLEDGE,
        MemoryRecordType.DEVELOPMENT_KNOWLEDGE,
        MemoryRecordType.MANUAL_NOTE,
    ],
)
def test_memory_agent_writes_project_knowledge_to_project_collection(
    record_type: MemoryRecordType,
) -> None:
    """Market/development/manual knowledge belongs in project memory."""
    backend = FakeMemoryBackend()
    service = MemoryAgentService(backend)

    service.write(
        make_request(
            record_type=record_type,
            title="Memory backend adapter decision",
            body="Agents depend on MemoryAgentService and MemoryBackend, not ApeRAG APIs.",
            source_id="DEC-9999",
            registry_reference="docs/knowledge/decisions_memory_aperag.md#DEC-9999",
        )
    )

    assert backend.writes[0]["collection_title"] == "stat-arb-project-knowledge"


def test_memory_agent_queries_project_topic_with_expected_markers() -> None:
    """Topic queries should search project memory and verify expected markers."""
    backend = FakeMemoryBackend()
    service = MemoryAgentService(backend)

    result = service.query(
        MemoryQueryRequest(
            query_type=MemoryQueryType.TOPIC,
            query="memory backend decision",
            expected_markers=["DEC-0001"],
            scope="project",
            top_k=3,
        )
    )

    assert result.ready is True
    assert result.missing_markers == ()
    assert backend.searches[0]["collection_title"] == "stat-arb-project-knowledge"
    assert backend.searches[0]["top_k"] == 3


def test_memory_agent_reports_missing_expected_markers() -> None:
    """Retrieval readiness should fail when required markers are absent."""
    backend = FakeMemoryBackend()
    service = MemoryAgentService(backend)

    result = service.query(
        MemoryQueryRequest(
            query_type=MemoryQueryType.TOPIC,
            query="memory backend decision",
            expected_markers=["DEC-MISSING"],
            scope="project",
        )
    )

    assert result.ready is False
    assert result.missing_markers == ("DEC-MISSING",)


def test_memory_agent_queries_relationships_through_graph_boundary() -> None:
    """Relationship queries should use the graph boundary instead of plain search."""
    backend = FakeMemoryBackend()
    service = MemoryAgentService(backend)

    result = service.query(
        MemoryQueryRequest(
            query_type=MemoryQueryType.RELATIONSHIP,
            query="BTC/USDT",
            relationship="similar_hypothesis",
            scope="agent",
            max_depth=2,
        )
    )

    assert result.graph_summary is not None
    assert result.results[0].source == "graph"
    assert backend.relationship_queries[0]["collection_title"] == "stat-arb-agent-memory"


def test_memory_policy_blocks_raw_logs_and_large_dataset_like_payloads() -> None:
    """Raw logs and large dataset dumps must not enter long-term memory."""
    policy = MemoryAgentPolicy()

    with pytest.raises(MemoryPolicyViolation, match="raw log"):
        policy.validate(make_request(body="2026-06-09 10:01:02 ERROR failed request\nTraceback line"))

    with pytest.raises(MemoryPolicyViolation, match="large dataset"):
        policy.validate(make_request(body="timestamp,open,high,low,close,volume\n" + "\n".join(["1,2,3,4,5,6"] * 10)))


def test_memory_agent_queues_write_when_backend_is_unavailable(tmp_path: Path) -> None:
    """Degraded mode should queue safe writes instead of silently dropping them."""
    queue_path = tmp_path / "memory-write-ahead.jsonl"
    backend = FakeMemoryBackend(fail_writes=True)
    service = MemoryAgentService(
        backend,
        write_ahead_queue=MemoryWriteAheadQueue(queue_path),
    )

    result = service.write(make_request())

    assert result.queued is True
    assert result.queue_path == queue_path
    queued = [json.loads(line) for line in queue_path.read_text(encoding="utf-8").splitlines()]
    assert queued[0]["request"]["title"] == "Critic quarantined hypothesis"
    assert queued[0]["collection_title"] == "stat-arb-agent-memory"
