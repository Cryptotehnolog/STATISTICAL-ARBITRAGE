"""Unit tests for the residual diagnostics checkpoint script."""

from pathlib import Path


def test_residual_diagnostics_pipeline_script_runs_relevant_boundaries() -> None:
    """Task 24.1 should have a dedicated checkpoint for statistical and Critic boundaries."""
    script = Path("scripts/check_residual_diagnostics_pipeline.ps1")

    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "test_residual_diagnostics.py" in text
    assert "test_statistical_testing_agent.py" in text
    assert "test_critic_agent.py::test_critic_weak_assumption_detection_flags_residual_diagnostics" in text


def test_pre_commit_includes_residual_diagnostics_pipeline_guard() -> None:
    """Residual diagnostics should stay guarded after Task 24.1 is closed."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")

    assert "check_residual_diagnostics_pipeline.ps1" in pre_commit
