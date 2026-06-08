"""Local integration tests for the Memory Agent policy/write boundary."""

from stat_arb.memory import MemoryRecordType, MemoryWriteRequest
from stat_arb.memory.config import ApeRAGConfig
from stat_arb.memory.policy import MemoryAgentService


class FakeApeRAGClient:
    """Small local fake that verifies the service calls the real client-shaped boundary."""

    def __init__(self) -> None:
        self.config = ApeRAGConfig()
        self.calls: list[tuple[str, str, str]] = []

    def write_markdown_document(
        self,
        *,
        filename: str,
        content: str,
        collection_title: str,
    ) -> list[str]:
        self.calls.append((filename, content, collection_title))
        return ["doc-local-integration"]


def test_memory_agent_service_validates_and_writes_to_agent_collection() -> None:
    """Memory writes should pass policy and land in the operational collection."""
    client = FakeApeRAGClient()
    service = MemoryAgentService(client)

    result = service.write(
        MemoryWriteRequest(
            record_type=MemoryRecordType.LESSON,
            title="Integration smoke",
            body="Agent memory writes use policy before client persistence.",
            source_id="integration-smoke",
            registry_reference="registry:integration/smoke",
            tags=["integration", "memory"],
            metadata={"scope": "local"},
        )
    )

    assert result.document_ids == ("doc-local-integration",)
    assert result.filename == "lesson-integration-smoke.md"
    assert len(client.calls) == 1
    filename, content, collection_title = client.calls[0]
    assert filename == result.filename
    assert "Integration smoke" in content
    assert collection_title == "stat-arb-agent-memory"
