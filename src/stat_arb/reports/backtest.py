"""Deterministic backtest report artifact generation."""

from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class DataQualityReportSnapshot:
    """Registry-derived data-quality summary for report rendering."""

    dataset_id: str
    symbol: str
    timeframe: str
    passed: bool
    quality_score: float
    missing_bars: int
    duplicate_timestamps: int
    outlier_count: int
    alignment_score: float
    issues: tuple[str, ...]
    report_path: str


@dataclass(frozen=True)
class ReportSeriesSnapshot:
    """Optional chart-ready series for visual report artifacts."""

    timestamps: tuple[str, ...]
    equity_curve: tuple[float, ...]
    drawdown_curve: tuple[float, ...]
    z_scores: tuple[float, ...]
    entry_markers: tuple[int, ...]
    exit_markers: tuple[int, ...]
    rolling_sharpe: tuple[float, ...]
    trade_pnls: tuple[float, ...]


@dataclass(frozen=True)
class BacktestReportSnapshot:
    """Registry-derived snapshot used by report generation."""

    backtest_id: str
    hypothesis_id: str
    net_pnl: float
    gross_pnl: float
    total_cost: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    turnover: float
    num_trades: int
    baseline_sharpe: float
    net_pnl_2x_costs: float
    net_pnl_half_costs: float
    critic_status: str | None
    critic_objections: str | None
    tested_at: datetime
    data_quality_reports: tuple[DataQualityReportSnapshot, ...] = ()
    series: ReportSeriesSnapshot | None = None


@dataclass(frozen=True)
class GeneratedReportArtifact:
    """Generated report artifact ready for registry persistence."""

    artifact_type: str
    file_path: Path
    format: str
    created_at: datetime


def generate_backtest_report_artifacts(
    snapshot: BacktestReportSnapshot,
    *,
    output_dir: Path | str,
) -> tuple[GeneratedReportArtifact, ...]:
    """Write HTML and JSON backtest report artifacts."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(UTC)
    base_name = f"backtest-{_safe_name(snapshot.backtest_id)}"

    html_path = root / f"{base_name}.html"
    pdf_path = root / f"{base_name}.pdf"
    json_path = root / f"{base_name}.summary.json"
    data_quality_path = root / f"{base_name}.data-quality.html"
    html_path.write_text(_render_html(snapshot), encoding="utf-8")
    pdf_path.write_bytes(_render_pdf(snapshot))
    json_path.write_text(
        json.dumps(_json_payload(snapshot), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    data_quality_path.write_text(_render_data_quality_html(snapshot), encoding="utf-8")

    artifacts = [
        GeneratedReportArtifact(
            artifact_type="backtest_report",
            file_path=html_path,
            format="html",
            created_at=created_at,
        ),
        GeneratedReportArtifact(
            artifact_type="backtest_report_pdf",
            file_path=pdf_path,
            format="pdf",
            created_at=created_at,
        ),
        GeneratedReportArtifact(
            artifact_type="json_summary",
            file_path=json_path,
            format="json",
            created_at=created_at,
        ),
        GeneratedReportArtifact(
            artifact_type="data_quality_report",
            file_path=data_quality_path,
            format="html",
            created_at=created_at,
        ),
    ]
    if snapshot.series is not None:
        artifacts.extend(_write_visualization_artifacts(root, base_name, snapshot, created_at))
    return tuple(artifacts)


def _render_html(snapshot: BacktestReportSnapshot) -> str:
    critic_status = snapshot.critic_status or "не указан"
    critic_objections = snapshot.critic_objections or "Нет"
    rows = (
        ("ID backtest", snapshot.backtest_id),
        ("ID hypothesis", snapshot.hypothesis_id),
        ("Net PnL", f"{snapshot.net_pnl:.6f}"),
        ("Gross PnL", f"{snapshot.gross_pnl:.6f}"),
        ("Итого costs", f"{snapshot.total_cost:.6f}"),
        ("Sharpe", f"{snapshot.sharpe_ratio:.6f}"),
        ("Sortino", f"{snapshot.sortino_ratio:.6f}"),
        ("Максимальная просадка", f"{snapshot.max_drawdown:.6f}"),
        ("Доля прибыльных trades", f"{snapshot.win_rate:.6f}"),
        ("Profit factor", f"{snapshot.profit_factor:.6f}"),
        ("Turnover", f"{snapshot.turnover:.6f}"),
        ("Количество trades", str(snapshot.num_trades)),
        ("Baseline Sharpe", f"{snapshot.baseline_sharpe:.6f}"),
        ("Net PnL при 2x costs", f"{snapshot.net_pnl_2x_costs:.6f}"),
        ("Net PnL при 0.5x costs", f"{snapshot.net_pnl_half_costs:.6f}"),
        ("Статус Critic", critic_status),
        ("Возражения Critic", critic_objections),
        ("Время backtest", snapshot.tested_at.isoformat()),
    )
    table_rows = "\n".join(
        "<tr>"
        f"<th>{html.escape(label)}</th>"
        f"<td>{html.escape(value)}</td>"
        "</tr>"
        for label, value in rows
    )
    data_quality_section = _data_quality_section(snapshot)
    visual_section = _visualization_section(snapshot)
    cost_section = _cost_attribution_section(snapshot)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Отчет по backtest {html.escape(snapshot.backtest_id)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #18212f; }}
    h1 {{ margin-bottom: 8px; }}
    h2 {{ margin-top: 28px; }}
    table {{ border-collapse: collapse; min-width: 720px; }}
    th, td {{ border: 1px solid #c7d0dc; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef3f8; width: 260px; }}
    .note {{ color: #56657a; }}
  </style>
</head>
<body>
  <h1>Отчет по backtest</h1>
  <p>Человекочитаемый снимок результата. Точные registry records остаются источником истины.</p>
  <table>
    {table_rows}
  </table>
  {cost_section}
  {data_quality_section}
  {visual_section}
</body>
</html>
"""


