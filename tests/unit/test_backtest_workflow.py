"""Static tests for the scripted backtest workflow."""

from pathlib import Path

WORKFLOW_SCRIPT = Path("scripts/run_backtest.ps1")
CHECK_SCRIPT = Path("scripts/check_backtest_workflow.ps1")
PRE_COMMIT_SCRIPT = Path("scripts/pre_commit_check.ps1")


def test_backtest_script_uses_experiment_stage_boundary() -> None:
    """Backtest workflow should run through Coordinator-backed CLI stage commands."""
    script = WORKFLOW_SCRIPT.read_text(encoding="utf-8")

    assert "param(" in script
    assert "[Parameter(Mandatory = $true)]" in script
    assert "uv run stat-arb experiment run-stage" in script
    assert "uv run stat-arb experiment execute-stage" in script
    assert "--stage" in script
    assert "backtesting" in script
    assert "--task-type" in script
    assert "run_backtest" in script
    assert "--agent-name" in script
    assert "backtest_agent" in script
    assert "--payload-json" in script
    assert "--advance-lifecycle" in script
    assert "--max-running-tasks" in script
    assert "--max-running-tasks-per-agent" in script
    assert "ApeRAGMemoryClient" not in script
    assert "run_backtest_agent_persistence(" not in script
    assert "run_report_agent(" not in script


def test_backtest_checkpoint_runs_workflow_contract() -> None:
    """Checkpoint should cover script contract and CLI backtest execution behavior."""
    script = CHECK_SCRIPT.read_text(encoding="utf-8")

    assert "Проверка backtest workflow" in script
    assert "test_backtest_workflow.py" in script
    assert "test_experiment_execute_stage_runs_backtesting_and_completes_task" in script
    assert "$LASTEXITCODE -ne 0" in script


def test_pre_commit_runs_backtest_workflow_checkpoint() -> None:
    """The backtest workflow checkpoint should be part of local pre-commit."""
    script = PRE_COMMIT_SCRIPT.read_text(encoding="utf-8")

    assert "check_backtest_workflow.ps1" in script
    assert "$backtestWorkflowCheckScript" in script
