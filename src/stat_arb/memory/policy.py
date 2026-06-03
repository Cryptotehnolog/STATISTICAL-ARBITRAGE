"""Policy layer for safe Memory Agent writes."""

from __future__ import annotations

import re
from dataclasses import dataclass

from stat_arb.memory.aperag_client import (
    ApeRAGMemoryClient,
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

    @staticmethod
    def _numeric_token_count(text: str) -> int:
        return len(re.findall(r"(?<![A-Za-z])-?\d+(?:\.\d+)?(?![A-Za-z])", text))


class MemoryAgentService:
    """Policy-enforced write boundary for future agents."""

    def __init__(
        self,
        client: ApeRAGMemoryClient,
        policy: MemoryAgentPolicy | None = None,
        *,
        collection_title: str | None = None,
    ) -> None:
        """Create a Memory Agent service backed by ApeRAG."""
        self.client = client
        self.policy = policy or MemoryAgentPolicy()
        self.collection_title = collection_title or client.config.agent_collection_title

    def write(self, request: MemoryWriteRequest) -> MemoryWriteResult:
        """Validate and write a memory record into the operational agent memory layer."""
        self.policy.validate(request)
        filename = self.policy.filename_for(request)
        document_ids = self.client.write_markdown_document(
            filename=filename,
            content=request.to_markdown(),
            collection_title=self.collection_title,
        )
        return MemoryWriteResult(document_ids=tuple(document_ids), filename=filename)