def _cost_attribution_section(snapshot: BacktestReportSnapshot) -> str:
    rows = (
        ("Gross PnL", snapshot.gross_pnl),
        ("Net PnL", snapshot.net_pnl),
        ("Итого costs", snapshot.total_cost),
        ("Net PnL при 2x costs", snapshot.net_pnl_2x_costs),
        ("Net PnL при 0.5x costs", snapshot.net_pnl_half_costs),
    )
    table_rows = "\n".join(
        f"<tr><th>{html.escape(label)}</th><td>{value:.6f}</td></tr>" for label, value in rows
    )
    return f"""<h2>Разбор costs</h2>
  <table>{table_rows}</table>"""


def _data_quality_section(snapshot: BacktestReportSnapshot) -> str:
    if not snapshot.data_quality_reports:
        return (
            "<h2>Качество данных</h2>"
            '<p class="note">Отчеты data quality не переданы в snapshot отчета.</p>'
        )
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(report.symbol)}</td>"
        f"<td>{html.escape(report.timeframe)}</td>"
        f"<td>{'пройдено' if report.passed else 'провалено'}</td>"
        f"<td>{report.quality_score:.6f}</td>"
        f"<td>{report.missing_bars}</td>"
        f"<td>{report.duplicate_timestamps}</td>"
        f"<td>{report.outlier_count}</td>"
        "</tr>"
        for report in snapshot.data_quality_reports
    )
    return f"""<h2>Качество данных</h2>
  <table>
    <tr><th>Symbol</th><th>Timeframe</th><th>Статус</th><th>Оценка качества</th><th>Пропущенные bars</th><th>Дубликаты</th><th>Outliers</th></tr>
    {rows}
  </table>"""


def _visualization_section(snapshot: BacktestReportSnapshot) -> str:
    if snapshot.series is None:
        return (
            "<h2>Визуализации</h2>"
            '<p class="note">Визуализации недоступны: registry не содержит исходные серии '
            "equity curve, z-score и trade distribution для этого backtest.</p>"
        )
    return """<h2>Визуализации</h2>
  <ul>
    <li>Кривая equity с наложенной просадкой</li>
    <li>Z-score signals с отметками entry/exit</li>
    <li>Диаграмма разбора costs</li>
    <li>Rolling Sharpe ratio</li>
    <li>Гистограмма распределения trades</li>
  </ul>"""


