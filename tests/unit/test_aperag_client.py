"""Unit tests for the ApeRAG memory client boundary."""

import json

import httpx
import pytest

from stat_arb.memory import (
    ApeRAGConfig,
    ApeRAGError,
    ApeRAGMemoryClient,
    MemoryRecordType,
    MemoryWriteRequest,
)


def make_client(handler: httpx.MockTransport) -> ApeRAGMemoryClient:
    """Create a test client with fake ApeRAG transport."""
    config = ApeRAGConfig(
        api_base_url="http://aperag.test",
        api_key="test-token",
        collection_title="stat-arb-project-knowledge",
        _env_file=None,
    )
    return ApeRAGMemoryClient(config, http_client=httpx.Client(transport=handler))


def test_health_check_uses_api_health_endpoint() -> None:
    """Client should expose ApeRAG health without touching Docker."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/health"
        assert request.headers["Authorization"] == "Bearer test-token"
        return httpx.Response(200, json={"status": "healthy", "service": "aperag-api"})

    client = make_client(httpx.MockTransport(handler))

    assert client.health_check()["status"] == "healthy"


def test_get_collection_reads_detail_config() -> None:
    """Collection lookup should return effective vector/fulltext/graph flags."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/collections":
            return httpx.Response(
                200,
                json={"items": [{"id": "col-1", "title": "stat-arb-project-knowledge"}]},
            )
        if request.url.path == "/api/v1/collections/col-1":
            return httpx.Response(
                200,
                json={
                    "id": "col-1",
                    "title": "stat-arb-project-knowledge",
                    "description": "Project memory",
                    "config": {
                        "enable_vector": True,
                        "enable_fulltext": True,
                        "enable_knowledge_graph": True,
                    },
                },
            )
        return httpx.Response(404)

    client = make_client(httpx.MockTransport(handler))

    collection = client.get_collection()

    assert collection.id == "col-1"
    assert collection.enable_vector is True
    assert collection.enable_fulltext is True
    assert collection.enable_knowledge_graph is True


def test_list_documents_normalizes_readiness() -> None:
    """Document status should expose active-memory readiness."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/collections":
            return httpx.Response(200, json={"items": [{"id": "col-1", "title": "stat-arb-project-knowledge"}]})
        if request.url.path == "/api/v1/collections/col-1":
            return httpx.Response(200, json={"id": "col-1", "title": "stat-arb-project-knowledge", "config": {}})
        if request.url.path == "/api/v1/collections/col-1/documents":
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "doc-1",
                            "name": "agent_memory_contracts.md",
                            "status": "COMPLETE",
                            "vector_index_status": "ACTIVE",
                            "fulltext_index_status": "ACTIVE",
                            "graph_index_status": "ACTIVE",
                        }
                    ]
                },
            )
        return httpx.Response(404)

    client = make_client(httpx.MockTransport(handler))

    docs = client.list_documents()

    assert docs[0].name == "agent_memory_contracts.md"
    assert docs[0].is_ready is True


def test_search_sends_bounded_vector_and_fulltext_payload() -> None:
    """Search should use bounded vector/full-text retrieval and avoid history writes."""
    seen_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_payload
        if request.url.path == "/api/v1/collections":
            return httpx.Response(200, json={"items": [{"id": "col-1", "title": "stat-arb-project-knowledge"}]})
        if request.url.path == "/api/v1/collections/col-1":
            return httpx.Response(200, json={"id": "col-1", "title": "stat-arb-project-knowledge", "config": {}})
        if request.url.path == "/api/v1/collections/col-1/searches":
            seen_payload = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "text": "ApeRAG is the active memory backend.",
                            "score": 0.88,
                            "document_name": "decisions_memory_lightrag.md",
                        }
                    ]
                },
            )
        return httpx.Response(404)

    client = make_client(httpx.MockTransport(handler))

    results = client.search("memory backend decisions", keywords=["ApeRAG"], top_k=3)

    assert seen_payload["vector_search"]["topk"] == 3
    assert seen_payload["fulltext_search"]["keywords"] == ["ApeRAG"]
    assert seen_payload["save_to_history"] is False
    assert results[0].text.startswith("ApeRAG")
    assert results[0].source == "decisions_memory_lightrag.md"


def test_get_graph_summary_counts_labels_nodes_and_edges() -> None:
    """Graph summary should report non-empty ApeRAG graph counts."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/collections":
            return httpx.Response(200, json={"items": [{"id": "col-1", "title": "stat-arb-project-knowledge"}]})
        if request.url.path == "/api/v1/collections/col-1":
            return httpx.Response(200, json={"id": "col-1", "title": "stat-arb-project-knowledge", "config": {}})
        if request.url.path == "/api/v1/collections/col-1/graphs/labels":
            return httpx.Response(200, json={"labels": ["agent", "decision"]})
        if request.url.path == "/api/v1/collections/col-1/graphs":
            return httpx.Response(200, json={"nodes": [{"id": "a"}], "edges": [{"id": "e"}]})
        return httpx.Response(404)

    client = make_client(httpx.MockTransport(handler))

    summary = client.get_graph_summary()

    assert summary.labels == 2
    assert summary.nodes == 1
    assert summary.edges == 1
    assert summary.is_non_empty is True


def test_http_errors_are_wrapped_without_api_key() -> None:
    """Client errors should not leak the bearer token."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "nope"})

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(ApeRAGError) as exc_info:
        client.health_check()

    message = str(exc_info.value)
    assert "HTTP 401" in message
    assert "test-token" not in message


def test_memory_write_request_renders_stable_markdown() -> None:
    """Future writes should pass through a typed memory-safe contract."""
    request = MemoryWriteRequest(
        record_type=MemoryRecordType.DATA_QUALITY_FAILURE,
        title="BTC/USDT data rejected",
        body="Missing bars exceeded the accepted threshold.",
        source_id="dq-report-1",
        registry_reference="registry:data_quality_reports/dq-report-1",
        tags=[" Data ", "data", "Quality"],
        metadata={"dataset_id": "dataset-1"},
    )

    markdown = request.to_markdown()

    assert "Record type: data_quality_failure" in markdown
    assert "Tags: data, quality" in markdown
    assert "registry:data_quality_reports/dq-report-1" in markdown
