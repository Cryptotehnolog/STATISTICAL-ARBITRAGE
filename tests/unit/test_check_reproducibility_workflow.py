"""Static tests for the Task 18.3 reproducibility workflow checkpoint."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_reproducibility_workflow.ps1")


def test_reproducibility_workflow_check_runs_twice_and_compares_snapshots() -> None:
    """Reproducibility checkpoint should run the deterministic two-run integration test."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "tests/integration/test_reproducibility_workflow.py" in script
    assert "--no-cov" in script
    assert "-p no:cacheprovider" in script
    assert "twice" in script.lower() or "дважды" in script.lower()


def test_reproducibility_workflow_check_is_in_pre_commit_and_ci() -> None:
    """Task 18.3 should be guarded locally and on GitHub Actions."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    tasks = Path(".kiro/specs/quant-research-architecture/tasks.md").read_text(encoding="utf-8")

    assert "check_reproducibility_workflow.ps1" in pre_commit
    assert "Invoke-RequiredCheck $reproducibilityWorkflowCheckScript" in pre_commit
    assert "Check reproducibility workflow" in ci
    assert "./scripts/check_reproducibility_workflow.ps1" in ci
    assert "- [x] 18.3 Create GitHub Actions workflow for reproducibility checks" in tasks
