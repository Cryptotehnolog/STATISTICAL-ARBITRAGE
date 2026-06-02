"""Shared helpers for LightRAG graph extraction smoke tests."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

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
