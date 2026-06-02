"""Unit tests for persistent LightRAG doc_status checks."""

from pathlib import Path
from uuid import uuid4

from stat_arb.scripts import check_lightrag_doc_status as doc_status_module


def _test_dir(name: str) -> Path:
    path = (Path("data/test_tmp") / f"{name}-{uuid4()}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_summarize_doc_status_ignores_duplicate_failures() -> None:
    """Duplicate records should not count as real LightRAG failures."""
    records = {
        "doc-1": {"status": "processed"},
        "dup-1": {
            "status": "failed",
            "content_summary": "[DUPLICATE] Original document: doc-1",
        },
    }

    summary = doc_status_module.summarize_doc_status(records)

    assert summary.processed == 1
    assert summary.failed == 1
    assert summary.duplicate_failed == 1
    assert summary.real_failed == 0


def test_summarize_doc_status_counts_real_failures() -> None:
    """Non-duplicate failed records should count as unresolved failures."""
    records = {
        "doc-1": {"status": "failed", "error": "HTTP 503"},
        "doc-2": {"status": "pending"},
        "doc-3": {"status": "mystery"},
    }

    summary = doc_status_module.summarize_doc_status(records)

    assert summary.real_failed == 1
    assert summary.pending == 1
    assert summary.unknown == 1


def test_check_lightrag_doc_status_allows_missing_when_requested() -> None:
    """Missing storage can be allowed for fresh local setups."""
    test_dir = _test_dir("doc-status-missing")

    result = doc_status_module.check_lightrag_doc_status(
        repo_root=test_dir,
        status_path=test_dir / "missing.json",
        allow_missing=True,
    )

    assert result == 0
