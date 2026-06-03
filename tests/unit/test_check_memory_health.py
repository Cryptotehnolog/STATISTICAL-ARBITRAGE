"""Static tests for memory health readiness script."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_memory_health.ps1")


def test_check_memory_health_composes_project_and_agent_memory_checks() -> None:
    """Readiness check should combine curated project memory and agent memory smoke."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_memory_backend.ps1" in script
    assert "-RequireGraph" in script
    assert "check_aperag_agent_memory.ps1" in script
    assert "stat-arb-agent-memory" in script
    assert "Memory health OK." in script


def test_check_memory_health_allows_expensive_parts_to_be_skipped() -> None:
    """Operator script should allow targeted checks during troubleshooting."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "$SkipCuratedGraph" in script
    assert "$SkipAgentMemory" in script
    assert "$IncludeGraphSmoke" in script
