"""Smoke-test operational ApeRAG agent memory through MemoryAgentService."""

from __future__ import annotations

import os
import sys
import time
from argparse import ArgumentParser
from pathlib import Path

from rich.console import Console
from rich.table import Table

from stat_arb.memory import (
    ApeRAGConfig,
    ApeRAGMemoryClient,
    MemoryAgentService,
    MemoryRecordType,
    MemoryWriteRequest,
)

console = Console()


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE env file entries into the current process."""
    if not path.exists():
        raise FileNotFoundError(f"ApeRAG env file не найден: {path}")
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ[key.strip()] = value.strip()


def wait_for_document_ready(
    client: ApeRAGMemoryClient,
    *,
    collection_id: str,
    document_id: str,
    timeout_seconds: int,
) -> bool:
    """Wait until one uploaded document has active vector and full-text indexes."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        docs = client.list_documents(collection_id)
        for doc in docs:
            if doc.id == document_id and doc.is_ready:
                return True
        time.sleep(2)
    return False


def smoke_aperag_agent_memory(
    *,
    env_file: Path,
    collection_title: str,
    timeout_seconds: int,
) -> int:
    """Create/check operational memory collection and run one policy-controlled write."""
    load_env_file(env_file)
    config = ApeRAGConfig(
        api_base_url=os.environ.get("APERAG_API_BASE_URL", "http://127.0.0.1:18000"),
        api_key=os.environ.get("APERAG_API_KEY", ""),
        agent_collection_title=collection_title,
    )

    with ApeRAGMemoryClient(config) as client:
        collection = client.ensure_collection(
            title=collection_title,
            description="Operational agent memory for Statistical Arbitrage runtime lessons.",
        )

        smoke_filename = "lesson-stat-arb-agent-memory-smoke.md"
        for doc in client.list_documents(collection.id):
            if doc.name == smoke_filename:
                client.delete_document(collection_id=collection.id, document_id=doc.id)

        service = MemoryAgentService(client, collection_title=collection_title)
        result = service.write(
            MemoryWriteRequest(
                record_type=MemoryRecordType.LESSON,
                title="ApeRAG agent memory smoke",
                body=(
                    "Operational agent memory accepts concise policy-approved lessons. "
                    "Raw logs, secrets, prompts, and metric-heavy payloads stay out."
                ),
                source_id="stat-arb-agent-memory-smoke",
                registry_reference="registry:smoke/agent-memory",
                tags=["smoke", "agent-memory", "aperag"],
                metadata={"scope": "operational-agent-memory"},
            )
        )

        document_id = result.document_ids[0]
        if not wait_for_document_ready(
            client,
            collection_id=collection.id,
            document_id=document_id,
            timeout_seconds=timeout_seconds,
        ):
            console.print("[red]Agent memory smoke document не дождался active indexes.[/red]")
            return 1

        search_results = client.search(
            "policy-approved operational agent memory lessons",
            collection_id=collection.id,
            keywords=["agent", "memory", "policy"],
            top_k=3,
        )
        if not search_results:
            console.print("[red]Agent memory smoke search не вернул results.[/red]")
            return 1

    table = Table(title="Проверка ApeRAG Agent Memory")
    table.add_column("Проверка", style="cyan")
    table.add_column("Результат", style="green")
    table.add_row("Collection", collection_title)
    table.add_row("Document", smoke_filename)
    table.add_row("Путь записи", "MemoryAgentService")
    table.add_row("Индексы", "ACTIVE")
    table.add_row("Поиск", f"OK, results={len(search_results)}")
    console.print(table)
    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = ArgumentParser(description="Smoke-test ApeRAG operational agent memory.")
    parser.add_argument("--env-file", default="data/aperag/.env")
    parser.add_argument("--collection-title", default="stat-arb-agent-memory")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    args = parser.parse_args()

    sys.exit(
        smoke_aperag_agent_memory(
            env_file=Path(args.env_file),
            collection_title=args.collection_title,
            timeout_seconds=args.timeout_seconds,
        )
    )


if __name__ == "__main__":
    main()
