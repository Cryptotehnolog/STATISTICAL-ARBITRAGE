# Technical Debt and Deferred Follow-ups

This file is the tracked backlog for every "do later" item that is too small or too
cross-cutting for the Kiro task plan.

Working rule: no deferred item should stay only in chat. When a decision creates follow-up
work, add it here in the same task unless it is already represented in `.kiro/tasks.md`.

## Open

### TD-0019: Add agent RAG answer-quality evaluation

Status: open

Why deferred: ApeRAG retrieval checks now validate indexed documents, topic-specific
keywords, graph readiness, and expected retrieved markers. A full answer-quality evaluation
requires a real agent boundary that asks ApeRAG and generates a final answer, which does
not exist yet.

Follow-up:
- Add a small eval script after the first agent produces answers from ApeRAG context.
- Use fixed project questions with required facts, forbidden hallucinations, and expected
  decision IDs.
- Keep retrieval readiness checks separate from answer-quality checks so backend health and
  agent reasoning failures are easy to distinguish.

Related tasks: 11.2, 11.4, 13.4.

### TD-0018: Decide one-bar DataQualityReport contract

Status: open

Why deferred: Completing Data Agent property tests exposed that `DataQualityReport`
currently requires `end_date` to be after `start_date`, so one-bar OHLCV validation cannot
produce a valid report. This is not blocking normal research batches, but it is a real
domain boundary decision.

Follow-up:
- Decide whether one-bar datasets are invalid input or valid diagnostic reports.
- If valid, update `DataQualityReport` validation and add an explicit unit/property test.
- If invalid, make `validate_ohlcv_batch` fail early with a clear message before creating
  the report.

Related tasks: 4.3, 4.4.

### TD-0001: Add Ubuntu portability hardening

Status: open

Why deferred: Current development runs on Windows and uses PowerShell scripts.

Follow-up:
- Add Linux-friendly shell commands or `.sh` wrappers for the core local workflow.
- Verify `uv sync`, Ruff, pytest, SQLite, Parquet, ApeRAG Docker Compose, Infisical
  Docker Compose, memory checks, and CCXT smoke on Ubuntu.
- Document the server migration path before deploying to an Ubuntu host.

Related tasks: 18.1, 19.1, 22.4.

### TD-0015: Write detailed Ubuntu migration checklist

Status: open

Why deferred: ApeRAG can answer the high-level Ubuntu portability theme, but the project
does not yet have a concrete operator checklist for server migration.

Follow-up:
- Document exact Ubuntu setup commands for `uv sync`, Docker, Infisical, OmniRoute,
  ApeRAG seeding, embedding endpoint, and checks.
- Include expected paths, environment variables, and validation commands.
- Keep this separate from Windows PowerShell commands or provide equivalent `.sh` wrappers.

Related tasks: TD-0001, 19.1, 22.4.

### TD-0002: Add live CCXT smoke test after data quality validation exists

Status: open

Why deferred: Task 4.1 is intentionally unit-tested with a fake exchange. A live exchange
smoke test depends on network availability, rate limits, and exchange behavior.

Follow-up:
- Add a small opt-in script that fetches a tiny OHLCV sample from one exchange.
- Run it only outside the fast pre-commit baseline.
- Feed the result through the data quality validator once task 4.3 exists.

Related tasks: 4.1, 4.3, 15.1.

### TD-0003: Add domain to parquet/storage conversion helpers at the first real boundary

Status: open

Why deferred: Conversion helpers before a service uses them would be premature mapping.

Follow-up:
- Add helpers only when ingestion, validation, registry, or CLI code first needs to move
  `OHLCVBatch`, `Dataset`, or `DataQualityReport` across parquet or SQLite boundaries.
- Keep Pydantic domain contracts separate from SQLAlchemy persistence models.

Related tasks: 4.3, 4.9, 4.10, 15.1.

### TD-0005: Keep Chroma compatibility parked unless a future backend needs it

Status: open

Why deferred: Chroma was considered for an earlier local memory backend, but ApeRAG is now
the active memory backend.

