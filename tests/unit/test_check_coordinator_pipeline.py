"""Static tests for the Coordinator Agent checkpoint command."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_coordinator_pipeline.ps1")


def test_check_coordinator_pipeline_runs_full_task_13_checkpoint() -> None:
    """Coordinator checkpoint should cover unit, integration, and boundary guards."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_coordinator_agent_boundaries.ps1" in script
    assert "tests/unit/test_coordinator_agent.py" in script
    assert "tests/unit/test_check_coordinator_pipeline.py" in script
    assert "tests/integration/test_coordinator_agent_integration.py" in script
    assert "--no-cov" in script
    assert "-p no:cacheprovider" in script


def test_check_coordinator_pipeline_is_in_pre_commit_and_ci() -> None:
    """Coordinator checkpoint should stay in both local and CI baselines."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "check_coordinator_pipeline.ps1" in pre_commit
    assert "Invoke-RequiredCheck $coordinatorPipelineCheckScript" in pre_commit
    assert "Check Coordinator Agent pipeline" in ci
    assert "./scripts/check_coordinator_pipeline.ps1" in ci
