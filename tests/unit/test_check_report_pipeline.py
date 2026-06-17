"""Tests for the Report Agent checkpoint script."""

from pathlib import Path


def test_check_report_pipeline_runs_report_tests() -> None:
    """Report checkpoint command should run report generation and boundary tests."""
    script = Path("scripts/check_report_pipeline.ps1").read_text(encoding="utf-8")

    assert "test_backtest_report_generation.py" in script
    assert "test_report_agent.py" in script
    assert "test_check_report_pipeline.py" in script
    assert "uv run pytest" in script
    assert "--no-cov" in script


def test_check_report_pipeline_is_in_pre_commit_and_ci() -> None:
    """Report checkpoint should run in local and CI baselines."""
    pre_commit = Path("scripts/pre_commit_check.ps1").read_text(encoding="utf-8")
    ci = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "check_report_pipeline.ps1" in pre_commit
    assert "Invoke-RequiredCheck $reportPipelineCheckScript" in pre_commit
    assert "Check Report Agent pipeline" in ci
    assert "./scripts/check_report_pipeline.ps1" in ci


def test_report_source_package_is_not_ignored_as_output() -> None:
    """Report source modules must not be hidden by output-directory ignore rules."""
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "\n/reports/\n" in gitignore
    assert "\nreports/\n" not in gitignore


def test_report_agent_uses_registry_linked_backtest_series_sidecars() -> None:
    """Report Agent should load factual chart series only through registry artifacts."""
    source = Path("src/stat_arb/agents/report.py").read_text(encoding="utf-8")
    tests = Path("tests/unit/test_report_agent.py").read_text(encoding="utf-8")

    assert 'artifact_type == "backtest_series"' in source
    assert "ReportSeriesSnapshot" in source
    assert "matching backtest_series sidecar is required" in source
    assert "backtest_series artifact does not match requested backtest" in source
    assert "test_report_agent_requires_factual_series_sidecar" in tests


def test_report_pipeline_guard_preserves_audit_boundary() -> None:
    """Report checkpoint should guard the staged audit-trail slice."""
    script = Path("scripts/check_report_pipeline.ps1").read_text(encoding="utf-8")
    source = Path("src/stat_arb/agents/report.py").read_text(encoding="utf-8")
    tests = Path("tests/unit/test_report_agent.py").read_text(encoding="utf-8")

    assert "AgentAuditEvent" in script
    assert "audit_writer\\.append" in script
    assert "AgentAuditEvent" in source
    assert "audit_writer.append" in source
    assert "test_report_agent_writes_operator_safe_audit_event" in tests
