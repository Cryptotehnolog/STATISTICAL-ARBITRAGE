"""Check Infisical Universal Auth and runtime secret reads."""

from __future__ import annotations

import sys
from argparse import ArgumentParser

from rich.console import Console
from rich.table import Table

from stat_arb.secrets.config import InfisicalConfig
from stat_arb.secrets.infisical_client import InfisicalClient, InfisicalError

console = Console()

DEFAULT_SECRET_KEY = "STAT_ARB_INFISICAL_SMOKE_SECRET"


def check_infisical_auth(
    *,
    secret_key: str = DEFAULT_SECRET_KEY,
    api_url: str | None = None,
    environment: str | None = None,
    secret_path: str | None = None,
) -> int:
    """Check Universal Auth login and read one test secret without printing its value."""
    config = InfisicalConfig()
    if api_url:
        config.api_url = api_url
    if environment:
        config.environment = environment
    if secret_path:
        config.secret_path = secret_path

    try:
        config.validate_for_runtime()
        with InfisicalClient(config) as client:
            token = client.login()
            secret = client.get_secret(secret_key)
    except (InfisicalError, ValueError) as exc:
        console.print(f"[red]Проверка Infisical auth не прошла:[/red] {exc}")
        return 1

    if not token:
        console.print("[red]Infisical Universal Auth не вернул access token.[/red]")
        return 1
    if not secret.value:
        console.print(f"[red]Secret '{secret_key}' найден, но значение пустое.[/red]")
        return 1

    table = Table(title="Проверка Infisical Auth")
    table.add_column("Проверка", style="cyan")
    table.add_column("Результат", style="green")
    table.add_row("API URL", config.normalized_api_url)
    table.add_row("Environment", config.environment)
    table.add_row("Secret path", config.secret_path)
    table.add_row("Secret key", secret.key)
    table.add_row("Universal Auth", "OK")
    table.add_row("Secret read", "OK, значение скрыто")
    console.print(table)
    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = ArgumentParser(
        description="Check Infisical Universal Auth and read one smoke-test secret."
    )
    parser.add_argument(
        "--secret-key",
        default=DEFAULT_SECRET_KEY,
        help="Secret key to read from Infisical. The value is never printed.",
    )
    parser.add_argument("--api-url", default="", help="Override INFISICAL_API_URL.")
    parser.add_argument("--environment", default="", help="Override INFISICAL_ENVIRONMENT.")
    parser.add_argument("--secret-path", default="", help="Override INFISICAL_SECRET_PATH.")
    args = parser.parse_args()
    sys.exit(
        check_infisical_auth(
            secret_key=args.secret_key,
            api_url=args.api_url or None,
            environment=args.environment or None,
            secret_path=args.secret_path or None,
        )
    )


if __name__ == "__main__":
    main()
