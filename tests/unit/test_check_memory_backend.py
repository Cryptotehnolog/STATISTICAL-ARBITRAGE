"""Unit tests for the active memory backend guard script."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_memory_backend.ps1")


def test_check_memory_backend_targets_aperag_only() -> None:
    """Guard should check the active ApeRAG backend without old memory calls."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '[ValidateSet("aperag")]' in script
    assert "check_aperag_memory_fresh.ps1" in script
    assert "check_lightrag" not in script.lower()
    assert "LightRAG" not in script


def test_check_memory_backend_supports_graph_flags() -> None:
    """Guard should support optional graph checks for slower readiness runs."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[switch]$IncludeGraphSmoke" in script
    assert "[switch]$RequireGraph" in script
    assert "-RequireCuratedGraph:$RequireGraph" in script
