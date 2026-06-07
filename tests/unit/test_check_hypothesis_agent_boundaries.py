"""Static tests for the Hypothesis Agent boundary guard script."""

from pathlib import Path


def test_hypothesis_agent_boundary_guard_is_wired_into_pre_commit_and_ci() -> None:
    """Boundary guard should run locally and in CI."""
    script = Path("scripts/check_hypothesis_agent_boundaries.ps1").read_text(encoding="utf-8")
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "src\\stat_arb\\agents\\hypothesis.py" in script
    assert "ApeRAGMemoryClient" in script
    assert "MemoryWriteRequest" in script
    assert "session.add" in script
    assert "check_hypothesis_agent_boundaries.ps1" in pre_commit
    assert "./scripts/check_hypothesis_agent_boundaries.ps1" in ci
