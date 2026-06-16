"""MVP acceptance checkpoint tests for Task 22."""

from __future__ import annotations

from pathlib import Path

from stat_arb.scripts.check_mvp_acceptance import (
    MVP_ACCEPTANCE_TARGETS,
    build_mvp_acceptance_report,
    seed_deterministic_mvp_registry,
)
from stat_arb.storage import create_database_engine, create_session_factory


def test_deterministic_mvp_acceptance_meets_task_22_targets(tmp_path: Path) -> None:
    """The MVP acceptance harness should prove 22.1-22.5 against registry evidence."""
    db_path = tmp_path / "mvp_acceptance.db"
    seed_deterministic_mvp_registry(db_path)

    engine = create_database_engine(db_path)
    session = create_session_factory(engine)()
    try:
        report = build_mvp_acceptance_report(session=session, repo_root=Path.cwd())
    finally:
        session.close()
        engine.dispose()

    assert report.passed is True
    assert report.numeric.assets == MVP_ACCEPTANCE_TARGETS.min_assets
    assert report.numeric.pairs_tested == MVP_ACCEPTANCE_TARGETS.min_pairs_tested
    assert report.numeric.completed_experiments == MVP_ACCEPTANCE_TARGETS.min_experiments
    assert report.numeric.generated_reports >= MVP_ACCEPTANCE_TARGETS.min_experiments
    assert {section.task_id for section in report.sections} == {
        "22.1",
        "22.2",
        "22.3",
        "22.4",
        "22.5",
    }
    assert all(section.passed for section in report.sections)


def test_mvp_acceptance_fails_when_scale_targets_are_not_met(tmp_path: Path) -> None:
    """Acceptance must fail closed instead of treating partial smoke as MVP."""
    db_path = tmp_path / "partial.db"
    seed_deterministic_mvp_registry(
        db_path,
        asset_count=12,
        pair_count=3,
        experiment_count=1,
    )

    engine = create_database_engine(db_path)
    session = create_session_factory(engine)()
    try:
        report = build_mvp_acceptance_report(session=session, repo_root=Path.cwd())
    finally:
        session.close()
        engine.dispose()

    assert report.passed is False
    numeric_section = next(section for section in report.sections if section.task_id == "22.2")
    assert numeric_section.passed is False
    assert any("assets" in failure for failure in numeric_section.failures)
    assert any("pairs" in failure for failure in numeric_section.failures)
    assert any("experiments" in failure for failure in numeric_section.failures)


def test_mvp_acceptance_guard_is_in_pre_commit_check() -> None:
    """The Task 22 checkpoint should stay wired into the local guard surface."""
    script = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    assert "check_mvp_acceptance.ps1" in script
