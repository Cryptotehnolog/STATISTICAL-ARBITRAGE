"""Static tests for ApeRAG curated graph rebuild automation."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/enable_aperag_curated_graph.ps1")


def test_enable_aperag_curated_graph_retries_transient_llm_failures() -> None:
    """Graph rebuild should retry transient LLM/provider failures before failing."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[int]$MaxRetries" in script
    assert "[int]$RetryDelaySeconds" in script
    assert "ALL_ACCOUNTS_INACTIVE" in script
    assert "all upstream accounts are inactive" in script
    assert "ServiceUnavailable" in script
    assert "GraphRebuildStartedAt" in script
    assert "RegexOptions]::IgnoreCase" in script
    assert 'Start-Sleep -Seconds 5' in script
    assert "--since" in script
    assert "Invoke-GraphRebuild" in script
    assert "Test-TransientGraphFailure" in script
    assert "Retrying failed GRAPH documents without confirmed transient log pattern" in script
    assert "Start-Sleep -Seconds $RetryDelaySeconds" in script
    assert script.index("Test-TransientGraphFailure") < script.index(
        "ApeRAG graph rebuild failed"
    )
