"""Guards for the research defaults policy."""

from pathlib import Path

RESEARCH_CONTRACTS_PATH = Path("docs/knowledge/research_workflow_contracts.md")


def test_research_defaults_policy_is_documented() -> None:
    """The project should distinguish hidden research defaults from safe technical defaults."""
    text = RESEARCH_CONTRACTS_PATH.read_text(encoding="utf-8")

    assert "## Defaults Policy" in text
    assert "Hidden research defaults are not allowed" in text
    assert "Technical defaults are allowed" in text
    assert "named persisted preset" in text
    assert "config hash" in text
    assert "old planning examples" in text
