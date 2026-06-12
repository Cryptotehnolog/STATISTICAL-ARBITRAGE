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

Risks: The current Task 12 boundary is intentionally lightweight. It produces complete
registry-backed HTML/PDF/JSON artifacts, data-quality pages, and deterministic visuals
when factual chart-ready series are provided. It must not fabricate charts from aggregate
metrics. Backtest Agent persistence can now write a registry-linked `backtest_series`
sidecar and Report Agent can load it, but the future full-runner still must make this
sidecar mandatory before `execute-stage --stage reporting` is exposed.

Verification: `scripts/check_report_pipeline.ps1` runs report artifact generation tests,
Report Agent registry/memory boundary tests, and the guard that keeps the report checkpoint
wired into pre-commit and CI. Human-facing report labels are Russian; technical artifact
types and JSON keys remain English internal contracts.

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
generation with series and the registry-only missing-visualization path.
`tests/unit/test_backtest_agent.py` verifies persisted `backtest_series` sidecars.
`tests/unit/test_report_agent.py` verifies sidecar loading, registry data-quality rows,
artifact persistence, and policy-safe memory summary writes.

## DEC-0075: Persist factual backtest series as registry-linked sidecars

Status: accepted

Decision: Backtest Agent persistence may receive explicit chart-ready factual series and
write them as a `backtest_series` JSON sidecar linked through `ReportArtifact`. Report
Agent reads that registry artifact and generates visual report artifacts from the sidecar.
If the sidecar is absent, Report Agent keeps the missing-visualization message and does
not fabricate charts from aggregate metrics.

Rationale: The report layer needs real equity, drawdown, z-score, rolling metric, and trade
series to produce trustworthy charts. Storing those series only as loose files would make
them hard to find and audit. Linking the JSON sidecar in the registry preserves the
Structured Registry as the source of truth for report inputs.

Rules:
- Series sidecars must be provided explicitly by the runner/backtest payload.
- Series sidecars must be registry-linked as `ReportArtifact(artifact_type="backtest_series")`.
- Report Agent must validate that the sidecar `backtest_id` matches the requested
  backtest.
- Reporting stage execution remains blocked until the runner can guarantee factual
  sidecars for full visual reports.

Verification:
- `tests/unit/test_backtest_agent.py`
- `tests/unit/test_report_agent.py`
- `scripts/check_backtest_pipeline.ps1`
- `scripts/check_report_pipeline.ps1`
