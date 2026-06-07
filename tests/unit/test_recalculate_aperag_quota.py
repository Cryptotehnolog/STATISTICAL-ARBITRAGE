"""Static tests for ApeRAG quota recalculation helper."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/recalculate_aperag_quota.ps1")


def test_recalculate_aperag_quota_uses_official_api_without_printing_secret() -> None:
    """Quota helper should use ApeRAG API and avoid leaking the API key."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "/api/v1/quotas" in script
    assert "/recalculate" in script
    assert "APERAG_API_KEY не задан" in script
    assert "Write-Output $env:APERAG_API_KEY" not in script
    assert "Quota recalculation завершен" in script

