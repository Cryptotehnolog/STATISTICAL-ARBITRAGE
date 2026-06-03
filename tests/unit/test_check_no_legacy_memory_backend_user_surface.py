"""Static tests for legacy memory backend user-surface guard."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_no_legacy_memory_backend_user_surface.ps1")
PRE_COMMIT_PATH = Path("scripts/pre_commit_check.ps1")


def test_guard_blocks_replaced_backend_commands() -> None:
    """Guard should block old memory backend commands from README/operator docs."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '"README.md"' in script
    assert '"docs/repository_structure.md"' in script
    assert "seed_lightrag" in script
    assert "query_lightrag" in script
    assert "LightRAG \\(Memory\\)" in script
    assert "Legacy memory backend не должен возвращаться" in script
    assert "Проверка активной пользовательской legacy memory backend поверхности прошла." in script


def test_pre_commit_runs_legacy_user_surface_guard() -> None:
    """Pre-commit checklist should keep active memory docs on ApeRAG."""
    script = PRE_COMMIT_PATH.read_text(encoding="utf-8")

    assert "check_no_legacy_memory_backend_user_surface.ps1" in script