Follow-up:
- Do not spend time on Chroma while ApeRAG is the active path.
- Reopen only if a future ApeRAG or memory-agent design has a concrete Chroma requirement.

Related tasks: 2.3, 20.1.

### TD-0006: Consider post-commit or scheduled knowledge seeding

Status: open

Why deferred: Knowledge seeding is stateful and can call external LLM providers, so it is
kept outside the fast commit check. A freshness guard exists, but automatic post-commit
seeding is still not enabled.

Follow-up:
- Keep manual/assistant-run seed scripts as the default.
- Consider a local scheduled workflow or post-commit helper only after seed runs are stable
  and bounded.
- Use `scripts/check_aperag_knowledge.ps1` before agent-facing memory work.

Related tasks: 11.1, 11.2.

### TD-0007: Keep curated knowledge shards synchronized with Kiro specs

Status: open

Why deferred: Large Kiro specs are intentionally not seeded directly into ApeRAG.

Follow-up:
- Run the shard suggestion workflow after major `.kiro` planning changes.
- Update `docs/knowledge/*.md` when architecture or requirements materially change.
- Re-seed curated ApeRAG memory after shard updates.

Related tasks: 11.1, 19.3.

### TD-0008: Define local Infisical backup and recovery discipline

Status: open

Why deferred: Infisical is working locally, but key/volume backup policy is not formalized.

Follow-up:
- Document what must be backed up before deleting Docker volumes or rotating encryption
  keys.
- Add a safe restore check for local development when the process is clear.

Related tasks: 2.4, 19.1, 22.4.

### TD-0009: Audit and remove obsolete `.kiro/skills` once Codex skill installation is stable

Status: open

Why deferred: Rust skills were installed into Codex, but the source `.kiro/skills` folder
may still exist as local planning material.

Follow-up:
- Verify Codex can see and use the installed `rust-skills` skill without `.kiro/skills`.
- If the folder is no longer needed, delete it instead of keeping duplicate skill source in
  the project.

Related tasks: Rust optimization path, 22.5.

### TD-0010: Keep Rust as an optimization path, not an early rewrite

Status: open

Why deferred: The MVP still needs Python-first agents, data validation, statistical tests,
and reporting before Rust acceleration has a stable boundary.

Follow-up:
- Use Python for orchestration, agents, RAG, APIs, dashboard, and research flow.
- Introduce Rust only when profiling identifies a stable compute hotspot, likely in
  statistics or backtesting.
- Before adding a Rust module, require a Python reference implementation, stable API
  boundary, unit/property tests, benchmark before/after, and Ubuntu/Windows build check.
- Use the installed `rust-skills` guidance when writing Rust.

Related tasks: 6.x, 7.x, 22.5.

### TD-0011: Add manual maintenance checklist for runtime cleanup

Status: open

Why deferred: Cleanup should not run automatically in pre-commit because runtime state can
be valuable.

Follow-up:
- Document when to run `scripts/clean_runtime_artifacts.ps1`.
- Keep destructive cleanup opt-in and scoped to regenerable artifacts.
- Add Linux equivalent during Ubuntu portability work.

Related tasks: 19.1, TD-0001.

### TD-0013: Add OmniRoute model-order rebenchmark workflow when provider behavior changes

Status: open

Why deferred: The current `my-ai` order was benchmarked on one small graph document, but
external model latency and quality can drift.

Follow-up:
- Re-run the benchmark script when OmniRoute account/model behavior changes.
- Update the combo ordering based on measured seconds, nodes, edges, and ApeRAG graph quality,
  not dashboard ping.

Related tasks: 11.1, 11.4.

### TD-0014: Add service-level data ingestion CLI after report/provenance integration

Status: open

Why deferred: The CCXT adapter exists, but a user-facing ingestion command should not bypass
quality report generation, provenance tracking, or registry writes.

Follow-up:
- Add CLI/script entry points after tasks 4.9 and 4.10 wire validation reports and provenance.
- The command should fetch, validate, persist parquet, and return clear Russian output.

Related tasks: 4.9, 4.10, 15.1.

### TD-0016: Update GitHub Actions to Node.js 24-compatible actions

Status: open

