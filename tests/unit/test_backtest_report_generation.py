"""Unit tests for deterministic backtest report generation."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from stat_arb.reports import BacktestReportSnapshot, generate_backtest_report_artifacts


def test_generate_backtest_report_artifacts_writes_html_and_json(tmp_path) -> None:
    """Backtest reports should produce human-readable HTML and machine-readable summary."""
    snapshot = BacktestReportSnapshot(
        backtest_id="bt-1",
        hypothesis_id="hyp-1",
        net_pnl=80.0,
        gross_pnl=100.0,
        total_cost=20.0,
        sharpe_ratio=1.2,
        sortino_ratio=1.5,
        max_drawdown=0.1,
        win_rate=0.6,
        profit_factor=1.8,
        turnover=1.1,
        num_trades=4,
        baseline_sharpe=0.4,
        net_pnl_2x_costs=60.0,
        net_pnl_half_costs=90.0,
        critic_status="quarantined",
        critic_objections="weak assumptions require retest",
        tested_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    artifacts = generate_backtest_report_artifacts(snapshot, output_dir=tmp_path)

    assert [artifact.artifact_type for artifact in artifacts] == [
        "backtest_report",
        "json_summary",
    ]
    html_path = artifacts[0].file_path
    json_path = artifacts[1].file_path
    assert html_path.exists()
    assert json_path.exists()

    html = html_path.read_text(encoding="utf-8")
    assert "Отчет по backtest" in html
    assert "bt-1" in html
    assert "Sharpe" in html
    assert "weak assumptions require retest" in html

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["backtest_id"] == "bt-1"
    assert payload["net_pnl"] == 80.0
    assert payload["critic_status"] == "quarantined"
