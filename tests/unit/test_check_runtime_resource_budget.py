"""Static tests for manual runtime resource budget monitoring."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_runtime_resource_budget.ps1")


def test_runtime_resource_budget_check_requires_explicit_budgets() -> None:
    """Runtime budget monitoring should not hide RAM/disk thresholds."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "RamBudgetGb" in script
    assert "DiskBudgetGb" in script
    assert "WarnUsageRatio" in script
    assert "Mandatory = $true" in script
    assert "evaluate_resource_budget" in script
    assert "ResourceUsageSnapshot" in script


def test_runtime_resource_budget_check_is_not_in_pre_commit() -> None:
    """Local Docker/WSL resource state should remain outside ordinary pre-commit checks."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")

    assert "check_runtime_resource_budget.ps1" not in pre_commit
