"""Tests for the production print guard."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_no_production_prints.ps1")


def test_no_production_prints_script_scans_core_modules_and_excludes_scripts() -> None:
    """Production modules should not regain debug print calls."""
    assert SCRIPT_PATH.exists()

    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "src/stat_arb/agents" in script
    assert "src/stat_arb/backtest" in script
    assert "src/stat_arb/ingestion" in script
    assert "src/stat_arb/statistical" in script
    assert "src/stat_arb/storage" in script
    assert "src/stat_arb/scripts" not in script
    assert "ast.walk" in script
    assert "node.func.id == 'print'" in script


def test_pre_commit_check_includes_no_production_prints_guard() -> None:
    """The local pre-commit checklist should catch debug print regressions."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")

    assert "check_no_production_prints.ps1" in pre_commit
    assert "$noProductionPrintsCheckScript" in pre_commit
    assert "Invoke-RequiredCheck $noProductionPrintsCheckScript" in pre_commit
