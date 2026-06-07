"""Static tests for curated ApeRAG seed automation."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/seed_aperag_curated.ps1")


def test_seed_aperag_curated_waits_for_graph_when_enabled() -> None:
    """EnableGraph should rebuild and wait for graph indexes before reporting success."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "if ($EnableGraph)" in script
    assert "enable_aperag_curated_graph.ps1" in script
    assert "-CollectionTitle $CollectionTitle" in script
    assert script.index("enable_aperag_curated_graph.ps1") < script.index(
        "ApeRAG curated seed завершен"
    )


def test_seed_aperag_curated_recalculates_quota_before_force_rebuild() -> None:
    """Force rebuild should repair stale ApeRAG quota usage before uploading docs."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "recalculate_aperag_quota.ps1" in script
    assert "if ($Force)" in script
    assert script.index("recalculate_aperag_quota.ps1") < script.index("if ($collection -and $Force)")


def test_seed_aperag_curated_uploads_new_or_changed_shards_without_force() -> None:
    """Incremental seed should not skip new or changed docs when a collection exists."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "$previousHashesByName" in script
    assert "$existingDocumentsByName" in script
    assert "$filesToUpload" in script
    assert "Измененные или отсутствующие curated shards" in script
    assert "DELETE" in script
    assert "Upload-CuratedShard" in script
