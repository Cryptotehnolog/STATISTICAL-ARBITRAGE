"""Static tests for the scripted pair-screening workflow."""

from pathlib import Path

SCREEN_SCRIPT = Path("scripts/screen_pairs.ps1")
CHECK_SCRIPT = Path("scripts/check_pair_screening_pipeline.ps1")
PRE_COMMIT_SCRIPT = Path("scripts/pre_commit_check.ps1")


def test_screen_pairs_script_uses_hypothesis_agent_cli_boundary() -> None:
    """Pair screening should be a script over the existing Hypothesis Agent CLI."""
    script = SCREEN_SCRIPT.read_text(encoding="utf-8")

    assert "param(" in script
    assert "[Parameter(Mandatory = $true)]" in script
    assert "uv run stat-arb hypothesis generate" in script
    assert "--assets-json" in script
    assert "--correlations-json" in script
    assert "--p-values-json" in script
    assert "--min-abs-correlation" in script
    assert "--min-market-cap" in script
    assert "--max-pairs" in script
    assert "--candidate-alpha" in script
    assert "--db-path" in script
    assert "uv run stat-arb hypothesis list" in script
    assert "ApeRAGMemoryClient" not in script


def test_pair_screening_checkpoint_runs_script_and_cli_coverage() -> None:
    """Checkpoint should cover the script contract and CLI generation behavior."""
    script = CHECK_SCRIPT.read_text(encoding="utf-8")

    assert "Проверка pair-screening workflow" in script
    assert "test_pair_screening_workflow.py" in script
    assert "test_cli_data.py::test_hypothesis_generate_uses_rule_based_agent_boundary" in script
    assert "$LASTEXITCODE -ne 0" in script


def test_pre_commit_runs_pair_screening_checkpoint() -> None:
    """The pair-screening checkpoint should be part of the local pre-commit guard."""
    script = PRE_COMMIT_SCRIPT.read_text(encoding="utf-8")

    assert "check_pair_screening_pipeline.ps1" in script
    assert "$pairScreeningPipelineCheckScript" in script
