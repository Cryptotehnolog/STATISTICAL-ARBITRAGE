from __future__ import annotations

import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from stat_arb.dashboard.data import get_dashboard_navigation, load_dashboard_snapshot
from stat_arb.storage import Experiment, Hypothesis, init_database
from stat_arb.storage.database import create_session_factory


def test_load_dashboard_snapshot_reads_registry_without_mutation(tmp_path) -> None:
    """Dashboard snapshot should expose registry counts without changing records."""
    db_path = tmp_path / "registry.db"
    engine = init_database(db_path)
    session_factory = create_session_factory(engine)
    try:
        with session_factory() as session:
            hypothesis = Hypothesis(
                hypothesis_id="hyp-1",
                asset_a="BTC/USDT",
                asset_b="ETH/USDT",
                rationale="Test pair",
                source="rule_based",
                novelty_score=0.9,
                status="new",
                created_by="test",
            )
            session.add(hypothesis)
            session.add(
                Experiment(
                    experiment_id="exp-1",
                    hypothesis_id="hyp-1",
                    status="statistical_testing",
                    current_agent="statistical_testing_agent",
                    created_at=datetime(2026, 1, 1, tzinfo=UTC).replace(tzinfo=None),
                )
            )
            session.commit()

        snapshot = load_dashboard_snapshot(db_path)

        assert snapshot.registry_path == db_path
        assert snapshot.counts["hypotheses"] == 1
        assert snapshot.counts["experiments"] == 1
        assert snapshot.experiments[0]["experiment_id"] == "exp-1"
        assert snapshot.experiments[0]["pair"] == "BTC/USDT / ETH/USDT"

        with session_factory() as session:
            assert session.query(Experiment).count() == 1
            assert session.query(Hypothesis).count() == 1
    finally:
        engine.dispose()


def test_dashboard_navigation_is_read_only_and_russian() -> None:
    """Initial dashboard pages should be Russian read-only navigation labels."""
    navigation = get_dashboard_navigation()

    assert [item.label for item in navigation] == [
        "Обзор",
        "Эксперименты",
        "Гипотезы",
        "Статтесты",
        "Бэктесты",
        "Отчеты",
        "Память",
        "Очередь одобрения",
    ]
    assert all(item.mode == "read_only" for item in navigation)


def test_check_dashboard_structure_script_passes() -> None:
    """Dashboard guard should validate scaffold files and read-only boundaries."""
    powershell_exe = shutil.which("pwsh") or shutil.which("powershell")
    assert powershell_exe is not None

    result = subprocess.run(
        [
            powershell_exe,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/check_dashboard_structure.ps1",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr


def test_pre_commit_runs_dashboard_structure_guard() -> None:
    """Fast pre-commit should keep the dashboard read-only scaffold guarded."""
    script = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")

    assert "check_dashboard_structure.ps1" in script
    assert "$dashboardStructureCheckScript" in script
    assert "Invoke-RequiredCheck $dashboardStructureCheckScript" in script
