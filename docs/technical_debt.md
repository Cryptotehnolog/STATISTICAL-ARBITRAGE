# Technical Debt and Deferred Follow-ups

This file is the tracked backlog for every "do later" item that is too small or too
cross-cutting for the Kiro task plan.

Working rule: no deferred item should stay only in chat. When a decision creates follow-up
work, add it here in the same task unless it is already represented in `.kiro/specs/quant-research-architecture/tasks.md`.

## Open

### TD-0044: Implement validated Kalman, Johansen, and Phillips-Perron scenarios one by one

Status: open; Johansen candidate implemented

Current baseline: Johansen is implemented as the first real candidate scenario through
`statsmodels.tsa.vector_ar.vecm.coint_johansen`. The model-comparison harness requires
explicit `det_order` and `k_ar_diff`, supports only the Johansen critical-value alpha
levels exposed by statsmodels (`0.10`, `0.05`, `0.01`), stores trace/max-eigen evidence in
artifact details, and does not invent a p-value. The result is research evidence only and
does not produce an approval decision.

Why still open: Kalman hedge-ratio/state-space benchmarking and Phillips-Perron
stationarity checks are not implemented. Phillips-Perron is not available in the currently
installed `statsmodels 0.14.6`, so adding it requires a focused dependency decision rather
than silently pulling in a new package.

Follow-up:
- Add Kalman only after choosing explicit state/noise parameter policy and persistence
  fields for hedge-ratio path evidence.
- Add Phillips-Perron only after a dependency/spike confirms API quality, licensing,
  Windows/Ubuntu compatibility, and deterministic test behavior.
- Persist method parameters, dependency versions, sample windows, p-values/statistics,
  out-of-sample evidence, and any failure reason in the model-comparison JSON artifact.
- Keep Engle-Granger as the required baseline until a separate Critic/Coordinator policy
  explicitly changes promotion rules.
- Do not let a candidate method produce an approval decision directly.

Related tasks: TD-0040, 6.x, 10.3, 24.2.

### TD-0043: Unify external API retry policy across data and runtime adapters

Status: open

Why deferred: `CCXTOHLCVSource` already has bounded exponential retry behavior and tests,
while Task 17 has a separate `RetryPolicy`/`plan_api_retry` contract for failure handling.
The current behavior is safe enough, but the project will become easier to audit if
external API adapters report retry attempts through one shared policy vocabulary.

Follow-up:
- Keep the existing CCXT retry tests passing.
- Reuse or adapt `RetryPolicy` for future data adapters without changing current
  deterministic ingestion behavior.
- Do not add a broad "all HTTP calls must use retry" grep rule; prefer adapter-specific
  tests so CLI health checks and explicit one-shot probes do not become noisy.

Related tasks: 4.1, 17.x, 22.1.

### TD-0042: Add dashboard research analytics panels after stable factual artifacts

Status: open

Why deferred: The Streamlit dashboard is intentionally small and read-only. Adding rolling
Sharpe, spread distributions, correlation heatmaps, and richer strategy diagnostics is
valuable, but these views should read factual registry/sidecar artifacts rather than
invent chart data from aggregate metrics.

Follow-up:
- Add rolling metrics, spread distribution, and correlation heatmap panels only from
  persisted factual artifacts.
- Keep dashboard actions behind Coordinator APIs and Memory Agent read boundaries.
- Add focused projection/helper tests instead of brittle browser-only UI assertions.

Related tasks: 12.x, 15.3, 16.x, TD-0023.

### TD-0041: Add event bus and heartbeat only after long-running workers exist

Status: open

Why deferred: The current architecture uses deterministic CLI workflows, registry-backed
state, Coordinator queue contracts, and explicit stage execution. A Redis/RabbitMQ/asyncio
event bus or heartbeat layer would be premature until agents become long-running workers
or live/paper services that can actually go stale.

Follow-up:
- Add heartbeat only when agent processes are persistent rather than short-lived service
  calls.
- Add an event bus only when workflow execution needs asynchronous fan-out, live data,
  or multiple concurrent workers.
- Keep Coordinator registry state as the source of truth, and do not let events bypass
  registry, Memory Agent policy, or permission checks.

Related tasks: 13.x, 15.x, 17.x, 21.x, TD-0031.

