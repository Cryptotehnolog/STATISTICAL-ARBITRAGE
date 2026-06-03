"""Static tests for user-facing Russian text guard."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_user_facing_russian.ps1")


def test_user_facing_russian_guard_normalizes_paths_for_ubuntu_ci() -> None:
    """The guard should exclude internal docs/knowledge on Windows and Ubuntu paths."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '$normalized = $RelativePath -replace "/", "\\"' in script
    assert "$normalized.StartsWith" in script
    assert '"docs\\knowledge"' in script
