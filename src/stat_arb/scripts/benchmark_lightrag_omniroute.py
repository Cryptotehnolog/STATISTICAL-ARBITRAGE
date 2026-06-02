"""Benchmark LightRAG graph extraction through OmniRoute models."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from argparse import ArgumentParser
from dataclasses import asdict, dataclass
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

DEFAULT_MODELS = (
    "kiro/deepseek-3.2",
    "kiro/qwen3-coder-next",
    "kiro/glm-5",
    "kiro/claude-sonnet-4.5",
    "kiro/minimax-m2.5",
)


@dataclass(frozen=True)
class BenchmarkResult:
    """One LightRAG extraction benchmark result."""

    model: str
    status: str
    elapsed_seconds: float
    nodes: int
    edges: int
    error: str


def rank_results(results: list[BenchmarkResult]) -> list[BenchmarkResult]:
    """Rank successful models by graph quality first, then latency."""
    return sorted(
        results,
        key=lambda result: (
            result.status != "passed",
            -result.edges,
            -result.nodes,
            result.elapsed_seconds,
            result.model,
        ),
    )


def benchmark_one_model(
    *,
    model: str,
    base_url: str,
    api_key: str,
    timeout: float,
    benchmark_root: Path,
    keep_data: bool,
) -> BenchmarkResult:
    """Run one isolated LightRAG extraction benchmark."""
    run_root = benchmark_root / f"{model.replace('/', '_')}-{uuid4().hex[:8]}"
    storage_path = run_root / "lightrag"
    vector_store_path = run_root / "vector_store"
    started_at = perf_counter()

    try:
        config = LightRAGConfig(
            storage_path=storage_path,
            vector_store_path=vector_store_path,
            vector_store="nano",
            embedding_local_files_only=True,
            llm_provider="openai_compatible",
            openai_compatible_model=model,
            openai_compatible_base_url=base_url,
            openai_compatible_api_key=api_key,
            openai_compatible_timeout=timeout,
            chunk_size=256,
            chunk_overlap=20,
            batch_size=8,
            max_workers=1,
        )
        client = LightRAGClient(config)
        health = client.health_check(check_embedding=True)
        if health.get("status") != "healthy":
            elapsed = perf_counter() - started_at
            return BenchmarkResult(
                model=model,
                status="failed",
                elapsed_seconds=elapsed,
                nodes=0,
                edges=0,
                error=f"Embedding preflight failed: {health}",
            )

        client.rag.insert(
            SMOKE_DOCUMENT,
            ids=f"benchmark-{model.replace('/', '-')}-{uuid4().hex[:8]}",
        )
        stats = count_graphml(storage_path / "graph_chunk_entity_relation.graphml")
        elapsed = perf_counter() - started_at
        status = "passed" if stats.nodes > 0 else "failed"
        error = "" if status == "passed" else "No graph nodes extracted."
        return BenchmarkResult(
            model=model,
            status=status,
            elapsed_seconds=elapsed,
            nodes=stats.nodes,
            edges=stats.edges,
            error=error,
        )
    except Exception as exc:  # noqa: BLE001 - benchmark must continue after one model fails.
        elapsed = perf_counter() - started_at
        return BenchmarkResult(
            model=model,
            status="failed",
            elapsed_seconds=elapsed,
            nodes=0,
            edges=0,
            error=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if not keep_data:
            safe_rmtree(run_root)


def render_results(results: list[BenchmarkResult]) -> None:
    """Render benchmark results and recommended ordering."""
    table = Table(title="LightRAG OmniRoute Benchmark")
    table.add_column("Rank", style="cyan")
    table.add_column("Model", style="green")
    table.add_column("Status")
    table.add_column("Seconds", justify="right")
    table.add_column("Узлы", justify="right")
    table.add_column("Связи", justify="right")
    table.add_column("Error", overflow="fold")

    ranked = rank_results(results)
    for index, result in enumerate(ranked, start=1):
        table.add_row(
            str(index),
            result.model,
            result.status,
            f"{result.elapsed_seconds:.2f}",
            str(result.nodes),
            str(result.edges),
            result.error,
        )
    console.print(table)

    recommended = [result.model for result in ranked if result.status == "passed"]
    if recommended:
        console.print("[green]Recommended combo order:[/green]")
        for model in recommended:
            console.print(f"  - {model}")
    else:
        console.print("[red]No models passed LightRAG graph extraction.[/red]")


def benchmark_lightrag_omniroute(
    models: list[str],
    base_url: str = "http://localhost:20128/v1",
    api_key: str = "",
    timeout: float = 180.0,
    keep_data: bool = False,
    repo_root: Path | None = None,
) -> int:
    """Run the LightRAG graph extraction benchmark for multiple models."""
    root = repo_root_from(repo_root)
    output_root = root / "data" / "omniroute_lightrag_benchmark"
    benchmark_root = output_root / f"run-{uuid4().hex[:12]}"
    results: list[BenchmarkResult] = []

    for model in models:
        console.print(f"[yellow]Benchmarking {model}...[/yellow]")
        result_path = benchmark_root / f"{model.replace('/', '_')}-{uuid4().hex[:8]}.json"
        command = [
            sys.executable,
            "-m",
            "stat_arb.scripts.benchmark_lightrag_omniroute",
            "--single-model",
            model,
            "--base-url",
            base_url,
            "--timeout",
            str(timeout),
            "--result-file",
            str(result_path),
            "--benchmark-root",
            str(benchmark_root),
        ]
        if api_key:
            command.extend(["--api-key", api_key])
        if keep_data:
            command.append("--keep-data")

        completed = subprocess.run(  # noqa: S603 - argv is constructed without a shell.
            command,
            check=False,
            cwd=root,
        )
        if result_path.exists():
            result = BenchmarkResult(**json.loads(result_path.read_text(encoding="utf-8")))
        else:
            result = BenchmarkResult(
                model=model,
                status="failed",
                elapsed_seconds=0.0,
                nodes=0,
                edges=0,
                error=f"Subprocess exited {completed.returncode} without a result file.",
            )
        results.append(result)

    render_results(results)

    output_path = output_root / "results_latest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([asdict(result) for result in rank_results(results)], indent=2) + "\n",
        encoding="utf-8",
    )
    console.print(f"[cyan]Results JSON:[/cyan] {output_path}")

    if not keep_data:
        safe_rmtree(benchmark_root)

    return 0 if any(result.status == "passed" for result in results) else 1


def run_single_model_from_cli(
    *,
    model: str,
    base_url: str,
    api_key: str,
    timeout: float,
    benchmark_root: Path,
    result_file: Path,
    keep_data: bool,
) -> int:
    """Run one benchmark in a fresh process and write the result as JSON."""
    result = benchmark_one_model(
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
        benchmark_root=benchmark_root,
        keep_data=keep_data,
    )
    result_file.parent.mkdir(parents=True, exist_ok=True)
    result_file.write_text(json.dumps(asdict(result), indent=2) + "\n", encoding="utf-8")
    return 0 if result.status == "passed" else 1


def main() -> None:
    """CLI entrypoint."""
    parser = ArgumentParser(description="Benchmark LightRAG graph extraction via OmniRoute.")
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Model to benchmark. Repeat to benchmark multiple models.",
    )
    parser.add_argument(
        "--single-model",
        help="Internal mode: benchmark one model in this process.",
    )
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
        help="Keep isolated benchmark runtime data under data/omniroute_lightrag_benchmark.",
    )
    parser.add_argument(
        "--benchmark-root",
        type=Path,
        help="Internal mode: benchmark runtime root.",
    )
    parser.add_argument(
        "--result-file",
        type=Path,
        help="Internal mode: write one BenchmarkResult JSON file.",
    )
    parser.add_argument(
        "--show-tracebacks",
        action="store_true",
        help="Print traceback details after failed model runs.",
    )
    args = parser.parse_args()
    if args.single_model:
        if args.benchmark_root is None or args.result_file is None:
            parser.error("--single-model requires --benchmark-root and --result-file")
        sys.exit(
            run_single_model_from_cli(
                model=args.single_model,
                base_url=args.base_url,
                api_key=args.api_key,
                timeout=args.timeout,
                benchmark_root=args.benchmark_root,
                result_file=args.result_file,
                keep_data=args.keep_data,
            )
        )

    models = args.models or list(DEFAULT_MODELS)
    try:
        sys.exit(
            benchmark_lightrag_omniroute(
                models=models,
                base_url=args.base_url,
                api_key=args.api_key,
                timeout=args.timeout,
                keep_data=args.keep_data,
            )
        )
    except Exception:  # noqa: BLE001 - CLI should optionally print debugging details.
        if args.show_tracebacks:
            traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
