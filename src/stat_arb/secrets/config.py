"""Configuration for Infisical secrets management."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InfisicalConfig(BaseSettings):
    """Configuration for Infisical Universal Auth and secrets reads."""

    model_config = SettingsConfigDict(
        env_prefix="INFISICAL_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    api_url: str = Field(
        default="http://localhost:8080",
        description="Base URL for local or hosted Infisical API",
    )
    client_id: str = Field(default="", description="Machine identity client ID")
    client_secret: str = Field(default="", description="Machine identity client secret")
    project_id: str = Field(default="", description="Infisical project ID")
    project_slug: str = Field(default="", description="Infisical project slug")
    organization_slug: str = Field(default="", description="Optional organization slug")
    environment: str = Field(default="dev", description="Infisical environment slug")
    secret_path: str = Field(default="/", description="Infisical secret path")
    timeout_seconds: float = Field(
        default=20.0,
        description="HTTP timeout for Infisical API calls",
        ge=1.0,
    )

    @property
    def normalized_api_url(self) -> str:
        """Return API URL without a trailing slash."""
        return self.api_url.rstrip("/")

    @property
    def project_lookup_params(self) -> dict[str, str]:
        """Return project query parameters supported by Infisical API."""
        if self.project_id:
            return {"workspaceId": self.project_id}
        if self.project_slug:
            return {"workspaceSlug": self.project_slug}
        return {}

    def validate_for_runtime(self) -> None:
        """Validate that required runtime credentials are present."""
        missing = []
        if not self.client_id:
            missing.append("INFISICAL_CLIENT_ID")
        if not self.client_secret:
            missing.append("INFISICAL_CLIENT_SECRET")
        if not self.project_id and not self.project_slug:
            missing.append("INFISICAL_PROJECT_ID или INFISICAL_PROJECT_SLUG")
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Не хватает Infisical configuration: {joined}")
