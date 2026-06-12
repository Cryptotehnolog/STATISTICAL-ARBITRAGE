"""Static tests for the scripted statistical-testing workflow."""

from pathlib import Path

WORKFLOW_SCRIPT = Path("scripts/run_statistical_testing.ps1")
CHECK_SCRIPT = Path("scripts/check_statistical_testing_workflow.ps1")
PRE_COMMIT_SCRIPT = Path("scripts/pre_commit_check.ps1")


def test_statistical_testing_script_uses_experiment_stage_boundary() -> None:
    """Statistical testing should run through Coordinator-backed CLI stage commands."""
    script = WORKFLOW_SCRIPT.read_text(encoding="utf-8")

    assert "param(" in script
    assert "[Parameter(Mandatory = $true)]" in script
    assert "uv run stat-arb experiment run-stage" in script
    assert "uv run stat-arb experiment execute-stage" in script
    assert "--stage" in script
    assert "statistical_testing" in script
    assert "--task-type" in script
    assert "run_statistical_tests" in script
    assert "--agent-name" in script
    assert "statistical_testing_agent" in script
    assert "--payload-json" in script
    assert "--advance-lifecycle" in script
    assert "--max-running-tasks" in script
    assert "--max-running-tasks-per-agent" in script
    assert "ApeRAGMemoryClient" not in script
    assert "run_statistical_testing(" not in script


def test_statistical_testing_checkpoint_runs_workflow_contract() -> None:
    """Checkpoint should cover script contract and CLI stage execution behavior."""
    script = CHECK_SCRIPT.read_text(encoding="utf-8")

    assert "Проверка statistical-testing workflow" in script
    assert "test_statistical_testing_workflow.py" in script
    assert "test_experiment_execute_stage_runs_statistical_testing_and_completes_task" in script
    assert "$LASTEXITCODE -ne 0" in script


def test_pre_commit_runs_statistical_testing_workflow_checkpoint() -> None:
    """The statistical-testing workflow checkpoint should be part of local pre-commit."""
    script = PRE_COMMIT_SCRIPT.read_text(encoding="utf-8")

    assert "check_statistical_testing_workflow.ps1" in script
    assert "$statisticalTestingWorkflowCheckScript" in script
