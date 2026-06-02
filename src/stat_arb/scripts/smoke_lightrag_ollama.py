"""Smoke-test LightRAG graph extraction with a local Ollama model.

This script uses an isolated runtime directory and a tiny document so the test
does not mutate the main project knowledge base.
"""

from __future__ import annotations

import shutil
import sys
import xml.etree.ElementTree as ET
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from rich.console import Console
from rich.table import Table

from stat_arb.memory.config import LightRAGConfig
from stat_arb.memory.lightrag_client import LightRAGClient
from stat_arb.scripts.seed_lightrag import repo_root_from

console = Console()

SMOKE_DOCUMENT = """
The Data Agent validates OHLCV candles for the Statistical Arbitrage project.
The Statistical Testing Agent runs Engle-Granger tests on asset pairs.
The Critic Agent reviews lookahead bias before a strategy is approved.
LightRAG stores the relation between agents, tests, risks, and decisions.
"""


@dataclass(frozen=True)
class GraphStats:
    """GraphML node and edge counts."""

    nodes: int
    edges: int


def count_graphml(path: Path) -> GraphStats:
    """Count nodes and edges in a GraphML file."""
    if not path.exists():
        return GraphStats(nodes=0, edges=0)

    root = ET.parse(path).getroot()
    nodes = 0
    edges = 0
    for element in root.iter():
        tag = element.tag.rsplit("}", maxsplit=1)[-1]
        if tag == "node":
            nodes += 1
        elif tag == "edge":
            edges += 1
    return GraphStats(nodes=nodes, edges=edges)


def safe_rmtree(path: Path) -> None:
    """Remove runtime data without failing the smoke on Windows file locks."""
    shutil.rmtree(path, ignore_errors=True)


def smoke_lightrag_ollama(
    model: str = "qwen2.5:3b",
    timeout: float = 600.0,
    keep_data: bool = False,
    repo_root: Path | None = None,
) -> int:
    """Run an isolated LightRAG insert and verify graph extraction."""
    root = repo_root_from(repo_root)
    smoke_root = root / "data" / "ollama_lightrag_smoke" / f"run-{uuid4().hex[:12]}"
    storage_path = smoke_root / "lightrag"
    vector_store_path = smoke_root / "vector_store"

    config = LightRAGConfig(
        storage_path=storage_path,
        vector_store_path=vector_store_path,
        vector_store="nano",
        embedding_local_files_only=True,
        llm_provider="ollama",
        ollama_model=model,
        ollama_timeout=timeout,
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

    console.print(f"[yellow]Running LightRAG Ollama smoke with {model}...[/yellow]")
    client.insert(SMOKE_DOCUMENT, metadata={"type": "ollama_graph_smoke"})

    graph_path = storage_path / "graph_chunk_entity_relation.graphml"
    stats = count_graphml(graph_path)

    table = Table(title="LightRAG Ollama Smoke")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Model", model)
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

    console.print("[green]LightRAG Ollama graph smoke passed.[/green]")
    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = ArgumentParser(description="Smoke-test LightRAG graph extraction with Ollama.")
    parser.add_argument("--model", default="qwen2.5:3b", help="Ollama model to test.")
    parser.add_argument(
        "--timeout",
        type=float,
        default=600.0,
        help="Per-request Ollama timeout in seconds.",
    )
    parser.add_argument(
        "--keep-data",
        action="store_true",
        help="Keep isolated smoke runtime data under data/ollama_lightrag_smoke.",
    )
    args = parser.parse_args()
    sys.exit(
        smoke_lightrag_ollama(
            model=args.model,
            timeout=args.timeout,
            keep_data=args.keep_data,
        )
    )


if __name__ == "__main__":
    main()
