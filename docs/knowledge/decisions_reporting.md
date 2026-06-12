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
sidecar and Report Agent can load it. CLI `execute-stage --stage reporting` is exposed
only behind a registry guard that requires a matching `backtest_series` sidecar for the
requested `backtest_id`.

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
- CLI reporting stage execution must fail closed unless the registry already contains a
  matching `backtest_series` sidecar for the requested backtest.
- Future full-runner paths must provide and persist those factual sidecars before queuing
  reporting work.

Verification:
- `tests/unit/test_backtest_agent.py`
- `tests/unit/test_report_agent.py`
- `tests/unit/test_cli_data.py`
- `scripts/check_backtest_pipeline.ps1`
- `scripts/check_report_pipeline.ps1`
- `scripts/check_cli_pipeline.ps1`

## DEC-0076: Enable CLI reporting execution only behind factual sidecar guard

Status: accepted

Decision: The CLI may execute queued `reporting` tasks through `run_report_agent`, but
only after checking the Structured Registry for a JSON `backtest_series` artifact whose
payload `backtest_id` matches the task payload. The CLI must not generate report visuals
from aggregate-only backtest metrics.

Rationale: Task 15 needs a staged runner path, not a broad full-run button. Reporting is
safe to expose only when the previous backtest stage has left auditable factual chart
series. This keeps Report Agent useful for humans while preserving registry-backed
evidence.

Rules:
- Reporting task payloads must include `backtest_id` and `output_dir`.
- `execute-stage --stage reporting` must use `report_agent` with task type
  `write_report`.
- The CLI guard must reject missing or mismatched `backtest_series` sidecars before
  calling Report Agent.
- Report Agent still writes memory summaries only through Memory Agent policy when a
  memory service is supplied; the CLI runner does not write directly to ApeRAG.

Verification:
- `tests/unit/test_cli_data.py::test_experiment_execute_stage_rejects_report_stage_without_factual_artifacts`
- `tests/unit/test_cli_data.py::test_experiment_execute_stage_runs_reporting_with_factual_sidecar`
- `tests/unit/test_check_cli_pipeline.py`
- `scripts/check_cli_pipeline.ps1`
