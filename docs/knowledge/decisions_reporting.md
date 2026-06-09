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
