"""Static tests for the pair alignment boundary guard."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_pair_alignment_boundary.ps1")
PRE_COMMIT_PATH = Path("scripts/pre_commit_check.ps1")
CI_PATH = Path(".github/workflows/ci.yml")


def test_pair_alignment_boundary_guard_targets_future_pair_modules() -> None:
    """Guard should watch future statistical boundaries for explicit alignment."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "src/stat_arb/statistical_testing" in script
    assert "src/stat_arb/backtesting" in script
    assert "OHLCVBatch" in script
    assert "StatisticalTestResult" in script
    assert "align_ohlcv_pair" in script
    assert "PairAlignmentResult" in script
    assert "reviewOnlyModules" in script
    assert "src/stat_arb/agents/critic.py" in script
    assert "hedge_ratio" not in script
    assert "hedge_ratio|pair" not in script


def test_pair_alignment_boundary_guard_is_in_fast_checks_and_ci() -> None:
    """The guard should run locally and in GitHub Actions."""
    pre_commit = PRE_COMMIT_PATH.read_text(encoding="utf-8")
    ci = CI_PATH.read_text(encoding="utf-8")

    assert "check_pair_alignment_boundary.ps1" in pre_commit
    assert "& $pairAlignmentBoundaryCheckScript" in pre_commit
    assert "Check pair alignment boundary" in ci
    assert "./scripts/check_pair_alignment_boundary.ps1" in ci
