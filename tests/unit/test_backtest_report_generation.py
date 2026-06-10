"""Unit tests for deterministic backtest report generation."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from stat_arb.reports import (
    BacktestReportSnapshot,
    DataQualityReportSnapshot,
    ReportSeriesSnapshot,
    generate_backtest_report_artifacts,
)


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
        data_quality_reports=(
            DataQualityReportSnapshot(
                dataset_id="dataset-a",
                symbol="AAA",
                timeframe="15m",
                passed=True,
                quality_score=0.98,
                missing_bars=0,
                duplicate_timestamps=0,
                outlier_count=1,
                alignment_score=1.0,
                issues=(),
                report_path="/data/aaa.quality.json",
            ),
        ),
        series=ReportSeriesSnapshot(
            timestamps=("2024-01-01T00:00:00Z", "2024-01-01T00:15:00Z", "2024-01-01T00:30:00Z"),
            equity_curve=(100.0, 104.0, 101.0),
            drawdown_curve=(0.0, 0.0, 0.028846),
            z_scores=(0.0, 2.2, 0.4),
            entry_markers=(1,),
            exit_markers=(2,),
            rolling_sharpe=(0.0, 1.1, 0.8),
            trade_pnls=(4.0, -3.0, 2.0),
        ),
    )

    artifacts = generate_backtest_report_artifacts(snapshot, output_dir=tmp_path)

    artifact_types = {artifact.artifact_type for artifact in artifacts}
    assert artifact_types == {
        "backtest_report",
        "backtest_report_pdf",
        "json_summary",
        "data_quality_report",
        "equity_curve",
        "z_score_signals",
        "cost_attribution",
        "rolling_sharpe",
        "trade_distribution",
    }
    paths = {artifact.artifact_type: artifact.file_path for artifact in artifacts}
    html_path = paths["backtest_report"]
    json_path = paths["json_summary"]
    assert html_path.exists()
    assert json_path.exists()
    assert paths["backtest_report_pdf"].read_bytes().startswith(b"%PDF-1.4")

    html = html_path.read_text(encoding="utf-8")
    assert "Отчет по backtest" in html
    assert "bt-1" in html
    assert "Sharpe" in html
    assert "weak assumptions require retest" in html
    assert "Кривая equity" in html
    assert "Качество данных" in html
    assert "Разбор costs" in html
    assert "Cost attribution" not in html
    assert "Data quality" not in html
    assert "Equity curve with drawdown overlay" not in html

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["backtest_id"] == "bt-1"
    assert payload["net_pnl"] == 80.0
    assert payload["critic_status"] == "quarantined"
    assert payload["data_quality_reports"][0]["symbol"] == "AAA"
    assert payload["series"]["equity_curve"] == [100.0, 104.0, 101.0]

    data_quality_html = paths["data_quality_report"].read_text(encoding="utf-8")
    assert "Отчет по data quality" in data_quality_html
    assert "AAA" in data_quality_html

    for artifact_type in (
        "equity_curve",
        "z_score_signals",
        "cost_attribution",
        "rolling_sharpe",
        "trade_distribution",
    ):
        svg = paths[artifact_type].read_text(encoding="utf-8")
        assert "<svg" in svg
        assert artifact_type in svg


def test_generate_backtest_report_marks_missing_visual_series(tmp_path) -> None:
    """Registry-only snapshots should not invent unavailable visualization series."""
    snapshot = BacktestReportSnapshot(
        backtest_id="bt-registry-only",
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
        critic_status=None,
        critic_objections=None,
        tested_at=datetime(2024, 1, 2, tzinfo=UTC),
    )

    artifacts = generate_backtest_report_artifacts(snapshot, output_dir=tmp_path)

    paths = {artifact.artifact_type: artifact.file_path for artifact in artifacts}
    assert "equity_curve" not in paths
    html = paths["backtest_report"].read_text(encoding="utf-8")
    assert "Визуализации недоступны" in html
    assert "registry не содержит исходные серии" in html
