"""Smoke-query the curated persistent LightRAG knowledge base."""

from __future__ import annotations

import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from rich.console import Console
from rich.table import Table

from stat_arb.memory.config import LightRAGConfig
from stat_arb.memory.lightrag_client import LightRAGClient
from stat_arb.scripts.seed_lightrag import repo_root_from

console = Console()

DEFAULT_QUERY = (
    "According to the project knowledge, what is the active LightRAG LLM gateway "
    "and what documents should regular curated seeding use?"
)
DEFAULT_EXPECTED_TERMS = ("OmniRoute", "docs/knowledge")


def query_lightrag_curated(
    query: str = DEFAULT_QUERY,
    expected_terms: tuple[str, ...] = DEFAULT_EXPECTED_TERMS,
    model: str = "my-ai",
    base_url: str = "http://localhost:20128/v1",
    api_key: str | None = None,
    timeout: float = 180.0,
    repo_root: Path | None = None,
) -> int:
    """Run a deterministic-ish query against persistent curated LightRAG memory."""
    root = repo_root_from(repo_root)
    config = LightRAGConfig(
        storage_path=root / "data" / "lightrag",
        vector_store_path=root / "data" / "vector_store",
        vector_store="nano",
        embedding_local_files_only=True,
        llm_provider="openai_compatible",
        openai_compatible_model=model,
        openai_compatible_base_url=base_url,
        openai_compatible_api_key=api_key or "",
        openai_compatible_timeout=timeout,
        max_workers=1,
    )
    client = LightRAGClient(config)

    health = client.health_check(check_embedding=True)
    if health.get("status") != "healthy":
        console.print(f"[red]Embedding preflight failed:[/red] {health}")
        return 1

    answer = client.query(query, mode="hybrid", top_k=5)
    answer_lower = answer.lower()
    missing_terms = [term for term in expected_terms if term.lower() not in answer_lower]

    table = Table(title="LightRAG Curated Query Smoke")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Model", model)
    table.add_row("Base URL", base_url)
    table.add_row("Query", query)
    table.add_row("Expected Terms", ", ".join(expected_terms))
    table.add_row("Missing Terms", ", ".join(missing_terms) if missing_terms else "none")
    console.print(table)
    console.print(answer)

    if missing_terms:
        console.print("[red]LightRAG curated query smoke failed.[/red]")
        return 1

    console.print("[green]LightRAG curated query smoke passed.[/green]")
    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = ArgumentParser(description="Smoke-query persistent curated LightRAG memory.")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Query to ask LightRAG.")
    parser.add_argument(
        "--expect",
        action="append",
        dest="expected_terms",
        help="Term that must appear in the answer. Can be passed multiple times.",
    )
    parser.add_argument("--model", default="my-ai", help="OmniRoute combo or model to use.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:20128/v1",
        help="OpenAI-compatible base URL exposed by OmniRoute.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("OMNIROUTE_API_KEY", ""),
        help="OmniRoute endpoint API key. Defaults to OMNIROUTE_API_KEY.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Per-request OmniRoute timeout in seconds.",
    )
    args = parser.parse_args()
    sys.exit(
        query_lightrag_curated(
            query=args.query,
            expected_terms=tuple(args.expected_terms or DEFAULT_EXPECTED_TERMS),
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            timeout=args.timeout,
        )
    )


if __name__ == "__main__":
    main()
