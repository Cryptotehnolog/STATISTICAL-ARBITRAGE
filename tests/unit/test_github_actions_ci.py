"""Static tests for GitHub Actions CI workflow."""

from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/ci.yml")


def test_ci_workflow_runs_core_python_checks() -> None:
    """CI should run the same fast, secret-safe checks as the local baseline."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "on:" in workflow
    assert 'branches: ["master"]' in workflow
    assert "ubuntu-latest" in workflow
    assert "actions/checkout@v6" in workflow
    assert "actions/setup-python@v6" in workflow
    assert "astral-sh/setup-uv@v8.2.0" in workflow
    assert "actions/checkout@v4" not in workflow
    assert "actions/setup-python@v5" not in workflow
    assert "astral-sh/setup-uv@v5" not in workflow
    assert "uv sync --extra dev" in workflow
    assert "./scripts/check_user_facing_russian.ps1" in workflow
    assert "./scripts/check_secret_leaks.ps1" in workflow
    assert "./scripts/check_research_defaults.ps1" in workflow
    assert "./scripts/check_property_integration.ps1" in workflow
    assert "uv run ruff check --no-cache src tests" in workflow
    assert 'uv run pytest tests/unit -m "not slow"' in workflow
    assert "--cov=stat_arb.backtest" in workflow
    assert "--cov=stat_arb.statistical" in workflow
    assert "--cov=stat_arb.storage" in workflow
    assert "--cov-fail-under=70" in workflow
    assert "--no-cov" not in workflow


def test_ci_workflow_does_not_require_local_services_or_secrets() -> None:
    """Fast CI should not depend on Docker services, OmniRoute, Infisical, or memory seed."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "check_omniroute.ps1" not in workflow
    assert "check_infisical_auth.ps1" not in workflow
    assert "seed_lightrag" not in workflow
    assert "OMNIROUTE_API_KEY" not in workflow
