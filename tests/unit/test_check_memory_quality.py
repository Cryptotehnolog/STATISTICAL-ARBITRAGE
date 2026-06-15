"""Static tests for project memory quality checks."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_memory_quality.ps1")


def test_memory_quality_check_combines_health_freshness_and_semantic_qa() -> None:
    """Memory quality should check runtime, freshness, graph, and project decisions."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "start_aperag_embedding_server.ps1" in script
    assert "check_aperag_memory_fresh.ps1" in script
    assert "-RequireCuratedGraph" in script
    assert "check_aperag_knowledge.ps1" in script
    assert "check_aperag_answer_eval.ps1" in script
    assert "Semantic QA" in script
    assert "Answer eval" in script
    assert "SkipAnswerEval" in script


def test_memory_quality_check_asks_project_specific_questions() -> None:
    """Semantic QA should cover decisions the assistant previously forgot."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "Future paper/live trading roles" in script
    assert "Regime Switch Detector" in script
    assert "Execution and Slippage Simulator" in script
    assert "Dynamic Risk and Capital Allocator" in script
    assert "patoles/agent-flow" in script
    assert "Rust" in script
    assert "ApeRAG" in script
    assert "GitHub Actions Node.js 24" in script
    assert "actions/checkout@v6" in script
    assert "One-bar DataQualityReport" in script
    assert "is_valid=false" in script
    assert "passed=false" in script
    assert "insufficient_data" in script


def test_memory_quality_answer_eval_has_required_and_forbidden_claims() -> None:
    """Memory quality should verify both required facts and forbidden hallucinations."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "RequiredFacts" in script
    assert "ForbiddenClaims" in script
    assert "one-bar DataQualityReport passed=true" in script
    assert "RLMs should replace ApeRAG now" in script
    assert "Context Engine may bypass Memory Agent policy" in script
