"""Deterministic backtest report artifact generation."""

from __future__ import annotations

import html
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path


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
    json_path = root / f"{base_name}.summary.json"
    html_path.write_text(_render_html(snapshot), encoding="utf-8")
    json_path.write_text(
        json.dumps(_json_payload(snapshot), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return (
        GeneratedReportArtifact(
            artifact_type="backtest_report",
            file_path=html_path,
            format="html",
            created_at=created_at,
        ),
        GeneratedReportArtifact(
            artifact_type="json_summary",
            file_path=json_path,
            format="json",
            created_at=created_at,
        ),
    )


def _render_html(snapshot: BacktestReportSnapshot) -> str:
    critic_status = snapshot.critic_status or "не указан"
    critic_objections = snapshot.critic_objections or "Нет"
    rows = (
        ("Backtest ID", snapshot.backtest_id),
        ("Hypothesis ID", snapshot.hypothesis_id),
        ("Net PnL", f"{snapshot.net_pnl:.6f}"),
        ("Gross PnL", f"{snapshot.gross_pnl:.6f}"),
        ("Итого costs", f"{snapshot.total_cost:.6f}"),
        ("Sharpe", f"{snapshot.sharpe_ratio:.6f}"),
        ("Sortino", f"{snapshot.sortino_ratio:.6f}"),
        ("Max drawdown", f"{snapshot.max_drawdown:.6f}"),
        ("Win rate", f"{snapshot.win_rate:.6f}"),
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
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>Отчет по backtest {html.escape(snapshot.backtest_id)}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #18212f; }}
    h1 {{ margin-bottom: 8px; }}
    table {{ border-collapse: collapse; min-width: 720px; }}
    th, td {{ border: 1px solid #c7d0dc; padding: 8px 10px; text-align: left; }}
    th {{ background: #eef3f8; width: 260px; }}
  </style>
</head>
<body>
  <h1>Отчет по backtest</h1>
  <p>Человекочитаемый снимок результата. Точные registry records остаются источником истины.</p>
  <table>
    {table_rows}
  </table>
</body>
</html>
"""


def _json_payload(snapshot: BacktestReportSnapshot) -> dict[str, object]:
    payload = asdict(snapshot)
    payload["tested_at"] = snapshot.tested_at.isoformat()
    return payload


def _safe_name(value: str) -> str:
    return "".join(character if character.isalnum() or character in "-_" else "-" for character in value)
