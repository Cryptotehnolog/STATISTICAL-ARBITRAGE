"""Static tests for legacy memory backend import guard."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_no_legacy_memory_backend_imports.ps1")


def test_guard_blocks_old_backend_imports_in_agent_facing_code() -> None:
    """Guard should block old memory client imports from agents and memory modules."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '"src/stat_arb/agents"' in script
    assert '"src/stat_arb/memory"' in script
    assert "LightRAGClient" in script
    assert "LightRAGConfig" in script
    assert "stat_arb\\.memory\\.lightrag_client" in script
    assert "MemoryAgentService" in script
    assert "Проверка отсутствия legacy memory backend imports прошла." in script
