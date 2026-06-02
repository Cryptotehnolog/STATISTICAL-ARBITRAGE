"""Unit tests for Infisical auth smoke command."""

from unittest.mock import MagicMock, patch

from stat_arb.scripts import check_infisical_auth as auth_module
from stat_arb.secrets.infisical_client import InfisicalError, SecretValue


def test_check_infisical_auth_passes_when_secret_is_read() -> None:
    """Auth smoke should pass after login and non-empty secret read."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.login.return_value = "token"
    client.get_secret.return_value = SecretValue(
        key="STAT_ARB_INFISICAL_SMOKE_SECRET",
        value="ok",
    )

    with (
        patch.object(auth_module.InfisicalConfig, "validate_for_runtime"),
        patch.object(auth_module, "InfisicalClient", return_value=client),
    ):
        result = auth_module.check_infisical_auth()

    assert result == 0
    client.login.assert_called_once()
    client.get_secret.assert_called_once_with("STAT_ARB_INFISICAL_SMOKE_SECRET")


def test_check_infisical_auth_fails_when_config_is_missing() -> None:
    """Auth smoke should fail clearly when runtime config is incomplete."""
    with patch.object(
        auth_module.InfisicalConfig,
        "validate_for_runtime",
        side_effect=ValueError("missing config"),
    ):
        result = auth_module.check_infisical_auth()

    assert result == 1


def test_check_infisical_auth_fails_when_secret_missing() -> None:
    """Auth smoke should fail when Infisical cannot return the requested secret."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.login.return_value = "token"
    client.get_secret.side_effect = InfisicalError("not found")

    with (
        patch.object(auth_module.InfisicalConfig, "validate_for_runtime"),
        patch.object(auth_module, "InfisicalClient", return_value=client),
    ):
        result = auth_module.check_infisical_auth()

    assert result == 1


def test_check_infisical_auth_fails_when_secret_value_empty() -> None:
    """Auth smoke should reject empty smoke secret values."""
    client = MagicMock()
    client.__enter__.return_value = client
    client.login.return_value = "token"
    client.get_secret.return_value = SecretValue(
        key="STAT_ARB_INFISICAL_SMOKE_SECRET",
        value="",
    )

    with (
        patch.object(auth_module.InfisicalConfig, "validate_for_runtime"),
        patch.object(auth_module, "InfisicalClient", return_value=client),
    ):
        result = auth_module.check_infisical_auth()

    assert result == 1
