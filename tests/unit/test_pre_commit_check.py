"""Unit tests for local pre-commit checklist composition."""

from pathlib import Path

CHECK_SCRIPT_PATH = Path("scripts/check.ps1")
CHECK_UNIT_SCRIPT_PATH = Path("scripts/check_unit.ps1")
PROPERTY_INTEGRATION_SCRIPT_PATH = Path("scripts/check_property_integration.ps1")
RESEARCH_DEFAULTS_SCRIPT_PATH = Path("scripts/check_research_defaults.ps1")
SCRIPT_PATH = Path("scripts/pre_commit_check.ps1")


def test_pre_commit_check_includes_memory_contract_guard() -> None:
    """Fast pre-commit should prevent direct agent memory writes."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_memory_contracts.ps1" in script
    assert "$memoryContractsCheckScript" in script
    assert "& $memoryContractsCheckScript" in script


def test_pre_commit_check_includes_research_defaults_guard() -> None:
    """Fast pre-commit should block hidden research-impacting defaults."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_research_defaults.ps1" in script
    assert "$researchDefaultsCheckScript" in script
    assert "& $researchDefaultsCheckScript" in script


def test_pre_commit_check_includes_legacy_backend_import_guard() -> None:
    """Fast pre-commit should block legacy memory imports in agent-facing code."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_no_legacy_memory_backend_imports.ps1" in script
    assert "$legacyMemoryBackendImportsCheckScript" in script
    assert "& $legacyMemoryBackendImportsCheckScript" in script


def test_pre_commit_check_includes_backtest_agent_boundary_guard() -> None:
    """Fast pre-commit should block Backtest Agent registry and memory boundary regressions."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_backtest_agent_boundaries.ps1" in script
    assert "$backtestAgentBoundaryCheckScript" in script
    assert "& $backtestAgentBoundaryCheckScript" in script


def test_pre_commit_check_includes_property_integration_smoke() -> None:
    """Fast pre-commit should keep property/integration folders exercised."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "check_property_integration.ps1" in script
    assert "$propertyIntegrationCheckScript" in script
    assert "& $propertyIntegrationCheckScript" in script


def test_check_scripts_exit_on_native_command_failure() -> None:
    """PowerShell native command failures should not be masked by later commands."""
    for path in (
        CHECK_SCRIPT_PATH,
        CHECK_UNIT_SCRIPT_PATH,
        PROPERTY_INTEGRATION_SCRIPT_PATH,
        RESEARCH_DEFAULTS_SCRIPT_PATH,
    ):
        script = path.read_text(encoding="utf-8")
        assert "$LASTEXITCODE -ne 0" in script, f"{path} must check native exit codes"
        assert "exit $LASTEXITCODE" in script, f"{path} must propagate native exit codes"


def test_check_script_runs_mypy_typecheck() -> None:
    """Local baseline should keep strict src typing aligned with CI."""
    script = CHECK_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "-m mypy src" in script


def test_check_scripts_resolve_windows_and_linux_virtualenv_python() -> None:
    """PowerShell checks should work on local Windows and GitHub Ubuntu runners."""
    for path in (
        CHECK_SCRIPT_PATH,
        CHECK_UNIT_SCRIPT_PATH,
        PROPERTY_INTEGRATION_SCRIPT_PATH,
        RESEARCH_DEFAULTS_SCRIPT_PATH,
    ):
        script = path.read_text(encoding="utf-8")
        assert ".venv\\Scripts\\python.exe" in script, f"{path} must support Windows venv"
        assert ".venv/bin/python" in script, f"{path} must support Ubuntu venv"