### TD-0040: Add explicit model-comparison harness for Kalman, Johansen, and Phillips-Perron

Status: resolved baseline

Resolution: Added an explicit model-comparison harness in
`stat_arb.statistical.model_comparison`. It requires exactly one Engle-Granger baseline,
records alternative methods only as explicitly named research scenarios, persists benchmark
evidence through a JSON sidecar plus `ReportArtifact`, and returns no promotion decision.
Kalman, Johansen, and Phillips-Perron are registered as scenario identifiers but remain
`not_implemented` until separate validated method tasks implement them.

Closed baseline by: `scripts/check_model_comparison_pipeline.ps1`.

Follow-up: TD-0044 owns real candidate-method implementation and validation.

Related tasks: 6.x, 10.3, 15.x, 24.2.

### TD-0039: Wire agent audit events through real workflows

Status: baseline complete for current mature boundaries

Current baseline: The project now has an operator-safe `AgentAuditEvent` contract, local
JSONL writer foundation, Coordinator lifecycle transitions can write sanitized audit events
through an optional audit writer after successful registry/memory boundary work, and the
operator CLI `experiment advance` command can persist final-decision audit events to a
physical JSONL artifact with `--audit-log-path`. The CLI also has a read-only
`experiment audit-log` inspection command for recent audit events. The read-only
dashboard now has a `Журнал действий агентов` section that reads the same JSONL audit log
as a safe projection, without importing the audit writer or mutating registry/memory
state. Report Agent can now emit a sanitized `report_artifacts_generated` audit event
after matching `backtest_series` validation, registry artifact persistence, and optional
Memory Agent summary. Backtest Agent can now emit a sanitized
`backtest_result_persisted` audit event after data-quality/statistical prerequisites,
registry backtest persistence, optional factual series sidecar persistence, and optional
Memory Agent summary. Statistical Testing Agent can now emit a sanitized
`statistical_test_persisted` audit event after data-quality prerequisites, registry
statistical-test persistence, and optional Memory Agent summary. Critic Agent can now
emit a sanitized `critic_review_persisted` audit event after registered backtest
verification, registry critic-review persistence, and optional Memory Agent summary.
Hypothesis Agent can now emit a sanitized `hypotheses_generated` audit event after
rule-based screening, registry hypothesis persistence, and optional Memory Agent summary.
Full future workflow wiring should still be staged so audit logs are not duplicated,
noisy, or allowed to leak secrets/raw payloads.

Follow-up:
- Treat new agent/workflow boundaries as a separate audit-hardening task when they become
  active execution boundaries.
- Keep exact numeric artifacts in registry/sidecars; audit logs should point to them.
- Keep dashboard audit inspection read-only; any future approval action must continue to
  go through the audited Coordinator API.

Related tasks: 11.x, 13.x, 15.x, 16.x, 17.x.

### TD-0038: Add arbitrary full experiment runner only after all stages have mature boundaries

Status: open

Why deferred: Task 15.3 now has safe local experiment execution commands for lifecycle
visibility, explicit stage queuing, mature single-stage execution, and a narrow
artifact-gated `backtesting,reporting` pipeline. A broad "run the whole experiment" button
would still be premature because `data_validation`, arbitrary stage chains, final decision
routing, and future factual artifact handoffs are not all mature enough to be executed
blindly.

Follow-up:
- Add full-run orchestration only after every included stage has explicit payload
  contracts, registry persistence, Coordinator permission checks, and factual artifacts
  required by the next stage.
- Keep `run-pipeline` narrow and fail-closed until the next stage chain has the same
  evidence quality as `backtesting,reporting`.
- Do not let a future full runner write directly to ApeRAG, mutate registry rows outside
  approved service boundaries, or generate reports from aggregate-only metrics.
- Include the selected stages, payload hashes, artifact IDs, registry IDs, and reproducible
  command in the run manifest.

Related tasks: 15.3, 15.7, 12.x, 13.x, 14, TD-0023.

### TD-0037: Stage multi-asset statistical arbitrage after MVP boundaries

Status: open

Why deferred: External reviews correctly pushed the project toward serious multi-asset
statistical arbitrage, including cross-asset spreads, factor exposure, session-aware data,
portfolio risk allocation, and asset-class-specific adjustments. Implementing that now as
a broad rewrite would bypass the current research MVP boundaries and add too many
untested data, risk, and execution assumptions at once.

