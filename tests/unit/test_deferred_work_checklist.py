"""Guards for keeping deferred work visible to the user."""

import re
from pathlib import Path

SCRIPT_PATH = Path("scripts/check_deferred_work_checklist.ps1")
CHECKLIST_PATH = Path("docs/deferred_work_checklist.md")
TECH_DEBT_PATH = Path("docs/technical_debt.md")
FUTURE_IDEAS_PATH = Path("docs/knowledge/future_ideas.md")
TECH_DEBT_BACKLOG_PATH = Path("docs/knowledge/technical_debt_backlog.md")


def _ids(pattern: str, text: str) -> set[str]:
    return set(re.findall(pattern, text, flags=re.MULTILINE))


def test_deferred_work_checklist_mentions_all_open_technical_debt_ids() -> None:
    """Every open TD item should be visible in the human-facing checklist."""
    checklist = CHECKLIST_PATH.read_text(encoding="utf-8")
    technical_debt = TECH_DEBT_PATH.read_text(encoding="utf-8")

    open_section = technical_debt.split("## Resolved", maxsplit=1)[0]
    open_td_ids = _ids(r"^### (TD-\d{4}):", open_section)

    assert open_td_ids
    missing = sorted(td_id for td_id in open_td_ids if td_id not in checklist)
    assert missing == []


def test_deferred_work_checklist_mentions_all_proposed_future_ideas() -> None:
    """Proposed future ideas from curated memory should not disappear from the checklist."""
    checklist = CHECKLIST_PATH.read_text(encoding="utf-8")
    future_ideas = FUTURE_IDEAS_PATH.read_text(encoding="utf-8")

    proposed_ids: set[str] = set()
    for block in future_ideas.split("\n## "):
        if "Status: proposed" in block:
            match = re.search(r"(IDEA-\d{4})", block)
            if match:
                proposed_ids.add(match.group(1))

    assert proposed_ids
    missing = sorted(idea_id for idea_id in proposed_ids if idea_id not in checklist)
    assert missing == []


def test_deferred_work_guard_is_wired_into_pre_commit() -> None:
    """The local pre-commit checklist should catch missing deferred items."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")

    assert "docs\\technical_debt.md" in script
    assert "docs\\knowledge\\future_ideas.md" in script
    assert "docs\\deferred_work_checklist.md" in script
    assert "check_deferred_work_checklist.ps1" in pre_commit
    assert "Invoke-RequiredCheck $deferredWorkChecklistScript" in pre_commit


def test_human_checklist_and_memory_backlog_describe_answer_eval_state() -> None:
    """Deferred roadmap should describe the current memory-quality layer accurately."""
    checklist = CHECKLIST_PATH.read_text(encoding="utf-8")
    backlog = TECH_DEBT_BACKLOG_PATH.read_text(encoding="utf-8")

    assert "deterministic answer-eval" in checklist
    assert "обязательные факты" in checklist
    assert "запрещенные ложные утверждения" in checklist
    assert "deterministic answer-eval" in backlog
    assert "required facts" in backlog
    assert "forbidden claims" in backlog
    assert "all 10 curated shards" not in backlog


def test_runtime_cleanup_is_documented_as_manual_and_safe() -> None:
    """Runtime cleanup should be a documented manual maintenance action, not hidden automation."""
    checklist = CHECKLIST_PATH.read_text(encoding="utf-8")
    technical_debt = TECH_DEBT_PATH.read_text(encoding="utf-8")
    maintenance_doc = Path("docs/runtime_maintenance.md").read_text(encoding="utf-8")

    assert "TD-0011" in checklist
    assert "Runtime cleanup" in technical_debt
    assert "clean_runtime_artifacts.ps1" in maintenance_doc
    assert "dry-run" in maintenance_doc
    assert "-Apply" in maintenance_doc
    assert "data/lightrag" not in maintenance_doc
    assert "data/aperag" in maintenance_doc
    assert "infra/infisical/.env" in maintenance_doc
    assert "Docker volumes" in maintenance_doc
