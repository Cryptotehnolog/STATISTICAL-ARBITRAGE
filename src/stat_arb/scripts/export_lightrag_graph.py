"""Export persistent LightRAG GraphML to a local HTML knowledge graph viewer."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from stat_arb.scripts.seed_lightrag import repo_root_from

console = Console()
GRAPHML_NS = {"g": "http://graphml.graphdrawing.org/xmlns"}
SEPARATOR = "<SEP>"


@dataclass(frozen=True)
class GraphExport:
    """Exported graph payload."""

    payload: dict[str, Any]
    output_dir: Path
    json_path: Path
    html_path: Path


def _split_values(value: str) -> list[str]:
    return [item.strip() for item in value.split(SEPARATOR) if item.strip()]


def _parse_graphml_data(element: ET.Element, key_names: dict[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for data in element.findall("g:data", GRAPHML_NS):
        key = data.attrib.get("key", "")
        name = key_names.get(key, key)
        values[name] = data.text or ""
    return values


def _coerce_float(value: str, default: float = 1.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_lightrag_graphml(graphml_path: Path) -> dict[str, Any]:
    """Parse LightRAG GraphML into a viewer-friendly JSON payload."""
    tree = ET.parse(graphml_path)
    root = tree.getroot()

    key_names: dict[str, str] = {}
    for key in root.findall("g:key", GRAPHML_NS):
        key_id = key.attrib.get("id")
        attr_name = key.attrib.get("attr.name")
        if key_id and attr_name:
            key_names[key_id] = attr_name

    graph = root.find("g:graph", GRAPHML_NS)
    if graph is None:
        msg = f"No graph element found in {graphml_path}"
        raise ValueError(msg)

    nodes: list[dict[str, Any]] = []
    node_by_id: dict[str, dict[str, Any]] = {}
    for node in graph.findall("g:node", GRAPHML_NS):
        node_id = node.attrib["id"]
        data = _parse_graphml_data(node, key_names)
        description = data.get("description", "")
        source_chunks = _split_values(data.get("source_id", ""))
        node_payload: dict[str, Any] = {
            "id": node_id,
            "label": data.get("entity_id") or node_id,
            "type": data.get("entity_type") or "unknown",
            "description": description,
            "source_chunks": source_chunks,
            "source_count": len(source_chunks),
            "file_path": data.get("file_path", ""),
            "created_at": data.get("created_at", ""),
            "degree": 0,
            "weighted_degree": 0.0,
        }
        nodes.append(node_payload)
        node_by_id[node_id] = node_payload

    edges: list[dict[str, Any]] = []
    for index, edge in enumerate(graph.findall("g:edge", GRAPHML_NS), start=1):
        source = edge.attrib["source"]
        target = edge.attrib["target"]
        data = _parse_graphml_data(edge, key_names)
        weight = _coerce_float(data.get("weight", "1"), default=1.0)
        source_chunks = _split_values(data.get("source_id", ""))
        edge_payload = {
            "id": f"e{index}",
            "source": source,
            "target": target,
            "weight": weight,
            "description": data.get("description", ""),
            "keywords": data.get("keywords", ""),
            "source_chunks": source_chunks,
            "source_count": len(source_chunks),
            "file_path": data.get("file_path", ""),
            "created_at": data.get("created_at", ""),
        }
        edges.append(edge_payload)

        if source in node_by_id:
            node_by_id[source]["degree"] += 1
            node_by_id[source]["weighted_degree"] += weight
        if target in node_by_id:
            node_by_id[target]["degree"] += 1
            node_by_id[target]["weighted_degree"] += weight

    nodes.sort(key=lambda item: (-int(item["degree"]), str(item["label"]).lower()))
    edges.sort(key=lambda item: (-float(item["weight"]), item["source"], item["target"]))

    type_counts: dict[str, int] = {}
    for node in nodes:
        node_type = str(node["type"])
        type_counts[node_type] = type_counts.get(node_type, 0) + 1

    return {
        "meta": {
            "generated_at": datetime.now(UTC).isoformat(),
            "source_graphml": str(graphml_path),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "type_counts": dict(sorted(type_counts.items())),
        },
        "nodes": nodes,
        "edges": edges,
    }


def _html_template(graph_json: str) -> str:
    escaped_graph_json = graph_json.replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LightRAG Knowledge Graph</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fb;
      --panel: #ffffff;
      --panel-2: #eef2f7;
      --text: #16202a;
      --muted: #5d6b7b;
      --line: #d7dee8;
      --accent: #0f766e;
      --accent-2: #7c2d12;
      --shadow: 0 12px 28px rgba(24, 38, 55, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
      letter-spacing: 0;
    }}
    .app {{
      display: grid;
      grid-template-columns: minmax(280px, 360px) minmax(0, 1fr);
      min-height: 100vh;
    }}
    aside {{
      background: var(--panel);
      border-right: 1px solid var(--line);
      padding: 18px;
      overflow: auto;
    }}
    main {{
      position: relative;
      min-width: 0;
      overflow: hidden;
    }}
    h1 {{
      margin: 0 0 12px;
      font-size: 22px;
      line-height: 1.2;
    }}
    h2 {{
      margin: 18px 0 8px;
      font-size: 14px;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin-bottom: 14px;
    }}
    .stat, .detail {{
      border: 1px solid var(--line);
      background: var(--panel-2);
      padding: 10px;
      border-radius: 6px;
    }}
    .stat strong {{
      display: block;
      font-size: 20px;
    }}
    .stat span, label, .hint, .detail small {{
      color: var(--muted);
      font-size: 12px;
    }}
    label {{
      display: block;
      margin-top: 12px;
      margin-bottom: 5px;
    }}
    input, select, button {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--text);
      padding: 9px 10px;
      font: inherit;
    }}
    input[type="range"] {{ padding: 0; }}
    button {{
      cursor: pointer;
      background: var(--accent);
      color: white;
      border-color: var(--accent);
      margin-top: 12px;
    }}
    canvas {{
      display: block;
      width: 100%;
      height: 100vh;
      background: #fbfcfe;
    }}
    .toolbar {{
      position: absolute;
      top: 16px;
      left: 16px;
      right: 16px;
      display: flex;
      gap: 8px;
      align-items: center;
      pointer-events: none;
    }}
    .badge {{
      pointer-events: auto;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.92);
      padding: 8px 10px;
      border-radius: 6px;
      box-shadow: var(--shadow);
      color: var(--muted);
      font-size: 13px;
    }}
    .list {{
      display: grid;
      gap: 6px;
      margin-top: 8px;
    }}
    .item {{
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 6px;
      padding: 8px;
      cursor: pointer;
    }}
    .item strong {{
      display: block;
      font-size: 13px;
      overflow-wrap: anywhere;
    }}
    .item span {{
      color: var(--muted);
      font-size: 12px;
    }}
    .detail {{
      max-height: 260px;
      overflow: auto;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }}
    @media (max-width: 860px) {{
      .app {{ grid-template-columns: 1fr; }}
      aside {{ border-right: 0; border-bottom: 1px solid var(--line); max-height: 48vh; }}
      canvas {{ height: 52vh; }}
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <h1>LightRAG Knowledge Graph</h1>
      <div class="stats">
        <div class="stat"><strong id="nodeCount">0</strong><span>nodes</span></div>
        <div class="stat"><strong id="edgeCount">0</strong><span>edges</span></div>
      </div>
      <label for="search">Search</label>
      <input id="search" type="search" placeholder="Entity, relation, keyword">
      <label for="typeFilter">Entity type</label>
      <select id="typeFilter"></select>
      <label for="minDegree">Minimum degree: <span id="minDegreeValue">0</span></label>
      <input id="minDegree" type="range" min="0" max="20" value="0">
      <label for="maxNodes">Max visible nodes</label>
      <input id="maxNodes" type="number" min="20" max="600" value="120">
      <button id="resetView" type="button">Reset View</button>
      <h2>Selection</h2>
      <div id="detail" class="detail">Click a node or edge.</div>
      <h2>Top Nodes</h2>
      <div id="topNodes" class="list"></div>
    </aside>
    <main>
      <canvas id="graphCanvas"></canvas>
      <div class="toolbar">
        <div id="visibleStats" class="badge">Loading graph...</div>
      </div>
    </main>
  </div>
  <script id="graph-data" type="application/json">{escaped_graph_json}</script>
  <script>
    const graphData = JSON.parse(document.getElementById("graph-data").textContent);
    const canvas = document.getElementById("graphCanvas");
    const ctx = canvas.getContext("2d");
    const controls = {{
      search: document.getElementById("search"),
      type: document.getElementById("typeFilter"),
      minDegree: document.getElementById("minDegree"),
      minDegreeValue: document.getElementById("minDegreeValue"),
      maxNodes: document.getElementById("maxNodes"),
      reset: document.getElementById("resetView"),
      detail: document.getElementById("detail"),
      topNodes: document.getElementById("topNodes"),
      visibleStats: document.getElementById("visibleStats"),
      nodeCount: document.getElementById("nodeCount"),
      edgeCount: document.getElementById("edgeCount"),
    }};
    const palette = ["#0f766e", "#b45309", "#2563eb", "#7c3aed", "#be123c", "#047857", "#4338ca", "#9333ea"];
    const typeColors = new Map();
    let nodes = [];
    let edges = [];
    let selected = null;
    let dragging = null;
    let pan = {{ x: 0, y: 0 }};
    let zoom = 1;
    let simulationTicks = 0;

    function colorFor(type) {{
      if (!typeColors.has(type)) {{
        typeColors.set(type, palette[typeColors.size % palette.length]);
      }}
      return typeColors.get(type);
    }}
    function resize() {{
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(300, Math.floor(rect.width * devicePixelRatio));
      canvas.height = Math.max(260, Math.floor(rect.height * devicePixelRatio));
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      draw();
    }}
    function resetPositions() {{
      const rect = canvas.getBoundingClientRect();
      pan = {{ x: rect.width / 2, y: rect.height / 2 }};
      zoom = 1;
      const radius = Math.min(rect.width, rect.height) * 0.36;
      nodes.forEach((node, index) => {{
        const angle = (index / Math.max(1, nodes.length)) * Math.PI * 2;
        node.x = Math.cos(angle) * radius;
        node.y = Math.sin(angle) * radius;
        node.vx = 0;
        node.vy = 0;
      }});
      for (let i = 0; i < 120; i++) tick();
      draw();
    }}
    function filteredGraph() {{
      const q = controls.search.value.trim().toLowerCase();
      const type = controls.type.value;
      const minDegree = Number(controls.minDegree.value);
      const maxNodes = Number(controls.maxNodes.value || 180);
      let filtered = graphData.nodes.filter(node => {{
        if (type !== "all" && node.type !== type) return false;
        if (node.degree < minDegree) return false;
        if (!q) return true;
        const text = [node.label, node.type, node.description, node.file_path].join(" ").toLowerCase();
        return text.includes(q);
      }});
      filtered = filtered.slice().sort((a, b) => b.degree - a.degree).slice(0, maxNodes);
      const ids = new Set(filtered.map(node => node.id));
      const filteredEdges = graphData.edges.filter(edge => ids.has(edge.source) && ids.has(edge.target));
      return {{ nodes: filtered, edges: filteredEdges }};
    }}
    function applyFilters() {{
      const filtered = filteredGraph();
      nodes = filtered.nodes.map(node => Object.assign({{}}, node));
      edges = filtered.edges;
      controls.minDegreeValue.textContent = controls.minDegree.value;
      controls.visibleStats.textContent = `${{nodes.length}} visible nodes, ${{edges.length}} visible edges`;
      renderTopNodes();
      resetPositions();
      simulationTicks = 80;
    }}
    function tick() {{
      const byId = new Map(nodes.map(node => [node.id, node]));
      for (const edge of edges) {{
        const a = byId.get(edge.source);
        const b = byId.get(edge.target);
        if (!a || !b) continue;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const distance = Math.max(1, Math.hypot(dx, dy));
        const target = 90 + Math.min(80, (a.degree + b.degree) * 2);
        const force = (distance - target) * 0.002;
        const fx = dx / distance * force;
        const fy = dy / distance * force;
        a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
      }}
      for (let i = 0; i < nodes.length; i++) {{
        for (let j = i + 1; j < nodes.length; j++) {{
          const a = nodes[i];
          const b = nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const distance = Math.max(2, Math.hypot(dx, dy));
          const force = Math.min(2.5, 120 / (distance * distance));
          const fx = dx / distance * force;
          const fy = dy / distance * force;
          a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
        }}
      }}
      for (const node of nodes) {{
        node.vx = (node.vx - node.x * 0.0008) * 0.86;
        node.vy = (node.vy - node.y * 0.0008) * 0.86;
        node.x += node.vx;
        node.y += node.vy;
      }}
    }}
    function draw() {{
      const rect = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, rect.width, rect.height);
      ctx.save();
      ctx.translate(pan.x, pan.y);
      ctx.scale(zoom, zoom);
      const byId = new Map(nodes.map(node => [node.id, node]));
      ctx.lineCap = "round";
      for (const edge of edges) {{
        const a = byId.get(edge.source);
        const b = byId.get(edge.target);
        if (!a || !b) continue;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.strokeStyle = selected === edge ? "#111827" : "rgba(80, 95, 115, 0.22)";
        ctx.lineWidth = selected === edge ? 2.4 : Math.max(0.8, Math.min(3, edge.weight));
        ctx.stroke();
      }}
      for (const node of nodes) {{
        const r = 5 + Math.min(15, Math.sqrt(node.degree) * 2.4);
        ctx.beginPath();
        ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
        ctx.fillStyle = colorFor(node.type);
        ctx.globalAlpha = selected && selected !== node ? 0.58 : 1;
        ctx.fill();
        ctx.globalAlpha = 1;
        if (selected === node) {{
          ctx.strokeStyle = "#111827";
          ctx.lineWidth = 3;
          ctx.stroke();
        }}
        if (node.degree >= 4 || selected === node) {{
          ctx.fillStyle = "#16202a";
          ctx.font = "12px Segoe UI, Arial";
          ctx.fillText(node.label, node.x + r + 4, node.y + 4);
        }}
      }}
      ctx.restore();
    }}
    function animate() {{
      if (simulationTicks > 0) {{
        tick();
        simulationTicks -= 1;
      }}
      draw();
      requestAnimationFrame(animate);
    }}
    function screenToGraph(event) {{
      const rect = canvas.getBoundingClientRect();
      return {{
        x: (event.clientX - rect.left - pan.x) / zoom,
        y: (event.clientY - rect.top - pan.y) / zoom,
      }};
    }}
    function hitTest(point) {{
      for (let i = nodes.length - 1; i >= 0; i--) {{
        const node = nodes[i];
        const r = 7 + Math.min(15, Math.sqrt(node.degree) * 2.4);
        if (Math.hypot(point.x - node.x, point.y - node.y) <= r) return node;
      }}
      const byId = new Map(nodes.map(node => [node.id, node]));
      for (const edge of edges) {{
        const a = byId.get(edge.source);
        const b = byId.get(edge.target);
        if (!a || !b) continue;
        const length = Math.max(1, Math.hypot(b.x - a.x, b.y - a.y));
        const t = Math.max(0, Math.min(1, ((point.x - a.x) * (b.x - a.x) + (point.y - a.y) * (b.y - a.y)) / (length * length)));
        const px = a.x + (b.x - a.x) * t;
        const py = a.y + (b.y - a.y) * t;
        if (Math.hypot(point.x - px, point.y - py) < 6 / zoom) return edge;
      }}
      return null;
    }}
    function describe(item) {{
      if (!item) return "Click a node or edge.";
      if (item.source && item.target) {{
        return `Relation: ${{item.source}} -> ${{item.target}}\\nWeight: ${{item.weight}}\\nKeywords: ${{item.keywords || "none"}}\\n\\n${{item.description || "No description."}}`;
      }}
      return `Entity: ${{item.label}}\\nType: ${{item.type}}\\nDegree: ${{item.degree}}\\nSource chunks: ${{item.source_count}}\\n\\n${{item.description || "No description."}}`;
    }}
    function renderTopNodes() {{
      controls.topNodes.innerHTML = "";
      nodes.slice().sort((a, b) => b.degree - a.degree).slice(0, 12).forEach(node => {{
        const div = document.createElement("div");
        div.className = "item";
        div.innerHTML = `<strong>${{node.label}}</strong><span>${{node.type}} · degree ${{node.degree}}</span>`;
        div.addEventListener("click", () => {{
          selected = node;
          controls.detail.textContent = describe(node);
          draw();
        }});
        controls.topNodes.appendChild(div);
      }});
    }}
    function initControls() {{
      controls.nodeCount.textContent = graphData.meta.node_count;
      controls.edgeCount.textContent = graphData.meta.edge_count;
      const types = ["all", ...Object.keys(graphData.meta.type_counts).sort()];
      controls.type.innerHTML = types.map(type => `<option value="${{type}}">${{type}}</option>`).join("");
      const maxDegree = Math.max(1, ...graphData.nodes.map(node => node.degree));
      controls.minDegree.max = maxDegree;
      controls.search.addEventListener("input", applyFilters);
      controls.type.addEventListener("change", applyFilters);
      controls.minDegree.addEventListener("input", applyFilters);
      controls.maxNodes.addEventListener("change", applyFilters);
      controls.reset.addEventListener("click", applyFilters);
    }}
    canvas.addEventListener("pointerdown", event => {{
      const point = screenToGraph(event);
      selected = hitTest(point);
      controls.detail.textContent = describe(selected);
      if (selected && !selected.source) dragging = selected;
      draw();
    }});
    canvas.addEventListener("pointermove", event => {{
      if (!dragging) return;
      const point = screenToGraph(event);
      dragging.x = point.x;
      dragging.y = point.y;
      dragging.vx = 0;
      dragging.vy = 0;
      simulationTicks = 20;
      draw();
    }});
    canvas.addEventListener("pointerup", () => {{ dragging = null; }});
    canvas.addEventListener("wheel", event => {{
      event.preventDefault();
      const factor = event.deltaY > 0 ? 0.92 : 1.08;
      zoom = Math.max(0.25, Math.min(3, zoom * factor));
      draw();
    }}, {{ passive: false }});
    window.addEventListener("resize", resize);
    initControls();
    resize();
    applyFilters();
    animate();
  </script>
</body>
</html>
"""