Why deferred: The current CI run passes, but GitHub warns that Node.js 20 actions are
deprecated and will be forced to Node.js 24 by default on June 16, 2026.

Follow-up:
- Check whether newer `actions/checkout`, `actions/setup-python`, and
  `astral-sh/setup-uv` releases explicitly support Node.js 24.
- Update `.github/workflows/ci.yml` action versions or set the recommended compatibility
  environment variable when the upstream actions support it.
- Confirm the next CI run remains green.

Related tasks: 18.1, 18.4.

### TD-0017: Write data-quality validation failures to ApeRAG through Memory Agent

Status: open

Why deferred: Dataset registry persistence now stores passed quality reports and JSON
sidecars, but failed validation summaries should be written through the Memory Agent
boundary rather than coupling storage helpers directly to ApeRAG.

Follow-up:
- Route `DataQualityFailureSummary` through the Memory Agent when that agent owns ApeRAG
  writes.
- Keep structured numeric metrics and report IDs in the registry; store only concise
  lessons, rejection reasons, and links in ApeRAG.

Related tasks: 4.9, 11.1, 11.4.

## Closed

### TD-CLOSED-0001: Make coverage artifacts part of runtime cleanup

Status: closed

Resolution: `scripts/clean_runtime_artifacts.ps1` now removes `coverage.xml` and `htmlcov/`
alongside `.coverage`, pytest caches, Ruff cache, and test temp data.

Closed by: `ca4b224 Add OHLCV data quality domain contracts`.

### TD-CLOSED-0002: Clean rebuild persistent local memory from curated shards

Status: closed

Resolution: Historical local memory storage was backed up and reseeded from curated
`docs/knowledge/*.md` through OmniRoute before the ApeRAG migration superseded that path.

Closed by: local runtime rebuild on 2026-06-03.

### TD-CLOSED-0003: Add local memory freshness guard

Status: closed

Resolution: Added a historical local memory freshness guard before the ApeRAG migration
made ApeRAG the active backend.

Closed by: superseded local memory guard.

### TD-CLOSED-0004: Automate curated local memory clean rebuild

Status: closed

Resolution: Added a historical local clean rebuild wrapper before the ApeRAG migration
made ApeRAG the active backend.

Closed by: superseded local memory rebuild wrapper.

### TD-CLOSED-0005: Split large curated decisions memory shard

Status: closed

Resolution: Replaced the oversized `docs/knowledge/decisions.md` body with a navigation
index and moved durable decisions into focused thematic shards:
`decisions_memory_aperag.md`, `decisions_infra_ci_secrets.md`, and
`decisions_data_pipeline.md`. The curated seed wrapper now caps one document at 12000
characters so future oversized shards are caught earlier.

Closed by: memory optimization task.

### TD-CLOSED-0006: Validate ApeRAG graph parity before removing the previous backend

Status: closed

Resolution: Enabled ApeRAG knowledge graph extraction for the main
`stat-arb-project-knowledge` curated collection, rebuilt graph indexes for all 10
`docs/knowledge/*.md` shards, and verified non-empty labels, nodes, edges, search, and
freshness checks.

Closed by: `scripts/enable_aperag_curated_graph.ps1` and
`scripts/check_aperag_memory_fresh.ps1`.

### TD-CLOSED-0007: Remove previous local memory code path

Status: closed

Resolution: Removed the old local memory backend from runtime dependencies, `src`,
PowerShell wrappers, and unit tests after ApeRAG project memory, graph parity, and
operational agent memory smoke checks were committed. Added pre-commit guards for
user-facing legacy memory commands and agent-facing legacy imports.

Closed by: `scripts/check_no_legacy_memory_backend_user_surface.ps1` and
`scripts/check_no_legacy_memory_backend_imports.ps1`.

### TD-CLOSED-0008: Decide ApeRAG human graph inspection path

Status: closed

Resolution: ApeRAG UI is the default human inspection path for graph memory. A custom local
viewer is no longer a prerequisite for removing the old local viewer workflow; add a new
task only if ApeRAG UI proves insufficient.

Closed by: ApeRAG migration cleanup.
