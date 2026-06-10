"""Static tests for the CLI pipeline checkpoint wrapper."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_cli_pipeline.ps1")


def test_check_cli_pipeline_runs_data_cli_tests() -> None:
    """The CLI checkpoint should run Task 15.1 data command coverage."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "Проверка CLI pipeline" in script
    assert "tests/unit/test_cli_data.py" in script
    assert "tests/unit/test_check_cli_pipeline.py" in script
    assert "$LASTEXITCODE -ne 0" in script
