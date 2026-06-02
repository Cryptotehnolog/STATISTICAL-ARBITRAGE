"""Unit tests for the Ollama LightRAG smoke helpers."""

import shutil
from pathlib import Path
from uuid import uuid4

from stat_arb.scripts.smoke_lightrag_ollama import GraphStats, count_graphml


def _test_dir(name: str) -> Path:
    path = (Path("data/test_tmp") / f"{name}-{uuid4()}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_count_graphml_returns_zero_for_missing_file() -> None:
    """Missing graph files should count as empty graphs."""
    test_dir = _test_dir("graph-missing")
    try:
        assert count_graphml(test_dir / "missing.graphml") == GraphStats(
            nodes=0,
            edges=0,
        )
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


def test_count_graphml_counts_namespaced_nodes_and_edges() -> None:
    """GraphML counting should handle namespaced files."""
    test_dir = _test_dir("graph-count")
    try:
        graphml = test_dir / "graph.graphml"
        graphml.write_text(
            """<?xml version="1.0" encoding="utf-8"?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <graph edgedefault="undirected">
    <node id="Data Agent" />
    <node id="Critic Agent" />
    <edge source="Data Agent" target="Critic Agent" />
  </graph>
</graphml>
""",
            encoding="utf-8",
        )

        assert count_graphml(graphml) == GraphStats(nodes=2, edges=1)
    finally:
        shutil.rmtree(test_dir, ignore_errors=True)
