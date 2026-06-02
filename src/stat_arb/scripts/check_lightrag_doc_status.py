"""Check persistent LightRAG document processing status."""

from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from stat_arb.scripts.seed_lightrag import repo_root_from

console = Console()


@dataclass(frozen=True)
class DocStatusSummary:
    """Summary of LightRAG document status records."""

    processed: int
    pending: int
    processing: int
    failed: int
    duplicate_failed: int
    real_failed: int
    unknown: int
    total: int


def _is_duplicate_failure(record_id: str, record: dict[str, Any]) -> bool:
    summary = str(record.get("content_summary", ""))
    return record_id.startswith("dup-") and summary.startswith("[DUPLICATE]")


def summarize_doc_status(records: dict[str, Any]) -> DocStatusSummary:
    """Summarize LightRAG doc_status records and separate duplicate failures."""
    processed = 0
    pending = 0
    processing = 0
    failed = 0
    duplicate_failed = 0
    real_failed = 0
    unknown = 0

    for record_id, raw_record in records.items():
        record = raw_record if isinstance(raw_record, dict) else {}
        status = str(record.get("status", "")).lower()
        if status == "processed":
            processed += 1
        elif status == "pending":
            pending += 1
        elif status == "processing":
            processing += 1
        elif status == "failed":
            failed += 1
            if _is_duplicate_failure(record_id, record):
                duplicate_failed += 1
            else:
                real_failed += 1
        else:
            unknown += 1

    return DocStatusSummary(
        processed=processed,
        pending=pending,
        processing=processing,
        failed=failed,
        duplicate_failed=duplicate_failed,
        real_failed=real_failed,
        unknown=unknown,
        total=len(records),
    )


def load_doc_status(path: Path) -> dict[str, Any]:
    """Load a LightRAG doc_status JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def check_lightrag_doc_status(
    repo_root: Path | None = None,
    status_path: Path | None = None,
    allow_missing: bool = False,
) -> int:
    """Check persistent LightRAG doc_status for real failures."""
    root = repo_root_from(repo_root)
    path = status_path or root / "data" / "lightrag" / "kv_store_doc_status.json"

    if not path.exists():
        message = f"LightRAG doc_status file not found: {path}"
        if allow_missing:
            console.print(f"[yellow]{message}[/yellow]")
            return 0
        console.print(f"[red]{message}[/red]")
        return 1

    summary = summarize_doc_status(load_doc_status(path))

    table = Table(title="LightRAG Persistent Doc Status")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", style="green")
    table.add_row("Total", str(summary.total))
    table.add_row("Processed", str(summary.processed))
    table.add_row("Pending", str(summary.pending))
    table.add_row("Processing", str(summary.processing))
    table.add_row("Failed", str(summary.failed))
    table.add_row("Duplicate Failed", str(summary.duplicate_failed))
    table.add_row("Real Failed", str(summary.real_failed))
    table.add_row("Unknown", str(summary.unknown))
    console.print(table)

    if summary.real_failed > 0 or summary.pending > 0 or summary.processing > 0 or summary.unknown > 0:
        console.print("[red]LightRAG persistent doc_status has unresolved records.[/red]")
        return 1

    console.print("[green]LightRAG persistent doc_status passed.[/green]")
    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = ArgumentParser(description="Check persistent LightRAG doc_status records.")
    parser.add_argument(
        "--status-path",
        type=Path,
        default=None,
        help="Path to kv_store_doc_status.json. Defaults to data/lightrag.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Return success when persistent LightRAG storage is not initialized yet.",
    )
    args = parser.parse_args()
    sys.exit(
        check_lightrag_doc_status(
            status_path=args.status_path,
            allow_missing=args.allow_missing,
        )
    )


if __name__ == "__main__":
    main()