def _render_data_quality_html(snapshot: BacktestReportSnapshot) -> str:
    return f"""<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><title>Отчет по data quality {html.escape(snapshot.backtest_id)}</title></head>
<body>
  <h1>Отчет по data quality</h1>
  {_data_quality_section(snapshot)}
</body>
</html>
"""


def _write_visualization_artifacts(
    root: Path,
    base_name: str,
    snapshot: BacktestReportSnapshot,
    created_at: datetime,
) -> tuple[GeneratedReportArtifact, ...]:
    assert snapshot.series is not None
    specs: tuple[tuple[str, str, str], ...] = (
        (
            "equity_curve",
            "Кривая equity с наложенной просадкой",
            _line_svg(
                "equity_curve",
                snapshot.series.equity_curve,
                title="Кривая equity",
                overlay=snapshot.series.drawdown_curve,
            ),
        ),
        (
            "z_score_signals",
            "Z-score signals с отметками entry/exit",
            _line_svg(
                "z_score_signals",
                snapshot.series.z_scores,
                title="Z-score signals",
                markers=snapshot.series.entry_markers + snapshot.series.exit_markers,
            ),
        ),
        ("cost_attribution", "Диаграмма разбора costs", _cost_svg(snapshot)),
        (
            "rolling_sharpe",
            "Rolling Sharpe ratio",
            _line_svg(
                "rolling_sharpe",
                snapshot.series.rolling_sharpe,
                title="Rolling Sharpe ratio",
            ),
        ),
        (
            "trade_distribution",
            "Гистограмма распределения trades",
            _bar_svg(
                "trade_distribution",
                snapshot.series.trade_pnls,
                title="Распределение trades",
            ),
        ),
    )
    artifacts: list[GeneratedReportArtifact] = []
    for artifact_type, title, content in specs:
        path = root / f"{base_name}.{artifact_type}.svg"
        path.write_text(content.replace("<title></title>", f"<title>{html.escape(title)}</title>"), encoding="utf-8")
        artifacts.append(
            GeneratedReportArtifact(
                artifact_type=artifact_type,
                file_path=path,
                format="svg",
                created_at=created_at,
            )
        )
    return tuple(artifacts)


def _line_svg(
    artifact_type: str,
    values: tuple[float, ...],
    *,
    title: str,
    overlay: tuple[float, ...] = (),
    markers: tuple[int, ...] = (),
) -> str:
    points = _polyline_points(values)
    overlay_points = _polyline_points(overlay) if overlay else ""
    marker_nodes = "\n".join(
        f'<circle cx="{40 + index * 40}" cy="70" r="4" fill="#b91c1c" />'
        for index in markers
        if index >= 0
    )
    overlay_node = (
        f'<polyline points="{overlay_points}" fill="none" stroke="#dc2626" stroke-width="2" />'
        if overlay_points
        else ""
    )
    return f"""<svg data-artifact="{html.escape(artifact_type)}" xmlns="http://www.w3.org/2000/svg" width="640" height="180" viewBox="0 0 640 180">
<title></title>
<rect width="640" height="180" fill="#ffffff"/>
<text x="20" y="28" font-family="Arial" font-size="16" fill="#18212f">{html.escape(title)}</text>
<polyline points="{points}" fill="none" stroke="#0f766e" stroke-width="3" />
{overlay_node}
{marker_nodes}
</svg>
"""


