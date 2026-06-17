"""Structured audit events for agent-facing actions."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

_SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "secret",
    "token",
    "password",
    "credential",
    "raw_payload",
    "raw_log",
)


class AgentAuditEvent(BaseModel):
    """Operator-safe record of one agent action or boundary decision."""

    event_id: str = Field(min_length=1, max_length=120)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    agent_name: str = Field(min_length=1, max_length=120)
    action: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=500)
    status: str = Field(min_length=1, max_length=80)
    registry_refs: tuple[str, ...] = ()
    memory_refs: tuple[str, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_id", "agent_name", "action", "reason", "status")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("reason is required" if value == "" or value.isspace() else "value is required")
        return stripped

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation with sensitive metadata redacted."""
        data = self.model_dump(mode="json")
        data["metadata"] = _sanitize_metadata(self.metadata)
        return data


class AgentAuditJsonlWriter:
    """Append-only JSONL writer for local agent audit events."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)

    def append(self, event: AgentAuditEvent) -> Path:
        """Append one sanitized event and return the audit file path."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event.to_safe_dict(), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        return self.path


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized = key.lower()
        if any(fragment in normalized for fragment in _SENSITIVE_KEY_FRAGMENTS):
            sanitized[key] = "<redacted>"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_metadata(value)
        else:
            sanitized[key] = value
    return sanitized
