"""Unit tests for Infisical REST client."""

import httpx
import pytest

from stat_arb.secrets.config import InfisicalConfig
from stat_arb.secrets.infisical_client import InfisicalClient, InfisicalError, SecretValue


def make_client(handler: httpx.MockTransport) -> InfisicalClient:
    """Create a test client with fake Infisical transport."""
    config = InfisicalConfig(
        api_url="http://infisical.test",
        client_id="client-id",
        client_secret="client-secret",
        project_id="project-id",
        environment="dev",
    )
    return InfisicalClient(config, http_client=httpx.Client(transport=handler))


def test_login_uses_universal_auth_endpoint() -> None:
    """Client should authenticate with Infisical Universal Auth."""
    seen_payload = {}

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_payload
        seen_payload = dict(request.read() and __import__("json").loads(request.content))
        assert request.url.path == "/api/v1/auth/universal-auth/login"
        return httpx.Response(200, json={"accessToken": "token", "expiresIn": 7200})

    client = make_client(httpx.MockTransport(handler))

    assert client.login() == "token"
    assert seen_payload == {"clientId": "client-id", "clientSecret": "client-secret"}


def test_list_secrets_sends_expected_query_and_auth_header() -> None:
    """Client should list raw secrets with project and environment scope."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"accessToken": "token", "expiresIn": 7200})

        assert request.url.path == "/api/v3/secrets/raw"
        assert request.headers["Authorization"] == "Bearer token"
        assert request.url.params["workspaceId"] == "project-id"
        assert request.url.params["environment"] == "dev"
        assert request.url.params["secretPath"] == "/"
        return httpx.Response(
            200,
            json={
                "secrets": [
                    {
                        "secretKey": "BINANCE_API_KEY",
                        "secretValue": "secret-value",
                        "secretPath": "/",
                    }
                ]
            },
        )

    client = make_client(httpx.MockTransport(handler))

    secrets = client.list_secrets()

    assert secrets == {
        "BINANCE_API_KEY": SecretValue(
            key="BINANCE_API_KEY",
            value="secret-value",
            path="/",
        )
    }


def test_secret_repr_masks_value() -> None:
    """Secret repr must not expose the raw value."""
    secret = SecretValue(key="API_KEY", value="raw-secret")

    assert "raw-secret" not in repr(secret)
    assert "***" in repr(secret)


def test_load_required_reports_missing_secret() -> None:
    """Missing required secret should fail loudly."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/login"):
            return httpx.Response(200, json={"accessToken": "token"})
        return httpx.Response(200, json={"secrets": []})

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(InfisicalError, match="BINANCE_API_KEY"):
        client.load_required(["BINANCE_API_KEY"])


def test_http_errors_are_wrapped_without_secret_values() -> None:
    """HTTP errors should be domain errors and avoid leaking credentials."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "nope"})

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(InfisicalError) as exc_info:
        client.login()

    message = str(exc_info.value)
    assert "HTTP 401" in message
    assert "client-secret" not in message
