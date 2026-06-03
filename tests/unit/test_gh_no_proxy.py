"""Static tests for GitHub CLI no-proxy wrapper."""

from pathlib import Path

SCRIPT_PATH = Path("scripts/gh_no_proxy.ps1")


def test_gh_no_proxy_clears_proxy_env_for_gh_commands() -> None:
    """Wrapper should remove broken process proxy variables only around gh."""
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "ValueFromRemainingArguments" in script
    assert "HTTP_PROXY" in script
    assert "GIT_HTTPS_PROXY" in script
    assert 'Remove-Item "Env:\\$name"' in script
    assert "& gh @GhArgs" in script
    assert "SetEnvironmentVariable" in script
