"""Static tests for ApeRAG memory freshness checks."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_aperag_memory_fresh.ps1")


def test_check_aperag_memory_fresh_waits_for_async_indexes() -> None:
    """Freshness check should tolerate temporary PENDING/CREATING indexes after seed."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "IndexWaitTimeoutSeconds" in script
    assert "IndexPollSeconds" in script
    assert "while ($true)" in script
    assert "check_aperag_knowledge.ps1" in script
    assert "Start-Sleep -Seconds $IndexPollSeconds" in script
    assert "ApeRAG indexes еще строятся" in script


def test_check_aperag_memory_fresh_starts_embedding_server_before_health_check() -> None:
    """Freshness checks should not fail just because the local embedding server is stopped."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "start_aperag_embedding_server.ps1" in script
    assert "Перед проверкой поднимаем local embedding endpoint" in script
    assert "-HealthWaitSeconds" in script
