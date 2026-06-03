"""Static tests for runtime infrastructure control scripts."""

from pathlib import Path

START_SCRIPT = Path("scripts/start_runtime_infra.ps1")
STOP_SCRIPT = Path("scripts/stop_runtime_infra.ps1")


def test_stop_runtime_infra_is_non_destructive_and_reports_memory() -> None:
    """Stop script should pause services without deleting Docker volumes."""
    script = STOP_SCRIPT.read_text(encoding="utf-8")

    assert "VmmemWSL" in script
    assert "start_aperag.ps1 -Stop" in script
    assert "start_aperag_embedding_server.ps1 -Stop" in script
    assert "docker compose --env-file $envFile -p stat-arb-infisical -f $composePath stop" in script
    assert "docker stop omniroute" in script
    assert "docker compose down" not in script
    assert "down -v" not in script
    assert "Remove-Item" not in script


def test_stop_runtime_infra_requires_explicit_wsl_shutdown() -> None:
    """WSL shutdown is useful but should remain an explicit operator choice."""
    script = STOP_SCRIPT.read_text(encoding="utf-8")

    assert "[switch]$ShutdownWsl" in script
    assert "if ($ShutdownWsl)" in script
    assert "wsl --shutdown" in script


def test_start_runtime_infra_reuses_existing_service_scripts() -> None:
    """Start script should compose existing checked runtime entry points."""
    script = START_SCRIPT.read_text(encoding="utf-8")

    assert "VmmemWSL" in script
    assert "start_aperag_embedding_server.ps1" in script
    assert "start_infisical.ps1" in script
    assert "start_aperag.ps1" in script
    assert "docker start omniroute" in script
    assert "check_infisical.ps1" in script
    assert "check_aperag.ps1" in script
    assert "check_omniroute.ps1" in script
