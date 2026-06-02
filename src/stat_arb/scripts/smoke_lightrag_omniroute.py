"""Smoke-test LightRAG graph extraction through OmniRoute.

This script uses the generic OpenAI-compatible provider pointed at the local
OmniRoute Docker gateway. Runtime data is isolated from the main knowledge base.
"""

from __future__ import annotations

import os
import sys
from argparse import ArgumentParser
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from rich.console import Console
from rich.table import Table

from stat_arb.memory.config import LightRAGConfig
from stat_arb.memory.lightrag_client import LightRAGClient
from stat_arb.scripts.lightrag_smoke_common import SMOKE_DOCUMENT, count_graphml, safe_rmtree
from stat_arb.scripts.seed_lightrag import repo_root_from

console = Console()


def smoke_lightrag_omniroute(
    model: str = "my-ai",
    base_url: str = "http://localhost:20128/v1",
    api_key: str | None = None,
    timeout: float = 180.0,
    keep_data: bool = False,
    repo_root: Path | None = None,
) -> int:
    """Run an isolated LightRAG insert through OmniRoute and verify extraction."""
    root = repo_root_from(repo_root)
    smoke_root = root / "data" / "omniroute_lightrag_smoke" / f"run-{uuid4().hex[:12]}"
    storage_path = smoke_root / "lightrag"
    vector_store_path = smoke_root / "vector_store"

    config = LightRAGConfig(
        storage_path=storage_path,
        vector_store_path=vector_store_path,
        vector_store="nano",
        embedding_local_files_only=True,
        llm_provider="openai_compatible",
        openai_compatible_model=model,
        openai_compatible_base_url=base_url,
        openai_compatible_api_key=api_key or "",
        openai_compatible_timeout=timeout,
        chunk_size=256,
        chunk_overlap=20,
        batch_size=8,
        max_workers=1,
    )
    client = LightRAGClient(config)

    health = client.health_check(check_embedding=True)
    if health.get("status") != "healthy":
        console.print(f"[red]Embedding preflight failed:[/red] {health}")
        return 1

    console.print(f"[yellow]Running LightRAG OmniRoute smoke with {model}...[/yellow]")
    started_at = perf_counter()
    client.insert(SMOKE_DOCUMENT, metadata={"type": "omniroute_graph_smoke"})
    elapsed_seconds = perf_counter() - started_at

    graph_path = storage_path / "graph_chunk_entity_relation.graphml"
    stats = count_graphml(graph_path)

    table = Table(title="LightRAG OmniRoute Smoke")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Model", model)
    table.add_row("Base URL", base_url)
    table.add_row("Elapsed Seconds", f"{elapsed_seconds:.2f}")
    table.add_row("Graph Path", str(graph_path))
    table.add_row("Nodes", str(stats.nodes))
    table.add_row("Edges", str(stats.edges))
    table.add_row("Smoke Data", str(smoke_root))
    console.print(table)

    if not keep_data:
        safe_rmtree(smoke_root)

    if stats.nodes <= 0:
        console.print("[red]No graph nodes extracted.[/red]")
        return 1

    console.print("[green]LightRAG OmniRoute graph smoke passed.[/green]")
    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = ArgumentParser(description="Smoke-test LightRAG graph extraction with OmniRoute.")
    parser.add_argument("--model", default="my-ai", help="OmniRoute combo or model to test.")
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
    parser.add_argument(
        "--keep-data",
        action="store_true",
        help="Keep isolated smoke runtime data under data/omniroute_lightrag_smoke.",
    )
    args = parser.parse_args()
    sys.exit(
        smoke_lightrag_omniroute(
            model=args.model,
            base_url=args.base_url,
            api_key=args.api_key,
            timeout=args.timeout,
            keep_data=args.keep_data,
        )
    )


if __name__ == "__main__":
    main()
