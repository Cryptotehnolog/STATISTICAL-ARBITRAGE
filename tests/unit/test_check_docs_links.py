"""Static tests for local documentation link guard."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/check_docs_links.ps1")
PRE_COMMIT_PATH = Path("scripts/pre_commit_check.ps1")


def test_docs_link_guard_script_exists_and_targets_readme_docs_and_kiro_specs() -> None:
    """The docs link guard should cover committed markdown documentation."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "README.md" in script
    assert "docs" in script
    assert ".kiro\\specs" in script
    assert "docs\\knowledge_graph" in script
    assert "local markdown links" in script
    assert "inline code local markdown paths" in script


def test_docs_link_guard_is_wired_into_pre_commit_checklist() -> None:
    """Broken local docs links should be caught before commits."""
    pre_commit = PRE_COMMIT_PATH.read_text(encoding="utf-8")

    assert "check_docs_links.ps1" in pre_commit
    assert "Invoke-RequiredCheck $docsLinksCheckScript" in pre_commit


def test_readme_core_docs_references_point_to_existing_files() -> None:
    """README may advertise core docs only when the files exist."""
    readme = Path("README.md").read_text(encoding="utf-8")

    for path in (
        "docs/architecture.md",
        "docs/agents.md",
        "docs/data.md",
        "docs/schema.md",
    ):
        assert f"`{path}`" in readme
        assert Path(path).exists()

    assert "`docs/api.md`" not in readme
