"""Unit tests for LightRAG graph export."""

import json
from pathlib import Path
from uuid import uuid4

from stat_arb.scripts import export_lightrag_graph as export_module


def _test_dir(name: str) -> Path:
    path = (Path("data/test_tmp") / f"{name}-{uuid4()}").resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_graphml(path: Path) -> None:
    path.write_text(
        """<?xml version='1.0' encoding='utf-8'?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns">
  <key id="n0" for="node" attr.name="entity_id" attr.type="string" />
  <key id="n1" for="node" attr.name="entity_type" attr.type="string" />
  <key id="n2" for="node" attr.name="description" attr.type="string" />
  <key id="n3" for="node" attr.name="source_id" attr.type="string" />
  <key id="e0" for="edge" attr.name="weight" attr.type="double" />
  <key id="e1" for="edge" attr.name="description" attr.type="string" />
  <key id="e2" for="edge" attr.name="keywords" attr.type="string" />
  <graph edgedefault="undirected">
    <node id="LightRAG">
      <data key="n0">LightRAG</data>
      <data key="n1">artifact</data>
      <data key="n2">Knowledge graph memory.</data>
      <data key="n3">chunk-a&lt;SEP&gt;chunk-b</data>
    </node>
    <node id="OmniRoute">
      <data key="n0">OmniRoute</data>
      <data key="n1">gateway</data>
      <data key="n2">OpenAI-compatible gateway.</data>
      <data key="n3">chunk-a</data>
    </node>
    <edge source="LightRAG" target="OmniRoute">
      <data key="e0">2.5</data>
      <data key="e1">LightRAG uses OmniRoute.</data>
      <data key="e2">gateway,graph extraction</data>
    </edge>
  </graph>
</graphml>
""",
        encoding="utf-8",
    )


def test_parse_lightrag_graphml_maps_nodes_edges_and_degrees() -> None:
    """GraphML parser should expose viewer-friendly nodes, edges, and degrees."""
    test_dir = _test_dir("graph-export-parse")
    graphml = test_dir / "graph.graphml"
    _write_graphml(graphml)

    payload = export_module.parse_lightrag_graphml(graphml)

    assert payload["meta"]["node_count"] == 2
    assert payload["meta"]["edge_count"] == 1
    assert payload["meta"]["type_counts"] == {"artifact": 1, "gateway": 1}
    assert payload["nodes"][0]["degree"] == 1
    assert payload["nodes"][0]["source_chunks"] == ["chunk-a", "chunk-b"]
    assert payload["edges"][0]["weight"] == 2.5
    assert payload["edges"][0]["keywords"] == "gateway,graph extraction"


def test_export_lightrag_graph_writes_json_and_html() -> None:
    """Exporter should write both graph.json and a standalone HTML viewer."""
    test_dir = _test_dir("graph-export-write")
    (test_dir / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    graphml = test_dir / "graph.graphml"
    output_dir = test_dir / "docs" / "knowledge_graph"
    _write_graphml(graphml)

    export = export_module.export_lightrag_graph(
        repo_root=test_dir,
        graphml_path=graphml,
        output_dir=output_dir,
    )

    payload = json.loads(export.json_path.read_text(encoding="utf-8"))
    html = export.html_path.read_text(encoding="utf-8")
    assert payload["meta"]["node_count"] == 2
    assert "<canvas id=\"graphCanvas\"" in html
    assert "Граф знаний LightRAG" in html
    assert "importantOnly" in html
    assert "Только важные узлы" in html
    assert "data-preset=\"agents\"" in html
    assert "data-preset=\"risks\"" in html
    assert "data-preset=\"decisions\"" in html