Follow-up:
- Add multi-leg signal contracts only after the current pair pipeline and failure
  handling baseline are stable.
- Before adding a second asset class, require asset class, venue, session calendar,
  timezone, adjustment policy, cost model, source provenance, and data-quality validation.
- Add factor exposure diagnostics and portfolio risk allocation as explicit policy
  contracts before autonomous sizing.
- Keep futures roll logic, equity corporate actions, ETF basket/iNAV logic, NLP filters,
  and broker execution behind separate approved tasks.
- Keep fixed Kelly fractions and hidden adaptive thresholds out of runtime defaults.

Related tasks: 17.x, 19.4, 21.x, 22.5, 24.x, DEC-0092.

### TD-0035: Wire dashboard approvals to audited Coordinator action after failure UX exists

Status: open

Why deferred: `apply_coordinator_approval_action` and Task 17 failure handling contracts
are implemented and tested, but the dashboard remains intentionally read-only. Adding
approve/reject/quarantine controls should be a focused dashboard UX task with clear
operator feedback, registry transition status, and memory-write result display.

Follow-up:
- Add dashboard controls that call only `apply_coordinator_approval_action`.
- Require actor, reason, and explicit decision selection in the UI.
- Show registry transition result and policy-safe memory-write status.
- Keep ad-hoc registry mutation and direct ApeRAG writes forbidden in Streamlit code.

Related tasks: 16.8b, 17.x, 13.4, 13.5.

### TD-0033: Compare native pairs pipeline against Jesse MCP ideas without adopting it as a dependency

Status: open

Why deferred: `bkuri/jesse-mcp` contains useful pairs-trading, risk-analysis, MCP tool, job
tracking, and certification-gate ideas, but direct adoption would add another trading
framework boundary, hidden defaults, mock fallback ambiguity, and live-trading tools before
the MVP has dashboard, failure handling, and paper/live policy controls.

Follow-up:
- After Task 16/17 baseline, run a read-only comparison of our Hypothesis, Statistical
  Testing, Backtest, Critic, Coordinator, and future Risk tasks against Jesse MCP pairs and
  risk tool taxonomy.
- Extract only missing validated capabilities, such as richer pair-screening diagnostics,
  factor analysis, Monte Carlo risk scenarios, job progress views, or certification gates.
- Keep every adopted idea behind explicit configs, registry provenance, Coordinator
  permissions, and Memory Agent policy.
- Do not install Jesse MCP as a runtime dependency or expose live trading tools unless a
  separate paper/live design is approved.

Related tasks: 9.x, 10.x, 13.x, 16.x, 17.x, 21.x, 24.x, IDEA-0007.

### TD-0032: Stage future paper/live trading roles after research MVP boundaries

Status: open

Why deferred: Regime Switch Detector, Execution and Slippage Simulator, and Dynamic Risk
and Capital Allocator are important for paper/live trading, but implementing them as full
agents now would expand v1 beyond a research platform and blur the boundary between
simulation and real capital risk.

Follow-up:
- Implement execution and slippage simulation first as a deterministic Backtest/Critic
  service boundary using explicit verified/manual-approved cost and liquidity inputs.
- Add regime robustness checks in the research pipeline before any live risk-off or model
  switching behavior.
- Add explicit capital allocation and exposure policy contracts before autonomous sizing.
- Keep all future paper/live memory writes behind Memory Agent policy and all exact
  metrics, approvals, and artifacts in the registry/sidecars.
- Revisit full paper/live agents only after dashboard, failure handling, reproducibility,
  and MVP validation are stable.

Related tasks: 7.x, 10.5, 16.x, 17.x, 21.x, 22.5, DEC-0081, DEC-0082, DEC-0083, DEC-0084.

### TD-0031: Add durable queue concurrency controls before multi-worker execution

Status: open

Why deferred: Coordinator queue claiming is currently a local MVP boundary backed by
SQLite and no real parallel worker runner exists yet. The current read-then-write claim is
acceptable for deterministic local checks, but it is not enough for multiple independent
worker processes.

Follow-up:
- Before enabling real multi-process or distributed workers, add atomic task claiming.
- Use optimistic locking/version checks or a database-specific row lock strategy.
- Add a race-condition test that proves two workers cannot claim the same pending task.
- Add a composite queue index for `(agent_name, status, priority, created_at)` as part of
  the same storage/migration hardening.
