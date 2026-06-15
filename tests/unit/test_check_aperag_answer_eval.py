"""Static tests for deterministic ApeRAG answer evaluation."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_aperag_answer_eval.ps1")


def test_answer_eval_requires_facts_and_forbids_bad_claims() -> None:
    """Answer eval should be stricter than a retrieval smoke test."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[string]$Question" in script
    assert "[string[]]$RequiredFacts" in script
    assert "[string[]]$ForbiddenClaims" in script
    assert "check_aperag_knowledge.ps1" in script
    assert "-ExpectedText $RequiredFacts" in script
    assert "-ForbiddenText $ForbiddenClaims" in script
    assert "Answer eval OK" in script


def test_answer_eval_is_deterministic_not_llm_judged() -> None:
    """The current guard should not depend on another generative judge."""
    script = SCRIPT_PATH.read_text(encoding="utf-8").lower()

    assert "llm judge" in script
    assert "openai" not in script
    assert "chat/completions" not in script
