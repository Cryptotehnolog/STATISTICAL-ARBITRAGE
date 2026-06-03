"""Unit tests for ApeRAG operational agent memory smoke script."""

from pathlib import Path

SCRIPT_PATH = Path("src/stat_arb/scripts/smoke_aperag_agent_memory.py")
WRAPPER_PATH = Path("scripts/check_aperag_agent_memory.ps1")


def test_smoke_script_uses_memory_agent_service() -> None:
    """Smoke writes must go through MemoryAgentService, not direct client writes."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "MemoryAgentService" in script
    assert "MemoryWriteRequest" in script
    assert "stat-arb-agent-memory" in script
    assert "write_markdown_document" not in script


def test_smoke_script_cleans_stable_smoke_document() -> None:
    """Smoke should not create unlimited duplicate operational memory docs."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "lesson-stat-arb-agent-memory-smoke.md" in script
    assert "delete_document" in script
    assert "wait_for_document_ready" in script


def test_agent_memory_wrapper_configures_aperag_and_runs_python_smoke() -> None:
    """PowerShell wrapper should configure ApeRAG then call the Python smoke."""
    script = WRAPPER_PATH.read_text(encoding="utf-8")

    assert "configure_aperag.ps1" in script
    assert "stat_arb.scripts.smoke_aperag_agent_memory" in script
    assert "stat-arb-agent-memory" in script
    assert "Проверка ApeRAG operational agent memory" in script
