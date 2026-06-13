from pathlib import Path

SCRIPT_PATH = Path("scripts/start_aperag_embedding_server.ps1")


def test_embedding_server_start_uses_native_powershell_process_launch() -> None:
    """Embedding server launcher should not mask success behind cmd.exe start semantics."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "Start-Process" in script
    assert "-WindowStyle Hidden" in script
    assert "cmd.exe /c" not in script
    assert "start `\"stat-arb-aperag-embedding`\"" not in script


def test_embedding_server_start_has_explicit_cold_start_wait() -> None:
    """Cold local embedding model startup should not be treated as immediate failure."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[int]$HealthWaitSeconds = 180" in script
    assert "$deadline = (Get-Date).AddSeconds($HealthWaitSeconds)" in script
    assert "не стартовал за $HealthWaitSeconds секунд" in script
