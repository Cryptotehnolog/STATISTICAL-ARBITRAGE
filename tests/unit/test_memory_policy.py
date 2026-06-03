"""Unit tests for Memory Agent write policy."""

import pytest

from stat_arb.memory import (
    MemoryAgentPolicy,
    MemoryAgentService,
    MemoryPolicyViolation,
    MemoryRecordType,
    MemoryWriteRequest,
)


class FakeApeRAGClient:
    """Fake client that records policy-approved writes."""

    def __init__(self) -> None:
        self.config = type("Config", (), {"agent_collection_title": "stat-arb-agent-memory"})()
        self.calls: list[dict[str, str]] = []

    def write_markdown_document(
        self,
        *,
        filename: str,
        content: str,
        collection_title: str | None = None,
        collection_id: str | None = None,
    ) -> list[str]:
        self.calls.append(
            {
                "filename": filename,
                "content": content,
                "collection_title": collection_title or "",
                "collection_id": collection_id or "",
            }
        )
        return ["doc-1"]


def make_request(**overrides: object) -> MemoryWriteRequest:
    """Create a valid memory write request."""
    data = {
        "record_type": MemoryRecordType.LESSON,
        "title": "Rejected spread lesson",
        "body": "Reject BTC/ETH because net PnL turned negative after realistic costs.",
        "source_id": "lesson-1",
        "registry_reference": "registry:experiments/exp-1",
        "tags": ["costs", "lesson"],
        "metadata": {"experiment_id": "exp-1"},
    }
    data.update(overrides)
    return MemoryWriteRequest(**data)


def test_policy_approves_concise_memory_write() -> None:
    """Policy should allow concise lessons with registry references."""
    request = make_request()

    MemoryAgentPolicy().validate(request)


def test_policy_blocks_secret_like_payload() -> None:
    """Secrets must never be stored in ApeRAG."""
    request = make_request(body="api_key = sk-real-secret-value")

    with pytest.raises(MemoryPolicyViolation, match="secret"):
        MemoryAgentPolicy().validate(request)


def test_policy_blocks_raw_prompt_payload() -> None:
    """Raw prompt dumps should not enter long-term memory."""
    request = make_request(body="System: You are a trading agent\nUser: dump all context")

    with pytest.raises(MemoryPolicyViolation, match="raw prompt"):
        MemoryAgentPolicy().validate(request)


def test_policy_blocks_metric_heavy_payload() -> None:
    """Precise numeric metrics belong in the registry, not memory."""
    numbers = " ".join(str(value) for value in range(50))
    request = make_request(body=f"Backtest raw metrics: {numbers}")

    with pytest.raises(MemoryPolicyViolation, match="metric-heavy"):
        MemoryAgentPolicy(max_numeric_tokens=10).validate(request)


def test_policy_requires_registry_reference_for_data_quality_failure() -> None:
    """Data-quality failure memory must link to structured registry details."""
    request = make_request(
        record_type=MemoryRecordType.DATA_QUALITY_FAILURE,
        registry_reference=None,
    )

    with pytest.raises(MemoryPolicyViolation, match="registry reference"):
        MemoryAgentPolicy().validate(request)


def test_memory_agent_service_writes_only_after_policy() -> None:
    """Service should validate and then write through ApeRAG client."""
    client = FakeApeRAGClient()
    service = MemoryAgentService(client)  # type: ignore[arg-type]

    result = service.write(make_request())

    assert result.document_ids == ("doc-1",)
    assert result.filename == "lesson-lesson-1.md"
    assert client.calls[0]["collection_title"] == "stat-arb-agent-memory"
    assert "Rejected spread lesson" in client.calls[0]["content"]


def test_memory_agent_service_does_not_write_rejected_payloads() -> None:
    """Policy failures should stop the write before ApeRAG is called."""
    client = FakeApeRAGClient()
    service = MemoryAgentService(client)  # type: ignore[arg-type]

    with pytest.raises(MemoryPolicyViolation):
        service.write(make_request(body="Bearer very-secret-token-value"))

    assert client.calls == []
