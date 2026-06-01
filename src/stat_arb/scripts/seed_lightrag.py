"""Seed LightRAG with curated project knowledge sources.

This entrypoint gathers committed project documentation and planning sources,
hashes their content, and inserts only changed documents into LightRAG.

Usage:
    uv run python -m stat_arb.scripts.seed_lightrag
    uv run python -m stat_arb.scripts.seed_lightrag --dry-run
"""

from __future__ import annotations

import json
import logging
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from stat_arb.memory.config import LightRAGConfig
from stat_arb.memory.lightrag_client import LightRAGClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
console = Console()

DEFAULT_SOURCE_PATTERNS = (
    "README.md",
    "docs/**/*.md",
    ".kiro/specs/**/*.md",
)

SKIP_PARTS = {
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "data",
    "htmlcov",
}


@dataclass(frozen=True)
class KnowledgeDocument:
    """A source document prepared for LightRAG insertion."""

    path: Path
    source_id: str
    title: str
    content: str
    content_hash: str


def repo_root_from(start: Path | None = None) -> Path:
    """Find the repository root by walking up to pyproject.toml."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    msg = f"Could not find repository root from {current}"
    raise RuntimeError(msg)


def _is_allowed_source(path: Path, repo_root: Path) -> bool:
    relative = path.relative_to(repo_root)
    if any(part in SKIP_PARTS for part in relative.parts):
        return False
    return path.is_file() and path.suffix.lower() == ".md"


def discover_source_paths(
    repo_root: Path,
    patterns: tuple[str, ...] = DEFAULT_SOURCE_PATTERNS,
) -> list[Path]:
    """Discover markdown sources that should be seeded into LightRAG."""
    paths: set[Path] = set()
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if _is_allowed_source(path, repo_root):
                paths.add(path.resolve())
    return sorted(paths)


def _title_from_markdown(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped.removeprefix("# ").strip()
    return fallback


def load_document(path: Path, repo_root: Path) -> KnowledgeDocument:
    """Load and hash one source document."""
    relative = path.relative_to(repo_root).as_posix()
    content = path.read_text(encoding="utf-8")
    content_hash = sha256(content.encode("utf-8")).hexdigest()
    return KnowledgeDocument(
        path=path,
        source_id=relative,
        title=_title_from_markdown(content, relative),
        content=content,
        content_hash=content_hash,
    )


def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load the seed manifest if it exists."""
    if not manifest_path.exists():
        return {"version": 1, "documents": {}}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def save_manifest(manifest_path: Path, manifest: dict[str, Any]) -> None:
    """Persist the seed manifest under ignored runtime data."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def changed_documents(
    documents: list[KnowledgeDocument],
    manifest: dict[str, Any],
) -> list[KnowledgeDocument]:
    """Return documents whose content hash differs from the manifest."""
    known_documents = manifest.get("documents", {})
    return [
        document
        for document in documents
        if known_documents.get(document.source_id, {}).get("hash") != document.content_hash
    ]


def render_document_for_lightrag(document: KnowledgeDocument) -> str:
    """Wrap source content with stable metadata for retrieval."""
    return "\n".join(
        [
            f"PROJECT KNOWLEDGE SOURCE: {document.source_id}",
            f"TITLE: {document.title}",
            "",
            document.content,
        ]
    )


def seed_lightrag(
    dry_run: bool = False,
    repo_root: Path | None = None,
    allow_model_download: bool = False,
    vector_store: str = "nano",
) -> int:
    """Seed changed project knowledge documents into LightRAG."""
    root = repo_root_from(repo_root)
    config = LightRAGConfig(
        embedding_local_files_only=not allow_model_download,
        vector_store=vector_store,
    )
    manifest_path = root / "data" / "lightrag_seed_manifest.json"
    documents = [load_document(path, root) for path in discover_source_paths(root)]
    manifest = load_manifest(manifest_path)
    to_seed = changed_documents(documents, manifest)

    table = Table(title="LightRAG Knowledge Seed")
    table.add_column("Source", style="cyan")
    table.add_column("Status", style="green")
    for document in documents:
        status = "changed" if document in to_seed else "unchanged"
        table.add_row(document.source_id, status)
    console.print(table)

    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] {len(to_seed)} changed document(s).")
        return 0

    if not to_seed:
        console.print("[green]Knowledge base is already up to date.[/green]")
        return 0

    client = LightRAGClient(config)
    health = client.health_check(check_embedding=True)
    if health.get("status") != "healthy":
        msg = (
            "LightRAG embedding preflight failed. "
            "Install/cache the embedding model before seeding."
        )
        raise RuntimeError(msg)

    for document in to_seed:
        client.insert(
            render_document_for_lightrag(document),
            metadata={
                "type": "project_knowledge",
                "source_id": document.source_id,
                "title": document.title,
                "content_hash": document.content_hash,
            },
        )
        manifest.setdefault("documents", {})[document.source_id] = {
            "hash": document.content_hash,
            "title": document.title,
            "seeded_at": datetime.now(UTC).isoformat(),
        }
        logger.info("Seeded LightRAG knowledge source %s", document.source_id)

    save_manifest(manifest_path, manifest)
    console.print(f"[green]Seeded {len(to_seed)} changed document(s).[/green]")
    return 0


def main() -> None:
    """CLI entrypoint."""
    parser = ArgumentParser(description="Seed LightRAG with curated project knowledge.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List changed sources without writing to LightRAG or the manifest.",
    )
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Allow downloading the embedding model if it is not already cached.",
    )
    parser.add_argument(
        "--vector-store",
        choices=("nano", "faiss"),
        default="nano",
        help="Embedded vector store for knowledge seeding. Defaults to nano on Windows.",
    )
    args = parser.parse_args()
    sys.exit(
        seed_lightrag(
            dry_run=args.dry_run,
            allow_model_download=args.allow_model_download,
            vector_store=args.vector_store,
        )
    )


if __name__ == "__main__":
    main()