- Treat ProcessPool/joblib pair scanning as blocked until this queue claim behavior is
  hardened.

Related tasks: 13.1, 13.5, 14, 15.x.

### TD-0030: Add ingestion watermarks and gap repair

Status: open

Why deferred: The CCXT source and service pipeline can fetch a bounded batch and validate
missing bars, but the user-facing ingestion workflow does not yet maintain dataset
freshness, watermarks, or automatic repair of detected gaps.

Follow-up:
- Add registry-backed ingestion watermarks per symbol/source/timeframe.
- Detect missing ranges before and after fetches.
- Add explicit gap-repair commands that fetch only missing windows.
- Keep live exchange checks outside ordinary pre-commit.

Related tasks: 4.x, 15.1.

### TD-0029: Add regime-break exit only through explicit research policy

Status: open

Why deferred: Regime detection exists as a statistical/critic signal, but using regime
breaks to exit positions changes strategy behavior and must not be hidden inside the
backtest core.

Follow-up:
- Add a named regime-exit policy only after the research workflow has explicit policy,
  provenance, and tests for how regime breaks affect entries/exits.
- Store the policy in the backtest reproducibility manifest and registry-side provenance.
- Keep current regime detection as diagnostic evidence until that policy exists.

Related tasks: 6.x, 7.x, 10.3, 15.6.

### TD-0028: Add profile-guided performance work after workflow runner exists

Status: open

Why deferred: Parallel pair scanning, rolling-window caching, regime vectorization, and
columnar backtest result storage can improve performance, but optimizing before a real
workflow runner and profiler output risks making the code harder to trust.

Follow-up:
- Add profiling around pair screening, statistical tests, walk-forward windows, regime
  detection, and backtest core after the first workflow runner exists.
- Use the results to decide whether to add ProcessPool/joblib parallelism, vectorize
  `regime.py`, cache overlapping walk-forward calculations, or change backtest core storage.
- Investigate dashboard snapshot N+1 queries and `st.cache_data` only after registry size
  makes dashboard latency measurable.
- Keep Python reference behavior and property tests before any Rust or columnar rewrite.

Related tasks: 13.x, 15.x, 18.x, TD-0010.

### TD-0027: Cache hypothesis novelty lookups after real agent workflow exists

Status: open

Why deferred: Hypothesis novelty checks can query ApeRAG, but there is no long-running
agent workflow that repeatedly asks the same novelty questions yet.

Follow-up:
- Add a bounded cache keyed by normalized pair, query, memory backend, and curated
  collection/version when repeated novelty lookups become measurable latency.
- Do not silently cache LLM reasoning outputs without provenance and invalidation rules.
- Keep OmniRoute/FreeDeepseek/FreeQwen fallback behavior explicit.

Related tasks: 9.x, 11.x, 15.x, TD-0013.

### TD-0023: Persist chart-ready report series sidecars

Status: mostly closed

Why deferred: Task 12 can generate deterministic report charts when equity, drawdown,
z-score, cost, and trade series are explicitly provided. The current registry-backed
Report Agent path correctly refuses to fabricate charts from aggregate metrics. The
Backtest Agent now persists chart-ready factual series as registry-linked
`backtest_series` JSON sidecars when the runner payload provides them, and Report Agent
loads those sidecars automatically. CLI `execute-stage --stage reporting` is now enabled
behind a guard that requires a matching `backtest_series` sidecar before report
generation.

Follow-up:
- Wire the future full experiment runner so every real backtest stage provides and
  persists factual series sidecars by default.
- Keep aggregate registry metrics separate from chart-ready time series.

Related tasks: 12.1, 12.4, 13.x, 14.x.

### TD-0020: Add Cost Assumption Agent for verified market costs

Status: open

Why deferred: Task 7.2 implements the math boundary for PnL and cost attribution. Fetching,
verifying, storing, and refreshing real exchange/account cost snapshots is a separate data
acquisition and provenance workflow.

Follow-up:
- Add a Cost Assumption Agent or service that collects exchange fee schedules, funding
  assumptions, borrow assumptions, and liquidity/slippage estimates.
- Store cost snapshots in the registry with source, verification time, venue, market type,
  status, and confidence.
