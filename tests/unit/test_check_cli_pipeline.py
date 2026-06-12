"""Static tests for the CLI pipeline checkpoint wrapper."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_cli_pipeline.ps1")


def test_check_cli_pipeline_runs_cli_tests() -> None:
    """The CLI checkpoint should run Task 15 command coverage."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    cli_tests = Path("tests/unit/test_cli_data.py").read_text(encoding="utf-8")

    assert "Проверка CLI pipeline" in script
    assert "tests/unit/test_cli_data.py" in script
    assert "tests/unit/test_cli_stage_support.py" in script
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
    assert '"run-pipeline"' in cli_tests
    assert "rejects_report_stage_without_factual_artifacts" in cli_tests
    assert "executes_backtesting_then_reporting_from_sidecar" in cli_tests
    assert "stops_before_reporting_without_sidecar" in cli_tests


def test_cli_stage_executor_does_not_bypass_memory_or_report_boundaries() -> None:
    """Stage executor must not write ApeRAG directly or create reports without artifacts."""
    cli_source = Path("src/stat_arb/cli/main.py").read_text(encoding="utf-8")
    support_source = Path("src/stat_arb/cli/stage_support.py").read_text(encoding="utf-8")

    assert "run_statistical_testing" in cli_source
    assert "run_backtest_agent_persistence" in cli_source
    assert "run_critic_agent_persistence" in cli_source
    assert "run_report_agent" in cli_source
    assert "run-pipeline сейчас поддерживает только stages=backtesting,reporting" in cli_source
    assert "matching backtest_series sidecar is required" in cli_source
    assert "backtest_series sidecar is required before reporting pipeline stage" in cli_source
    assert "_require_matching_backtest_series_sidecar" in cli_source
    assert "_latest_backtest_id_from_series_sidecar" in cli_source
    assert "ApeRAGMemoryClient" not in cli_source
    assert "STATISTICAL_TESTING" in support_source
    assert "BACKTESTING" in support_source
    assert "CRITIC_REVIEW" in support_source
    assert "REPORTING" in support_source


def test_stage_payload_parsing_lives_outside_cli_entrypoint() -> None:
    """Stage payload parsing should stay typed and separate from the Click entrypoint."""
    cli_source = Path("src/stat_arb/cli/main.py").read_text(encoding="utf-8")
    payload_source = Path("src/stat_arb/cli/stage_payloads.py").read_text(encoding="utf-8")

    assert "build_statistical_testing_input" in cli_source
    assert "build_backtest_agent_input" in cli_source
    assert "build_critic_agent_input" in cli_source
    assert "build_report_agent_input" in cli_source
    assert "def _payload_float" not in cli_source
    assert "def _object_datetime" not in cli_source
    assert "def build_statistical_testing_input" in payload_source
    assert "def build_backtest_agent_input" in payload_source
    assert "def build_critic_agent_input" in payload_source
    assert "def build_report_agent_input" in payload_source
