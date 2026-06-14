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
    assert "uv run mypy src" in workflow
    assert 'uv run pytest tests/unit -m "not slow"' in workflow
    assert "--cov=stat_arb.backtest" in workflow
    assert "--cov=stat_arb.cli" in workflow
    assert "--cov=stat_arb.dashboard" in workflow
    assert "--cov=stat_arb.statistical" in workflow
    assert "--cov=stat_arb.storage" in workflow
    assert "--cov-fail-under=70" in workflow
    assert "--no-cov" not in workflow


def test_ci_workflow_does_not_require_local_services_or_secrets() -> None:
    """Fast CI should not depend on Docker services, OmniRoute, Infisical, or memory seed."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "check_omniroute.ps1" not in workflow
    assert "check_infisical_auth.ps1" not in workflow
    assert "check_memory_health.ps1" not in workflow
    assert "check_aperag" not in workflow
    assert "docker compose" not in workflow
    assert "start_aperag" not in workflow
    assert "seed_lightrag" not in workflow
    assert "seed_aperag" not in workflow
    assert "OMNIROUTE_API_KEY" not in workflow
    assert "INFISICAL_CLIENT_SECRET" not in workflow


def test_ci_workflow_catches_lint_type_test_and_reproducibility_failures() -> None:
    """Task 18.4 should guard the failure-catching CI steps, not just workflow syntax."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "Run Ruff" in workflow
    assert "uv run ruff check --no-cache src tests" in workflow
    assert "Run mypy" in workflow
    assert "uv run mypy src" in workflow
    assert "Run unit tests" in workflow
    assert 'uv run pytest tests/unit -m "not slow"' in workflow
    assert "--cov-fail-under=70" in workflow
    assert "Check property and integration smoke tests" in workflow
    assert "./scripts/check_property_integration.ps1" in workflow
    assert "Check reproducibility workflow" in workflow
    assert "./scripts/check_reproducibility_workflow.ps1" in workflow
    assert "Check secret leaks" in workflow
    assert "./scripts/check_secret_leaks.ps1" in workflow


def test_ci_task_18_4_is_marked_complete_with_guard_tests() -> None:
    """The plan should reflect that CI workflow guard tests exist."""
    tasks = Path(".kiro/specs/quant-research-architecture/tasks.md").read_text(encoding="utf-8")

    assert "- [x]* 18.4 Write integration tests for CI workflows" in tasks
    assert "tests/unit/test_github_actions_ci.py" in tasks
