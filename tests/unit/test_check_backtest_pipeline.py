"""Static tests for the backtest pipeline check script."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_backtest_pipeline.ps1")


def test_check_backtest_pipeline_runs_all_backtest_boundary_tests() -> None:
    """Pipeline check should exercise core through registry/memory boundary."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "test_backtest_core.py" in script
    assert "test_backtest_costs.py" in script
    assert "test_backtest_metrics.py" in script
    assert "test_backtest_baseline.py" in script
    assert "test_backtest_sensitivity.py" in script
    assert "test_backtest_reproducibility.py" in script
    assert "test_backtest_walk_forward.py" in script
    assert "test_backtest_agent.py" in script
    assert "--no-cov" in script
