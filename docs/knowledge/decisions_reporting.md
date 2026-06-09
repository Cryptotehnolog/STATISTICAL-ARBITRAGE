# Knowledge Decisions: Reporting

This shard contains durable decisions about Report Agent boundaries, report artifacts, and
what belongs in the registry versus ApeRAG memory.

## DEC-0056: Build Report Agent around registry-backed artifacts first

Decision: Report generation starts with a small deterministic boundary that builds HTML and
JSON backtest artifacts from a registry-derived `BacktestReportSnapshot`, persists artifact
links as `ReportArtifact` rows, and writes only a concise report summary through the Memory
Agent policy layer.

Rationale: Reporting must not become an unstructured side channel. Backtest metrics, cost
attribution, critic status, experiment IDs, and artifact paths belong in the SQLite
registry. ApeRAG should store a searchable summary and a registry reference so future
agents can find the report without duplicating precise metrics in memory.

Alternatives considered: Generate full PDF/chart reports before the boundary exists; let
Report Agent write directly to ApeRAG; store only files without registry rows; mark Task 12
complete after a minimal HTML report. Those options either bypass the source of truth or
create false completion.

Risks: The current boundary is a prerequisite, not the full Report Agent. Task 12 still
needs complete report content, data quality report pages, visualizations, and full
content-completeness tests before it can be closed.

Verification: `scripts/check_report_pipeline.ps1` runs report artifact generation tests,
Report Agent registry/memory boundary tests, and the guard that keeps the report checkpoint
wired into pre-commit and CI.

## DEC-0057: Generate deterministic report visuals only from chart-ready series

Decision: The Report Agent may generate lightweight SVG visual artifacts for equity curve,
drawdown overlay, z-score entry/exit markers, cost attribution, rolling Sharpe, and trade
distribution when `ReportSeriesSnapshot` is provided. If a report is built only from the
current registry aggregates, the HTML report must explicitly state that visualization
series are unavailable instead of fabricating curves from summary metrics.

Rationale: Reports must be useful to humans without corrupting research evidence. The
registry currently stores aggregate backtest metrics and data-quality records, not the full
equity curve or trade distribution series. Inventing charts from aggregates would make a
pretty report but harm auditability. Deterministic SVG keeps Task 12 lightweight and avoids
browser/rendering CPU overhead.

Alternatives considered: Add a heavy PDF/chart dependency immediately; derive fake curves
from net PnL and drawdown; postpone all visual reporting until the dashboard. The chosen
boundary provides useful artifacts now while preserving a clean path for richer dashboard
views later.

Verification: `tests/unit/test_backtest_report_generation.py` covers full artifact
generation with series and the registry-only missing-visualization path. `tests/unit/test_report_agent.py`
verifies registry data-quality rows, artifact persistence, and policy-safe memory summary
writes.
