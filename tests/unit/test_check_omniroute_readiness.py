"""Static tests for OmniRoute runtime readiness guard."""

from pathlib import Path

SCRIPT = Path("scripts/check_omniroute_readiness.ps1")


def test_omniroute_readiness_checks_state_models_chat_and_provider_status() -> None:
    """The readiness script should catch runtime degradation before ApeRAG uses OmniRoute."""
    script = SCRIPT.read_text(encoding="utf-8")

    assert "check_omniroute_state.ps1" in script
    assert "/v1/models" in script
    assert "/v1/chat/completions" in script
    assert "provider_connections" in script
    assert "credits_exhausted" in script
    assert "quota_exhausted" in script
    assert "rate_limited_until" in script
    assert "expires_at" in script
    assert "docker logs" in script


def test_omniroute_readiness_has_explicit_warning_policy() -> None:
    """Warning thresholds should be explicit script parameters, not hidden constants."""
    script = SCRIPT.read_text(encoding="utf-8")

    assert "[int]$MaxChatLatencyMs" in script
    assert "[int]$WarnTokenExpiresMinutes" in script
    assert "[int]$RecentLogTail" in script
    assert "[switch]$WarnOnly" in script
    assert "ReadinessIssue" in script


def test_omniroute_readiness_scopes_log_risk_scan_to_current_check() -> None:
    """Old Docker logs from a fixed provider session should not poison fresh readiness."""
    script = SCRIPT.read_text(encoding="utf-8")

    assert "$readinessStartedAtUtc" in script
    assert "--since $readinessStartedAtUtc" in script
