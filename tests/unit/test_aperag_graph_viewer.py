"""Static tests for the ApeRAG graph viewer scripts."""

from pathlib import Path

EXPORT_SCRIPT = Path("scripts/export_aperag_graph.ps1")
CHECK_SCRIPT = Path("scripts/check_aperag_graph_export.ps1")
SERVE_SCRIPT = Path("scripts/serve_aperag_graph.ps1")
OPEN_SCRIPT = Path("scripts/open_aperag_graph.ps1")
SHORTCUT_SCRIPT = Path("scripts/create_aperag_graph_shortcut.ps1")
VIEWER = Path("docs/knowledge_graph/index.html")


def test_aperag_graph_export_reads_graph_endpoints() -> None:
    """Exporter should use ApeRAG graph endpoints and write graph.json."""
    script = EXPORT_SCRIPT.read_text(encoding="utf-8")

    assert "/graphs/labels" in script
    assert "/graphs?max_nodes=$MaxNodes&max_depth=$MaxDepth" in script
    assert "docs\\knowledge_graph" in script
    assert "graph.json" in script
    assert "source = \"ApeRAG\"" in script


def test_aperag_graph_viewer_is_three_dimensional() -> None:
    """Viewer should use a 3D graph library and human-facing Russian labels."""
    html = VIEWER.read_text(encoding="utf-8")

    assert "Граф знаний ApeRAG" in html
    assert "aperag-knowledge-graph" in html
    assert "3d-force-graph" in html
    assert "ForceGraph3D" in html
    assert "Только важные узлы" in html
    assert "Сбросить вид" in html
    assert "Left-click" not in html


def test_aperag_graph_scripts_support_desktop_launch_and_checks() -> None:
    """Open and shortcut scripts should refresh export before browser launch."""
    check_script = CHECK_SCRIPT.read_text(encoding="utf-8")
    serve_script = SERVE_SCRIPT.read_text(encoding="utf-8")
    open_script = OPEN_SCRIPT.read_text(encoding="utf-8")
    shortcut_script = SHORTCUT_SCRIPT.read_text(encoding="utf-8")

    assert "export_aperag_graph.ps1" in check_script
    assert "export_aperag_graph.ps1" in serve_script
    assert "WScript.Shell" in serve_script
    assert "aperag-knowledge-graph" in serve_script
    assert "serve_aperag_graph.ps1" in open_script
    assert "Граф знаний ApeRAG.lnk" in shortcut_script
    assert "ApeRAG Knowledge Graph.lnk" in shortcut_script
    assert "open_aperag_graph.ps1" in shortcut_script
