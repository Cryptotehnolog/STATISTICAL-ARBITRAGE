"""Unit tests for Infisical configuration."""

import pytest

from stat_arb.secrets.config import InfisicalConfig


@pytest.fixture(autouse=True)
def clear_infisical_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests isolated from local runtime Infisical credentials."""
    for name in (
        "INFISICAL_API_URL",
        "INFISICAL_CLIENT_ID",
        "INFISICAL_CLIENT_SECRET",
        "INFISICAL_PROJECT_ID",
        "INFISICAL_PROJECT_SLUG",
        "INFISICAL_ORGANIZATION_SLUG",
        "INFISICAL_ENVIRONMENT",
        "INFISICAL_SECRET_PATH",
        "INFISICAL_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)


def test_default_config_targets_local_infisical() -> None:
    """Default config should target the local Docker deployment."""
    config = InfisicalConfig(_env_file=None)

    assert config.api_url == "http://localhost:8080"
    assert config.normalized_api_url == "http://localhost:8080"
    assert config.environment == "dev"
    assert config.secret_path == "/"
    assert config.project_lookup_params == {}


def test_project_lookup_prefers_id() -> None:
    """workspaceId is preferred over workspaceSlug for API compatibility."""
    config = InfisicalConfig(
        project_id="project-id",
        project_slug="project-slug",
        _env_file=None,
    )

    assert config.project_lookup_params == {"workspaceId": "project-id"}


def test_project_lookup_supports_slug() -> None:
    """Machine identities can also use workspaceSlug."""
    config = InfisicalConfig(project_slug="project-slug", _env_file=None)

    assert config.project_lookup_params == {"workspaceSlug": "project-slug"}


def test_runtime_validation_reports_missing_values() -> None:
    """Runtime validation should report all required missing values."""
    config = InfisicalConfig(_env_file=None)

    with pytest.raises(ValueError, match="INFISICAL_CLIENT_ID"):
        config.validate_for_runtime()