- Prevent Backtest Agent from using stale, rejected, or unverified cost snapshots unless a
  human explicitly approves a manual assumption.
- Keep old Kiro planning percentages out of runtime defaults and agent memory as trusted
  market data.

Related tasks: 7.2, 7.8, 10.5, 11.1, 15.6.

### TD-0019: Add agent RAG answer-quality evaluation

Status: open

Why deferred: ApeRAG retrieval checks now validate indexed documents, topic-specific
keywords, graph readiness, expected retrieved markers, and a deterministic answer-eval
guard with required facts plus forbidden claims for key project-memory questions. A full
answer-quality evaluation still requires a real agent boundary that asks ApeRAG and
generates a final answer, which does not exist yet.

Follow-up:
- Extend the existing deterministic eval after the first agent produces answers from
  ApeRAG context.
- Use fixed project questions with required facts, forbidden hallucinations, and expected
  decision IDs.
- Keep retrieval readiness, deterministic project-memory answer eval, and generated-answer
  quality eval separate so backend health and agent reasoning failures are easy to
  distinguish.

Related tasks: 11.2, 11.4, 13.4.

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

Status: closed

Resolution: `scripts/check_live_market_data_acceptance.ps1` is an opt-in Bybit-first live
market-data acceptance smoke. It checks 50 active `USDT` swap symbols by default, requires
all 50 to return OHLCV rows, and writes `data/live_market_data_acceptance/report.json`.

Boundary:
- Run it only outside the fast pre-commit baseline and CI.
- Treat failures as live readiness failures, not deterministic code regressions.
- Keep future exchange expansion explicit: Bybit first, then Binance, OKX, and Deribit when
  their contracts are deliberately added.

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

## Resolved

### TD-RESOLVED-0036: Harden CLI and dashboard coverage gates incrementally

Status: resolved

Resolution: CI already measures `stat_arb.cli` and `stat_arb.dashboard`. Added
`stat_arb.dashboard.presentation` as a Streamlit-free helper module for dashboard column
labels, metric normalization, numeric means, and visible-column projection, with focused
unit coverage. No stricter dashboard-specific coverage gate was added because the current
UI layer is still intentionally small and read-only; premature UI gates would be noisy.

Closed by: Task 19 readiness CLI/dashboard testability baseline.

Related tasks: 15.x, 16.x, 18.1, 18.4.

### TD-RESOLVED-0011: Add manual maintenance checklist for runtime cleanup

Status: resolved

Resolution: Added `docs/runtime_maintenance.md` and linked it from README/repository
structure docs. Runtime cleanup is documented as a manual dry-run-first maintenance action
using `scripts/clean_runtime_artifacts.ps1`; it is not part of pre-commit and must not
delete persistent ApeRAG data, registry state, Infisical `.env`, Docker volumes, or
provider runtime state.

Closed by: Task 19 readiness cleanup documentation.

Related tasks: 19.1, TD-0001.

### TD-RESOLVED-0018: Decide one-bar DataQualityReport contract

Status: resolved

Resolution: `DataQualityReport` now allows `start_date == end_date` so one-bar OHLCV
validation can produce a diagnostic trace instead of crashing, but it must be
`is_valid=false`, `passed=false`, `invalid_reason="insufficient_data"`, and carry an
`insufficient_data` ERROR issue. Reversed ranges are still rejected. `Dataset` remains
stricter and still requires `end_date` after `start_date`, so a one-bar diagnostic cannot
be mistaken for research-ready data.

Closed by: one-bar DataQualityReport contract task.

Related tasks: 4.3, 4.4.

### TD-RESOLVED-0016: Update GitHub Actions to Node.js 24-compatible actions

Status: resolved

Resolution: `.github/workflows/ci.yml` now uses `actions/checkout@v6`,
`actions/setup-python@v6`, and `astral-sh/setup-uv@v8.2.0`. Unit tests guard against
regressing to the older action versions, and GitHub CI is green after the update.

Closed by: `9082302 Update GitHub Actions Node runtime`.

Related tasks: 18.1, 18.4.

### TD-RESOLVED-0035: Add audited Coordinator approval transition API for dashboard actions

Status: resolved

