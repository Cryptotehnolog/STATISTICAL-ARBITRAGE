"""Static tests for the CLI pipeline checkpoint wrapper."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_cli_pipeline.ps1")


def test_check_cli_pipeline_runs_cli_tests() -> None:
    """The CLI checkpoint should run Task 15 command coverage."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    cli_tests = Path("tests/unit/test_cli_data.py").read_text(encoding="utf-8")

    assert "Проверка CLI pipeline" in script
    assert "tests/unit/test_cli_data.py" in script
    assert "tests/unit/test_check_cli_pipeline.py" in script
    assert "$LASTEXITCODE -ne 0" in script
    assert '["data", "list"' in cli_tests
    assert '["hypothesis", "list"' in cli_tests
    assert '["experiment", "list"' in cli_tests
    assert '"experiment"' in cli_tests
    assert '"status"' in cli_tests
    assert '"advance"' in cli_tests
    assert '"run-stage"' in cli_tests
    assert '"execute-stage"' in cli_tests
    assert "rejects_report_stage_without_factual_artifacts" in cli_tests


def test_cli_stage_executor_does_not_bypass_memory_or_report_boundaries() -> None:
    """Stage executor must not write ApeRAG directly or create reports without artifacts."""
    cli_source = Path("src/stat_arb/cli/main.py").read_text(encoding="utf-8")

    assert "run_statistical_testing" in cli_source
    assert "run_backtest_agent_persistence" in cli_source
    assert "run_critic_agent_persistence" in cli_source
    assert "ApeRAGMemoryClient" not in cli_source
    assert "run_report_agent" not in cli_source
    assert "stage executor пока поддерживает statistical_testing, backtesting" in cli_source
    assert "и critic_review" in cli_source


def test_stage_payload_parsing_lives_outside_cli_entrypoint() -> None:
    """Stage payload parsing should stay typed and separate from the Click entrypoint."""
    cli_source = Path("src/stat_arb/cli/main.py").read_text(encoding="utf-8")
    payload_source = Path("src/stat_arb/cli/stage_payloads.py").read_text(encoding="utf-8")

    assert "build_statistical_testing_input" in cli_source
    assert "build_backtest_agent_input" in cli_source
    assert "build_critic_agent_input" in cli_source
    assert "def _payload_float" not in cli_source
    assert "def _object_datetime" not in cli_source
    assert "def build_statistical_testing_input" in payload_source
    assert "def build_backtest_agent_input" in payload_source
    assert "def build_critic_agent_input" in payload_source
