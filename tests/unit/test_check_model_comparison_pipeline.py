"""Unit tests for model-comparison checkpoint command."""

from pathlib import Path


def test_model_comparison_check_runs_explicit_harness_tests() -> None:
    """Checkpoint command should guard TD-0040 model-comparison contracts."""
    script = Path("scripts/check_model_comparison_pipeline.ps1").read_text(encoding="utf-8")

    assert "tests/unit/test_model_comparison.py" in script
    assert "Model comparison pipeline OK" in script
