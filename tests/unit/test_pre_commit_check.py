"""Unit tests for local pre-commit checklist composition."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/pre_commit_check.ps1")


def test_pre_commit_check_includes_memory_contract_guard() -> None:
    """Fast pre-commit should prevent direct agent memory writes."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_memory_contracts.ps1" in script
    assert "$memoryContractsCheckScript" in script
    assert "& $memoryContractsCheckScript" in script
