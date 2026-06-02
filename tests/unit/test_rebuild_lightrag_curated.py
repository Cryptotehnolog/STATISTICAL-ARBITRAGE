"""Unit tests for curated LightRAG rebuild wrapper script."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/rebuild_lightrag_curated.ps1")


def test_rebuild_lightrag_curated_backs_up_seeds_and_guards() -> None:
    """Rebuild wrapper should backup runtime storage, force seed, and run the guard."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "Move-ToBackup" in script
    assert '$lightragDir = Join-Path $dataDir "lightrag"' in script
    assert "lightrag_seed_manifest.json" in script
    assert "seed_lightrag_curated.ps1" in script
    assert "-Apply -Force" in script
    assert "check_lightrag_memory_fresh.ps1" in script
    assert "Backup создан" in script


def test_rebuild_lightrag_curated_supports_guard_skip_flags() -> None:
    """Rebuild wrapper should expose guard skips for controlled local recovery."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[switch]$SkipGuard" in script
    assert "[switch]$SkipDocker" in script
    assert "[switch]$SkipQuery" in script
    assert "[switch]$SkipViewerExport" in script
    assert "Guard пропущен" in script
