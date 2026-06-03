"""Unit tests for memory contract guard script."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_memory_contracts.ps1")


def test_check_memory_contracts_enforces_policy_layer() -> None:
    """Guard should require agent writes to go through policy service."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "src\\stat_arb\\memory\\policy.py" in script
    assert "MemoryAgentService" in script
    assert "ApeRAGMemoryClient" in script
    assert "write_markdown_document" in script


def test_check_memory_contracts_has_russian_operator_output() -> None:
    """Human-facing guard output should be Russian."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "Проверка memory contracts" in script
    assert "должны писать в память через MemoryAgentService" in script
