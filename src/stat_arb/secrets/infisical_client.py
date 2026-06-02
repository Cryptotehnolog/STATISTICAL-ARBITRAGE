"""Small REST client for Infisical Universal Auth and secret reads."""

from dataclasses import dataclass
from typing import Any

import httpx

from stat_arb.secrets.config import InfisicalConfig


class InfisicalError(RuntimeError):
    """Raised when Infisical authentication or secret loading fails."""


@dataclass(frozen=True)
class SecretValue:
    """A secret value loaded from Infisical."""

    key: str
    value: str
    path: str = "/"

    def __repr__(self) -> str:
        """Mask secret values in debug output."""
        return f"SecretValue(key={self.key!r}, value='***', path={self.path!r})"


class InfisicalClient:
    """Infisical REST client using Universal Auth.

    The project avoids the Python SDK because the SDK currently conflicts with
    the project's Pydantic v2 baseline.
    """

    def __init__(
        self,
        config: InfisicalConfig | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.config = config or InfisicalConfig()
        self._client = http_client or httpx.Client(timeout=self.config.timeout_seconds)
        self._owns_client = http_client is None
        self._access_token: str | None = None

    def close(self) -> None:
        """Close the underlying HTTP client if this instance owns it."""
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "InfisicalClient":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def login(self) -> str:
        """Authenticate with Universal Auth and return an access token."""
        self.config.validate_for_runtime()
        payload: dict[str, str] = {
            "clientId": self.config.client_id,
            "clientSecret": self.config.client_secret,
        }
        if self.config.organization_slug:
            payload["organizationSlug"] = self.config.organization_slug

        response = self._client.post(
            f"{self.config.normalized_api_url}/api/v1/auth/universal-auth/login",
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        self._raise_for_response(response, "Infisical authentication failed")
        data = response.json()
        token = data.get("accessToken")
        if not token:
            raise InfisicalError("Infisical authentication response did not include accessToken")
        self._access_token = str(token)
        return self._access_token

    def list_secrets(
        self,
        *,
        recursive: bool = False,
        include_imports: bool = False,
        expand_references: bool = False,
    ) -> dict[str, SecretValue]:
        """List secrets from the configured project, environment, and path."""
        token = self._ensure_token()
        params = {
            **self.config.project_lookup_params,
            "environment": self.config.environment,
            "secretPath": self.config.secret_path,
            "viewSecretValue": "true",
            "recursive": str(recursive).lower(),
            "include_imports": str(include_imports).lower(),
            "expandSecretReferences": str(expand_references).lower(),
        }
        response = self._client.get(
            f"{self.config.normalized_api_url}/api/v3/secrets/raw",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        self._raise_for_response(response, "Infisical secret list failed")
        return self._parse_secrets(response.json())

    def get_secret(self, key: str) -> SecretValue:
        """Return one secret by key or raise a clear error."""
        secrets = self.list_secrets()
        try:
            return secrets[key]
        except KeyError as exc:
            raise InfisicalError(f"Infisical secret not found: {key}") from exc

    def load_required(self, keys: list[str]) -> dict[str, str]:
        """Load required secrets and return a plain key-value mapping."""
        secrets = self.list_secrets()
        missing = [key for key in keys if key not in secrets]
        if missing:
            raise InfisicalError(f"Infisical secrets not found: {', '.join(missing)}")
        return {key: secrets[key].value for key in keys}

    def _ensure_token(self) -> str:
        if self._access_token:
            return self._access_token
        return self.login()

    @staticmethod
    def _parse_secrets(payload: dict[str, Any]) -> dict[str, SecretValue]:
        parsed: dict[str, SecretValue] = {}
        for item in payload.get("secrets", []):
            key = item.get("secretKey")
            if not key:
                continue
            parsed[str(key)] = SecretValue(
                key=str(key),
                value=str(item.get("secretValue", "")),
                path=str(item.get("secretPath", "/")),
            )
        return parsed

    @staticmethod
    def _raise_for_response(response: httpx.Response, message: str) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise InfisicalError(f"{message}: HTTP {response.status_code}") from exc
