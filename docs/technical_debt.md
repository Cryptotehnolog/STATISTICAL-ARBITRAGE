# Technical Debt and Deferred Follow-ups

This file is the tracked backlog for every "do later" item that is too small or too
cross-cutting for the Kiro task plan.

Working rule: no deferred item should stay only in chat. When a decision creates follow-up
work, add it here in the same task unless it is already represented in `.kiro/tasks.md`.

## Open

### TD-0001: Add Ubuntu portability hardening

Status: open

Why deferred: Current development runs on Windows and uses PowerShell scripts.

Follow-up:
- Add Linux-friendly shell commands or `.sh` wrappers for the core local workflow.
- Verify `uv sync`, Ruff, pytest, SQLite, Parquet, FAISS/NanoVectorDB, LightRAG, Infisical
  Docker Compose, graph export, and CCXT smoke on Ubuntu.
- Document the server migration path before deploying to an Ubuntu host.

Related tasks: 18.1, 19.1, 22.4.

### TD-0015: Write detailed Ubuntu migration checklist

Status: open

Why deferred: LightRAG can answer the high-level Ubuntu portability theme, but the project
does not yet have a concrete operator checklist for server migration.

Follow-up:
- Document exact Ubuntu setup commands for `uv sync`, Docker, Infisical, OmniRoute,
  LightRAG seeding, graph export, and checks.
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

### TD-0004: Revisit FAISS versus NanoVectorDB for runtime memory

Status: open

Why deferred: NanoVectorDB is currently smoother for repeated Windows seed runs, while
FAISS remains the intended local MVP vector backend.

Follow-up:
- Re-test FAISS metadata replacement behavior after memory-agent workflows exist.
- Decide whether runtime experiment memory should use FAISS, NanoVectorDB, or a different
  backend.

Related tasks: 11.1, 11.2, 11.4.

### TD-0005: Run a Chroma compatibility spike before advertising Chroma as active

Status: open

Why deferred: Chroma was planned, but the current LightRAG environment did not expose a
working Chroma storage path during setup.

Follow-up:
- Verify the installed LightRAG version supports Chroma in this project.
- If useful, add an explicit Chroma profile and tests.
- Do not make Chroma part of the default runtime until the spike passes.

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
- Use `scripts/check_lightrag_memory_fresh.ps1` before agent-facing memory work.

Related tasks: 11.1, 11.2.

### TD-0007: Keep curated knowledge shards synchronized with Kiro specs

Status: open

Why deferred: Large Kiro specs are intentionally not seeded directly into LightRAG.

Follow-up:
- Run the shard suggestion workflow after major `.kiro` planning changes.
- Update `docs/knowledge/*.md` when architecture or requirements materially change.
- Re-seed curated LightRAG memory after shard updates.

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

### TD-0012: Add LightRAG viewer readability improvements as graph size grows

Status: open

Why deferred: The local HTML viewer exists and is usable, but larger graphs may need more
human-facing controls.

Follow-up:
- Revisit filters, presets, search, labels, and layout once real project memory grows.
- Keep all human-facing viewer labels in Russian.

Related tasks: 11.2, 16.7.

### TD-0013: Add OmniRoute model-order rebenchmark workflow when provider behavior changes

Status: open

Why deferred: The current `my-ai` order was benchmarked on one small LightRAG document, but
external model latency and quality can drift.

Follow-up:
- Re-run the benchmark script when OmniRoute account/model behavior changes.
- Update the combo ordering based on measured seconds, nodes, and edges, not dashboard ping.

Related tasks: 11.1, 11.4.

### TD-0014: Add service-level data ingestion CLI after report/provenance integration

Status: open

Why deferred: The CCXT adapter exists, but a user-facing ingestion command should not bypass
quality report generation, provenance tracking, or registry writes.

Follow-up:
- Add CLI/script entry points after tasks 4.9 and 4.10 wire validation reports and provenance.
- The command should fetch, validate, persist parquet, and return clear Russian output.

Related tasks: 4.9, 4.10, 15.1.

### TD-0015: Split large curated decisions memory shard

Status: open

Why deferred: `docs/knowledge/decisions.md` is now large enough to make clean LightRAG
rebuilds slow and close to curated seed limits.

Follow-up:
- Split decisions into smaller curated shards by theme, for example architecture,
  memory/LLM, data pipeline, and CI.
- Keep the shard names stable so LightRAG source IDs remain human-readable.
- Rebuild LightRAG after the split and confirm graph export plus query smoke still pass.

Related tasks: 2.3, 18.1, 19.1.

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

## Closed

### TD-CLOSED-0001: Make coverage artifacts part of runtime cleanup

Status: closed

Resolution: `scripts/clean_runtime_artifacts.ps1` now removes `coverage.xml` and `htmlcov/`
alongside `.coverage`, pytest caches, Ruff cache, and test temp data.

Closed by: `ca4b224 Add OHLCV data quality domain contracts`.

### TD-CLOSED-0002: Clean rebuild persistent LightRAG from curated shards

Status: closed

Resolution: Backed up the previous persistent `data/lightrag` and
`data/lightrag_seed_manifest.json` under `data/backups/`, then reseeded only
`docs/knowledge/*.md` through OmniRoute. Post-rebuild checks passed with 7 processed docs,
0 failed docs, 0 duplicate failed docs, valid graph export, and successful control queries.

Closed by: local runtime rebuild on 2026-06-03.

### TD-CLOSED-0003: Add LightRAG memory freshness guard

Status: closed

Resolution: Added `scripts/check_lightrag_memory_fresh.ps1` to verify curated seed
freshness, OmniRoute/doc_status, graph export, human-facing viewer export, and a control
query in one command.

Closed by: `scripts/check_lightrag_memory_fresh.ps1`.

### TD-CLOSED-0004: Automate curated LightRAG clean rebuild

Status: closed

Resolution: Added `scripts/rebuild_lightrag_curated.ps1` to backup current persistent
LightRAG runtime storage, reseed only `docs/knowledge/*.md`, and run the memory freshness
guard.

Closed by: `scripts/rebuild_lightrag_curated.ps1`.