def _bar_svg(artifact_type: str, values: tuple[float, ...], *, title: str) -> str:
    if not values:
        values = (0.0,)
    maximum = max(abs(value) for value in values) or 1.0
    bars = []
    for index, value in enumerate(values[:12]):
        height = abs(value) / maximum * 100.0
        y = 90.0 - height if value >= 0 else 90.0
        color = "#0f766e" if value >= 0 else "#dc2626"
        bars.append(
            f'<rect x="{40 + index * 42}" y="{y:.2f}" width="28" height="{height:.2f}" fill="{color}" />'
        )
    return f"""<svg data-artifact="{html.escape(artifact_type)}" xmlns="http://www.w3.org/2000/svg" width="640" height="180" viewBox="0 0 640 180">
<title></title>
<rect width="640" height="180" fill="#ffffff"/>
<line x1="30" y1="90" x2="610" y2="90" stroke="#64748b" stroke-width="1"/>
<text x="20" y="28" font-family="Arial" font-size="16" fill="#18212f">{html.escape(title)}</text>
{''.join(bars)}
</svg>
"""


def _cost_svg(snapshot: BacktestReportSnapshot) -> str:
    cost_share = 0.0 if snapshot.gross_pnl == 0.0 else min(1.0, abs(snapshot.total_cost / snapshot.gross_pnl))
    cost_width = 500.0 * cost_share
    return f"""<svg data-artifact="cost_attribution" xmlns="http://www.w3.org/2000/svg" width="640" height="180" viewBox="0 0 640 180">
<title></title>
<rect width="640" height="180" fill="#ffffff"/>
<text x="20" y="28" font-family="Arial" font-size="16" fill="#18212f">Разбор costs</text>
<rect x="40" y="70" width="500" height="34" fill="#dbeafe"/>
<rect x="40" y="70" width="{cost_width:.2f}" height="34" fill="#dc2626"/>
<text x="40" y="130" font-family="Arial" font-size="13" fill="#18212f">Доля costs от Gross PnL: {cost_share:.2%}</text>
</svg>
"""


def _polyline_points(values: tuple[float, ...]) -> str:
    if not values:
        values = (0.0,)
    minimum = min(values)
    maximum = max(values)
    span = maximum - minimum or 1.0
    step = 560.0 / max(1, len(values) - 1)
    return " ".join(
        f"{40 + index * step:.2f},{140 - ((value - minimum) / span) * 90:.2f}"
        for index, value in enumerate(values)
    )


def _render_pdf(snapshot: BacktestReportSnapshot) -> bytes:
    lines = [
        "Отчет по backtest",
        f"ID backtest: {snapshot.backtest_id}",
        f"ID hypothesis: {snapshot.hypothesis_id}",
        f"Net PnL: {snapshot.net_pnl:.6f}",
        f"Sharpe: {snapshot.sharpe_ratio:.6f}",
        f"Статус Critic: {snapshot.critic_status or 'не указан'}",
    ]
    stream = "BT /F1 12 Tf 72 760 Td " + " T* ".join(_pdf_literal(line) for line in lines) + " ET"
    objects = [
        "1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        "2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        "3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        "4 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream.encode('latin-1'))} >> stream\n{stream}\nendstream endobj\n",
    ]
    content = "%PDF-1.4\n"
    offsets = [0]
    for item in objects:
        offsets.append(len(content.encode("latin-1")))
        content += item
    xref_offset = len(content.encode("latin-1"))
    xref = ["xref\n0 6\n", "0000000000 65535 f \n"]
    xref.extend(f"{offset:010d} 00000 n \n" for offset in offsets[1:])
    content += "".join(xref)
    content += "trailer << /Size 6 /Root 1 0 R >>\nstartxref\n"
    content += f"{xref_offset}\n%%EOF\n"
    return content.encode("latin-1")


def _pdf_literal(value: str) -> str:
    try:
        value.encode("latin-1")
    except UnicodeEncodeError:
        payload = b"\xfe\xff" + value.encode("utf-16-be")
        return f"<{payload.hex().upper()}>"
    return f"({_pdf_escape(value)})"


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _json_payload(snapshot: BacktestReportSnapshot) -> dict[str, object]:
    payload = asdict(snapshot)
    payload["tested_at"] = snapshot.tested_at.isoformat()
    return payload


def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "-" for character in value)