def export_lightrag_graph(
    repo_root: Path | None = None,
    graphml_path: Path | None = None,
    output_dir: Path | None = None,
) -> GraphExport:
    """Export LightRAG GraphML to graph.json and index.html."""
    root = repo_root_from(repo_root)
    source = graphml_path or root / "data" / "lightrag" / "graph_chunk_entity_relation.graphml"
    target_dir = output_dir or root / "docs" / "knowledge_graph"
    if not source.exists():
        msg = f"LightRAG GraphML file not found: {source}"
        raise FileNotFoundError(msg)

    payload = parse_lightrag_graphml(source)
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "graph.json"
    html_path = target_dir / "index.html"
    graph_json = json.dumps(payload, indent=2, ensure_ascii=False)
    json_path.write_text(graph_json + "\n", encoding="utf-8")
    html_path.write_text(_html_template(graph_json), encoding="utf-8")
    return GraphExport(
        payload=payload,
        output_dir=target_dir,
        json_path=json_path,
        html_path=html_path,
    )


def main() -> None:
    """CLI entrypoint."""
    parser = ArgumentParser(description="Export LightRAG GraphML to a local HTML viewer.")
    parser.add_argument(
        "--graphml",
        type=Path,
        default=None,
        help="GraphML source path. Defaults to data/lightrag/graph_chunk_entity_relation.graphml.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to docs/knowledge_graph.",
    )
    args = parser.parse_args()

    export = export_lightrag_graph(graphml_path=args.graphml, output_dir=args.output_dir)
    table = Table(title="LightRAG Graph Export")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("Nodes", str(export.payload["meta"]["node_count"]))
    table.add_row("Edges", str(export.payload["meta"]["edge_count"]))
    table.add_row("JSON", str(export.json_path))
    table.add_row("HTML", str(export.html_path))
    console.print(table)
    sys.exit(0)


if __name__ == "__main__":
    main()
