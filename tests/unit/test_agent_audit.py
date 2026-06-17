"""Tests for agent audit events."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from stat_arb.agents import AgentAuditEvent, AgentAuditJsonlWriter


def test_agent_audit_event_requires_operator_safe_fields() -> None:
    """Audit entries should be structured and require a non-empty reason."""
    event = AgentAuditEvent(
        event_id="evt-001",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        agent_name="critic_agent",
        action="review_experiment",
        reason="Review explicit critic policy evidence.",
        status="success",
        registry_refs=("experiment:exp-001",),
        memory_refs=("memory:doc-001",),
        metadata={"policy": "cost_realism"},
    )

    assert event.agent_name == "critic_agent"
    assert event.metadata["policy"] == "cost_realism"

    with pytest.raises(ValueError, match="reason is required"):
        AgentAuditEvent(
            event_id="evt-002",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            agent_name="critic_agent",
            action="review_experiment",
            reason=" ",
            status="success",
        )


def test_agent_audit_event_redacts_sensitive_metadata() -> None:
    """Audit metadata should not persist secrets, tokens, or raw payload blobs."""
    event = AgentAuditEvent(
        event_id="evt-003",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        agent_name="memory_agent",
        action="write_summary",
        reason="Persist policy-safe memory summary.",
        status="success",
        metadata={
            "api_key": "secret-value",
            "access_token": "token-value",
            "raw_payload": {"full": "payload"},
            "summary": "safe",
        },
    )

    sanitized = event.to_safe_dict()

    assert sanitized["metadata"]["api_key"] == "<redacted>"
    assert sanitized["metadata"]["access_token"] == "<redacted>"
    assert sanitized["metadata"]["raw_payload"] == "<redacted>"
    assert sanitized["metadata"]["summary"] == "safe"


def test_agent_audit_jsonl_writer_appends_safe_events(tmp_path: Path) -> None:
    """Audit writer should create append-only JSONL without leaking sensitive fields."""
    path = tmp_path / "agent_audit.jsonl"
    writer = AgentAuditJsonlWriter(path)
    event = AgentAuditEvent(
        event_id="evt-004",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        agent_name="coordinator_agent",
        action="approve",
        reason="Human reviewer approved the report package.",
        status="success",
        metadata={"client_secret": "hidden", "decision": "approved"},
    )

    writer.append(event)

    content = path.read_text(encoding="utf-8")
    assert "coordinator_agent" in content
    assert "hidden" not in content
    assert "<redacted>" in content
