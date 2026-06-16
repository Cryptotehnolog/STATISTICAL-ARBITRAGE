"""Static guard for the rolling stability diagnostics checkpoint script."""

from pathlib import Path


def test_stability_diagnostics_checkpoint_script_covers_core_agent_and_critic() -> None:
    """The 24.2 guard should exercise statistical, agent, and critic stability layers."""
    script = Path("scripts/check_stability_diagnostics_pipeline.ps1")
    assert script.exists()

    text = script.read_text(encoding="utf-8")
    assert "tests/unit/test_stability_diagnostics.py" in text
    assert "tests/unit/test_statistical_testing_agent.py" in text
    assert "test_critic_weak_assumption_detection_flags_stability_diagnostics" in text
