"""Tests for the Critic Agent checkpoint script."""

from pathlib import Path


def test_check_critic_pipeline_runs_critic_tests() -> None:
    """Critic checkpoint command should run the Critic Agent unit baseline."""
    script = Path("scripts/check_critic_pipeline.ps1").read_text(encoding="utf-8")

    assert "test_critic_agent.py" in script
    assert "test_check_critic_pipeline.py" in script
    assert "--no-cov" in script


def test_check_critic_pipeline_is_in_pre_commit_and_ci() -> None:
    """Critic checkpoint should run in the local and CI baselines."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "check_critic_pipeline.ps1" in pre_commit
    assert "& $criticPipelineCheckScript" in pre_commit
    assert "Check Critic Agent pipeline" in ci
    assert "./scripts/check_critic_pipeline.ps1" in ci
