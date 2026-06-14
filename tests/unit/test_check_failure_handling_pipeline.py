"""Static tests for the failure handling checkpoint command."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_failure_handling_pipeline.ps1")


def test_check_failure_handling_pipeline_runs_task_17_checkpoint() -> None:
    """Failure handling checkpoint should cover Task 17 unit tests and source guards."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "src\\stat_arb\\agents\\failure_handling.py" in script
    assert "tests/unit/test_failure_handling.py" in script
    assert "--no-cov" in script
    assert "-p no:cacheprovider" in script
    assert "ApeRAGMemoryClient" in script
    assert "safe_mode_components" in script


def test_check_failure_handling_pipeline_is_in_pre_commit_and_ci() -> None:
    """Failure handling checkpoint should stay in local and CI baselines."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "check_failure_handling_pipeline.ps1" in pre_commit
    assert "Invoke-RequiredCheck $failureHandlingPipelineCheckScript" in pre_commit
    assert "Check failure handling pipeline" in ci
    assert "./scripts/check_failure_handling_pipeline.ps1" in ci
