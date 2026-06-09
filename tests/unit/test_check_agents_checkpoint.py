"""Static tests for the Task 14 all-agents checkpoint command."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_agents_checkpoint.ps1")


def test_check_agents_checkpoint_runs_agent_pipeline_guards_and_integration_smoke() -> None:
    """Task 14 checkpoint should prove agent boundaries work together."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_data_pipeline.ps1" in script
    assert "check_memory_agent_pipeline.ps1" in script
    assert "check_hypothesis_pipeline.ps1" in script
    assert "check_statistical_pipeline.ps1" in script
    assert "check_backtest_pipeline.ps1" in script
    assert "check_critic_pipeline.ps1" in script
    assert "check_report_pipeline.ps1" in script
    assert "check_coordinator_pipeline.ps1" in script
    assert "tests/integration/test_agents_checkpoint_integration.py" in script
    assert "--no-cov" in script
    assert "-p no:cacheprovider" in script


def test_check_agents_checkpoint_is_in_pre_commit_and_ci() -> None:
    """Task 14 checkpoint should be part of local and GitHub baselines."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "check_agents_checkpoint.ps1" in pre_commit
    assert "& $agentsCheckpointScript" in pre_commit
    assert "Check agents checkpoint" in ci
    assert "./scripts/check_agents_checkpoint.ps1" in ci
