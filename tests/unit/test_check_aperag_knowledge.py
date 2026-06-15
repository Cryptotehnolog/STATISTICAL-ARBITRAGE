"""Static tests for ApeRAG knowledge readiness checks."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_aperag_knowledge.ps1")


def test_check_aperag_knowledge_uses_query_aware_keywords() -> None:
    """Knowledge check should not hard-code unrelated full-text keywords."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[string[]]$Keywords" in script
    assert "Get-SearchKeywords" in script
    assert "keywords = $resolvedKeywords" in script
    assert 'keywords = @("ApeRAG", "memory", "backend")' not in script


def test_check_aperag_knowledge_can_require_expected_text() -> None:
    """Semantic smoke should support checking that relevant text was retrieved."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[string[]]$ExpectedText" in script
    assert "$combinedText" in script
    assert "$_.content" in script
    assert "$_.metadata.title" in script
    assert "expected text" in script
    assert "$normalizedCombinedText" in script
    assert '-replace "\\s+", " "' in script


def test_check_aperag_knowledge_can_reject_forbidden_text() -> None:
    """Answer eval needs negative assertions against known-wrong claims."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[string[]]$ForbiddenText" in script
    assert "$forbiddenMatches" in script
    assert "forbidden text" in script
    assert "$normalizedCombinedText" in script


def test_check_aperag_knowledge_allows_larger_topk_for_semantic_qa() -> None:
    """Decision QA should be able to search deeper than the default smoke test."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[int]$TopK = 5" in script
    assert "topk = $TopK" in script


def test_check_aperag_knowledge_readiness_depends_on_required_indexes() -> None:
    """ApeRAG document status may lag while vector/fulltext indexes are already usable."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    bad_docs_block = script.split("$badDocs = @(", 1)[1].split(")", 1)[0]

    assert 'vector_index_status -ne "ACTIVE"' in bad_docs_block
    assert 'fulltext_index_status -ne "ACTIVE"' in bad_docs_block
    assert 'status -ne "COMPLETE"' not in bad_docs_block
