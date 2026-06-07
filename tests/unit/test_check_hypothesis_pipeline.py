"""Static tests for the hypothesis pipeline checkpoint script."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_hypothesis_pipeline.ps1")


def test_check_hypothesis_pipeline_runs_generation_and_boundary_tests() -> None:
    """Checkpoint should exercise generation, novelty, linking, and guard tests."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "test_hypothesis_agent.py" in script
    assert "test_check_hypothesis_pipeline.py" in script
    assert "--no-cov" in script
