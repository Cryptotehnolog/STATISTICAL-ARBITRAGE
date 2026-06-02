"""Unit tests for LightRAG memory freshness guard script."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_lightrag_memory_fresh.ps1")


def test_memory_fresh_guard_checks_seed_doc_status_export_and_query() -> None:
    """Guard should compose the key LightRAG freshness checks."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "seed_lightrag_curated.ps1" in script
    assert "Dry run: 0 changed document" in script
    assert "check_omniroute.ps1" in script
    assert "-SkipSmoke" in script
    assert "check_lightrag_graph_export.ps1" in script
    assert "query_lightrag_curated.ps1" in script
    assert "technical_debt.md" in script
    assert "docs/knowledge" in script
    assert "kv_store_doc_status.json" in script
    assert "duplicate source_id" in script
    assert "processed curated docs" in script


def test_memory_fresh_guard_supports_skip_flags() -> None:
    """Guard should allow fast local checks when Docker or query are intentionally skipped."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[switch]$SkipQuery" in script
    assert "[switch]$SkipDocker" in script
    assert "Query smoke пропущен" in script
    assert "Docker/OmniRoute readiness пропущен" in script