Resolution: Added `CoordinatorApprovalActionRequest` and
`apply_coordinator_approval_action`. Manual approve/reject/quarantine actions now require
actor and reason provenance, persist through the Coordinator lifecycle transition API, and
write only policy-safe summaries through Memory Agent policy. Dashboard code remains free
of direct registry mutations.

Closed by: Task 16.8b.

### TD-0034: Add read-only Memory Agent search boundary for dashboard queries

Status: resolved

Resolution: Added a dashboard-facing Memory Agent query wrapper and active Streamlit
search controls. Dashboard queries now go through `MemoryAgentService.query`, return
sanitized snippets, graph readiness metadata, degraded-read status, and source metadata
keys, while keeping dashboard code free of `ApeRAGMemoryClient`, raw HTTP calls, and
direct document endpoint usage.

Closed by: Task 16.7b.

### TD-0022: Ruflo read-only swarm audit policy

Status: resolved

Original concern: Ruflo can improve review quality through specialized agent swarms, but
its full install path includes MCP, hooks, daemon/background workers, and environment-level
automation. That is too broad for the main project while secrets, ApeRAG, Docker runtime,
and trading/backtest boundaries are active.

Resolution: The first read-only swarm audit for Tasks 1-11 was completed and the accepted
findings were triaged through the normal Codex workflow before implementation. The project
keeps Ruflo/swarm review as a checkpoint audit method, not as an autonomous developer.

Ongoing policy:
- Use swarm audit only at explicit checkpoints: completed task groups, risky refactors,
  security/secret changes, memory-backend changes, or pre-release review.
- Keep swarm access read-only. Do not allow write access, direct ApeRAG writes, Infisical
  secrets, Docker socket access, Git push/commit, autopilot, daemon, or auto-fix.
- Treat findings as review input, not truth. Codex must verify each finding against code,
  tests, docs, and project decisions before changing anything.
- Prefer isolated copy/worktree execution when the audit tool needs local project files.

Related tasks: 11.x, 18.1, 19.3.

### TD-0021: Harden ApeRAG graph rebuild against OmniRoute provider outages

Status: resolved

Why deferred: During Critic Agent task 10.5, ApeRAG vector/fulltext seeding worked but
knowledge-graph rebuild repeatedly failed because OmniRoute `my-ai` chat returned HTTP
503 with `ALL_ACCOUNTS_INACTIVE`. The project code and local ApeRAG containers were not
the root cause; the active LLM combo had no usable upstream account at that moment.

Resolution: OmniRoute was reinstalled with a clean Docker volume, a fresh Kiro OAuth
connection was added, `my-ai` was rebuilt without stale account-bound IDs, and
`scripts/check_omniroute_readiness.ps1` now checks Docker health, stale state, models,
chat, latency, provider quota/cooldown/auth status, recent log risk patterns, and token
expiry before long ApeRAG graph rebuilds. The restored OmniRoute path passed bounded
ApeRAG graph smoke and a full curated graph rebuild.

Follow-up:
- Keep the OmniRoute combo/account readiness check outside ordinary pre-commit checks.
- FreeDeepseekAPI is verified as an explicit fallback, but full curated rebuilds are
  sequential and slower than an ideal provider path.
- FreeQwenApi is now available as a third explicit experimental fallback after local Qwen
  Web auth and `scripts/check_free_qwen.ps1`, but it must remain non-default until a full
  curated benchmark and dependency review are complete.
- Keep bounded retries in `scripts/enable_aperag_curated_graph.ps1`, and fail clearly
  after the retry budget is exhausted.

Related tasks: 10.5, 11.1, 11.4, TD-0013.

## Closed

### TD-CLOSED-0010: Write data-quality validation failures through Memory Agent

Status: closed

Resolution: `write_data_quality_failure_memory` routes concise `DataQualityFailureSummary`
content through `MemoryAgentService`. Task 11 now owns the agent-facing Memory Agent
boundary, record filtering, collection routing, and degraded write queue contracts.
Structured numeric metrics and report IDs remain in the registry.

Closed by: Task 11 Memory Agent boundary.

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

### TD-CLOSED-0009: Remove obsolete `.kiro/skills` after Codex skill installation

Status: closed

Resolution: Selected Rust skills from `actionbook/rust-skills` were installed into
`C:\Users\Victor\.codex\skills`, the current Codex session can see them, and duplicate
`.kiro/skills` source is absent from the project.

Closed by: Codex skills installation audit.
