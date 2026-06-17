"""Static tests for the statistical testing checkpoint script."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_statistical_pipeline.ps1")


def test_check_statistical_pipeline_runs_statistical_and_agent_boundaries() -> None:
    """Checkpoint should exercise statistical functions and registry/memory agent boundary."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "test_statistical_testing_agent.py" in script
    assert "test_cointegration.py" in script
    assert "test_stationarity.py" in script
    assert "test_hedge_ratio.py" in script
    assert "test_mean_reversion.py" in script
    assert "test_regime.py" in script
    assert "test_zscore.py" in script
    assert "test_validation_windows.py" in script
    assert "test_statistical_properties.py" in script
    assert "AgentAuditEvent" in script
    assert "audit_writer\\.append" in script
    assert "--no-cov" in script
