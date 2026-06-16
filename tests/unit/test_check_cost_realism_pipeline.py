"""Tests for the capacity/cost realism checkpoint script."""

from pathlib import Path


def test_cost_realism_pipeline_script_covers_backtest_and_critic_boundaries() -> None:
    """The guard should cover scenario math and Critic promotion evidence."""
    script = Path("scripts/check_cost_realism_pipeline.ps1")

    assert script.exists()
    content = script.read_text(encoding="utf-8")

    assert "tests/unit/test_backtest_realism.py" in content
    assert "tests/unit/test_backtest_sensitivity.py" in content
    assert (
        "tests/unit/test_critic_agent.py::"
        "test_critic_cost_realism_detection_flags_capacity_and_execution_scenarios"
    ) in content
    assert "tests/unit/test_check_cost_realism_pipeline.py" in content
