# Technical Debt Backlog Memory

This shard summarizes deferred follow-up work that must not be kept only in chat.
The full tracked backlog is `docs/technical_debt.md`.
The human-facing control checklist is `docs/deferred_work_checklist.md`.

## Operating Rule

Any "do later" item must be implemented immediately, added to `.kiro/specs/quant-research-architecture/tasks.md`, or added
to `docs/technical_debt.md`. If it matters for agent memory, also update a curated
`docs/knowledge/*.md` shard.
`scripts/check_deferred_work_checklist.ps1` guards that every open `TD-*` and every
proposed `IDEA-*` is visible in `docs/deferred_work_checklist.md`, so deferred work cannot
quietly stay in memory shards without a human-facing checklist entry.
`scripts/check_memory_quality.ps1` checks memory quality as a layered readiness gate:
auto-start local embedding, verify ApeRAG health/freshness/graph readiness, and run
project-specific semantic QA plus deterministic answer-eval queries for key decisions.
The deterministic answer-eval layer checks required facts and forbidden claims in
retrieved ApeRAG context; it is not a generative LLM judge.

## Active Follow-up Themes

- Agent audit trail: `AgentAuditEvent` and a JSONL writer foundation exist for
  operator-safe audit events. Coordinator lifecycle transitions are the first wired
  production boundary: after successful registry/memory work they can emit sanitized audit
  events with agent/action/reason/status, registry refs, memory refs, and metadata. The CLI
  `experiment advance --audit-log-path` command can persist final-decision audit events to
  a physical JSONL artifact through `AgentAuditJsonlWriter`, and `experiment audit-log`
  can inspect recent audit events read-only without touching the registry. The dashboard
  now has a read-only `Журнал действий агентов` view over the same JSONL audit artifact;
  it must not import the audit writer or mutate registry/memory state. Report Agent now
  emits a sanitized `report_artifacts_generated` audit event after sidecar validation,
  registry artifact persistence, and optional Memory Agent summary. Backtest Agent now
  emits a sanitized `backtest_result_persisted` audit event after data-quality/statistical
  prerequisites, registry result persistence, optional factual series sidecar persistence,
  and optional Memory Agent summary. Statistical Testing Agent now emits a sanitized
  `statistical_test_persisted` audit event after data-quality prerequisites, registry
  statistical-test result persistence, and optional Memory Agent summary. Critic Agent now
  emits a sanitized `critic_review_persisted` audit event after registered backtest
  verification, registry critic-review persistence, and optional Memory Agent summary.
  Future workflow wiring should extend this pattern to other real agent boundaries. Audit
  logs must not carry secrets, tokens, raw logs, or raw payloads.
- Model comparison: keep Kalman, Johansen/VECM, and Phillips-Perron as explicit research
  extensions. Add them through a model-comparison harness with persisted method,
  parameters, dependency versions, out-of-sample evidence, and multiple-testing/conflict
  policy, not as hidden replacements for Engle-Granger.
- Event bus and heartbeat: add these only after real long-running worker agents or
  live/paper services exist. Current CLI/registry workflows should stay deterministic and
  should not gain Redis/RabbitMQ/asyncio infrastructure without a measured workflow need.
- Dashboard research analytics: rolling metrics, spread distributions, and correlation
  heatmaps are useful, but they must read factual registry/sidecar artifacts and remain
  behind the existing read-only dashboard and Coordinator action boundaries.
- External API retry unification: CCXT already has bounded exponential retry tests. Future
  adapters should report retry behavior through a shared failure-handling vocabulary, but
  the project should avoid broad grep-style rules that make one-shot health probes noisy.
- Ubuntu portability: add Linux-friendly commands or shell wrappers, then verify `uv sync`,
  checks, SQLite, Parquet, ApeRAG, Infisical Docker Compose, graph export, and CCXT smoke
  on Ubuntu before server deployment.
- Ubuntu migration checklist: write exact Ubuntu operator commands, expected paths,
  environment variables, and validation steps before server migration.
- Live CCXT smoke: `scripts/check_live_market_data_acceptance.ps1` is the opt-in
  Bybit-first live market-data acceptance smoke. It checks 50 active `USDT` swap symbols by
  default, writes `data/live_market_data_acceptance/report.json`, and stays outside
  pre-commit/CI because live exchanges depend on network state, rate limits, and venue
  behavior.
- Domain conversion helpers: add domain to parquet/storage helpers only when ingestion,
  validation, registry, or CLI code first needs that boundary.
- Runtime memory backend: ApeRAG is the active backend; add alternatives only through a fresh
  design decision.
- Chroma: keep compatibility work parked unless ApeRAG or another future backend needs it.
- Knowledge seeding automation: keep agent-facing memory checks explicit until ApeRAG
  ingestion, vector search, and graph extraction are proven stable. Use
  `scripts/check_aperag_knowledge.ps1` before agent-facing memory work.
- Curated memory changes should use `scripts/seed_aperag_curated.ps1 -Force -EnableGraph`
  followed by `scripts/check_aperag_memory_fresh.ps1 -RequireGraph`.
- Curated shards: keep `docs/knowledge/*.md` synchronized with material Kiro planning
  changes and reseed ApeRAG after updates.
- CLI/dashboard coverage hardening baseline is closed: CI measures `stat_arb.cli` and
  `stat_arb.dashboard`, while dashboard labels, metric formatting, and visible-column
  projection live in a Streamlit-free `stat_arb.dashboard.presentation` helper with
  focused tests. Do not add stricter dashboard-specific gates until UI logic is mature
  enough that the gate improves behavior instead of creating noise.
- Infisical recovery: define backup and restore discipline before deleting Docker volumes
  or rotating encryption keys.
- Rust boundary: keep Python-first MVP; introduce Rust only after profiling identifies a
  stable compute hotspot with Python reference tests, stable API boundary, benchmark, and
  Ubuntu/Windows build check.
- Runtime cleanup: documented in `docs/runtime_maintenance.md`; keep cleanup manual,
  dry-run-first, and scoped to regenerable artifacts. Do not delete `data/aperag`,
  registry data, `infra/infisical/.env`, Docker volumes, or provider runtime state through
  ordinary cleanup.
- GitHub CLI in Codex: use `scripts/gh_no_proxy.ps1` for `gh` commands because this session
  can inherit broken process proxy variables pointing at `127.0.0.1:9`.
- OmniRoute benchmarking: re-run model ordering benchmark when provider behavior changes.
- ApeRAG graph fallback: FreeDeepseekAPI and FreeQwenApi are available only as explicit
  experimental paths through `-CompletionBackend free_deepseek` and
  `-CompletionBackend free_qwen`. Keep OmniRoute as default until a full curated benchmark
  proves a better stable provider order.
- Data ingestion CLI: add user-facing ingestion command only after quality report generation
  and dataset provenance are wired to the registry.
- Data-quality failure memory: keep routing `DataQualityFailureSummary` through
  `MemoryAgentService`, while keeping numeric report details in the registry.
- Cost Assumption Agent: collect, verify, store, and refresh exchange/account-specific cost
  snapshots; Backtest Agent must not use old planning percentages as trusted market data.
- Agent RAG answer-quality evaluation: `scripts/check_memory_quality.ps1` now includes a
  deterministic answer-eval guard for key project-memory questions with required facts and
  forbidden claims. Full generated-answer evaluation remains deferred until the first
  agent produces final answers from ApeRAG context.
- Report chart series sidecars: Backtest Agent can now persist factual chart series as a
  registry-linked `backtest_series` JSON artifact, and Report Agent can load it for visual
  artifacts. CLI reporting execution is now guarded by matching `backtest_series`
  presence. Remaining work is to make the future full experiment runner provide and
  persist these sidecars before queuing reporting work.
- Arbitrary full experiment runner: Task 15.3 is complete for the current safe local CLI
  execution baseline, including lifecycle visibility, explicit stage queuing, mature
  single-stage execution, and the narrow artifact-gated `backtesting,reporting` pipeline.
  A broad full-run command remains deferred until every included stage has explicit payload
  contracts, registry persistence, Coordinator permission checks, and factual artifacts
  required by the next stage.
- ApeRAG human graph view: ApeRAG UI is the default inspection path; build a local viewer only
  if the UI proves insufficient.
- Queue concurrency: before enabling real multi-worker execution, add atomic Coordinator
  task claiming, a race-condition test, and a composite queue index. Parallel pair/window
  execution is blocked on this durable claim boundary.
- Ingestion watermarks and gap repair: Task 15.1 should track dataset freshness and fetch
  missing ranges instead of only taking a caller-provided `since`.
- Regime-break exits: keep them out of backtest behavior until an explicit research policy
  and provenance path exist.
- Performance work: parallel pair scanning, regime vectorization, walk-forward caching, and
  backtest core storage changes must be driven by profiling after a workflow runner exists.
  Dashboard N+1 query reduction and `st.cache_data` should also be driven by measured
  registry growth/latency instead of premature caching.
- Hypothesis novelty caching: add only when repeated ApeRAG novelty lookups become a real
  workflow bottleneck, with explicit cache keys and invalidation.
- Multi-asset roadmap: keep the MVP crypto-first and research-first while staging future
  multi-asset work. A new asset class requires explicit asset class, venue,
  session/calendar, timezone, adjustment policy, cost model, source provenance, and
  data-quality validation. Do not add live execution, hidden thresholds, fixed Kelly
  fractions, ETF iNAV arbitrage, NLP filters, or broad provider integrations before the
  relevant MVP boundaries are stable.
- External evaluation references: `hparreao/Awesome-AI-Evaluation-Guide` and
  `AIAnytime/rag-evaluator` may inform project-native memory and agent evaluation, but
  should not become runtime dependencies without a focused spike. Prefer local curated
  questions, required facts, retrieval/freshness checks, and later answer-quality checks
  over generic BLEU/ROUGE-style scores for project decisions.
- Recursive Language Models: evaluate only as a future sandboxed long-context reasoning
  spike. Do not replace ApeRAG as the durable memory backend unless a read-only comparison
  proves better quality on curated project questions, required facts, source relevance,
  latency, cost, and hallucination checks.
- Context Engine routing: evaluate only after at least two memory/reasoning strategies are
  proven. ApeRAG remains the durable memory path; future RLM-style reasoning may become a
  separate sandboxed mode. Any router must log task type, accuracy/latency/cost constraints,
  source requirements, selected backend, and provenance, and must not bypass Memory Agent
  policy, registry records, Coordinator permissions, or secret boundaries.

## Closed Follow-up

- Coverage artifacts are now included in `scripts/clean_runtime_artifacts.ps1`.
- Historical local memory rebuild work was superseded by ApeRAG.
- Decisions memory is split into thematic shards:
  `decisions_memory_aperag.md`, `decisions_infra_ci_secrets.md`, and
  `decisions_data_pipeline.md`.
- ApeRAG graph parity is proven for the main curated collection. `stat-arb-project-knowledge`
  has vector, full-text, and graph indexes active for the current curated shard set, and
  graph endpoints returned non-empty labels, nodes, and edges. The latest checked curated
  rebuild used 22 shards.
- ApeRAG client boundary exists in `ApeRAGMemoryClient` with typed search/readiness/graph
  contracts and `MemoryWriteRequest` for policy-controlled Memory Agent writes.
- Memory Agent policy layer exists in `MemoryAgentService`; agents must write
  operational memory through policy checks, not directly through `ApeRAGMemoryClient`.
- ApeRAG operational agent memory has a dedicated `stat-arb-agent-memory` collection smoke
  path through `scripts/check_aperag_agent_memory.ps1`.
- The previous local memory backend code, scripts, tests, and dependencies were removed
  after ApeRAG became the active project and operational agent memory backend.
- Duplicate `.kiro/skills` source was removed after the selected Rust skills were installed
  into Codex and confirmed visible in the current session.
- Dashboard Memory Agent read boundary is implemented. Task 16.7b added active Streamlit
  memory search through `MemoryAgentService.query`, sanitized snippets, graph readiness
  metadata, degraded-read status, and guards against direct ApeRAG/HTTP calls in dashboard.
- Dashboard approval actions have an audited Coordinator API. Task 16.8b added
  `CoordinatorApprovalActionRequest` and `apply_coordinator_approval_action`, requiring
  actor/reason provenance and routing approve/reject/quarantine through registry lifecycle
  transition plus Memory Agent policy.
- Dashboard approve/reject/quarantine UI remains intentionally deferred until Task 17
  failure handling provides safe operator feedback, retries, and error-state behavior.
- GitHub Actions Node.js 24 migration is resolved. CI uses `actions/checkout@v6`,
  `actions/setup-python@v6`, and `astral-sh/setup-uv@v8.2.0`, with tests guarding against
  older action versions.
- One-bar data quality report contract is resolved. `DataQualityReport` allows
  `start_date == end_date` only as an invalid diagnostic trace:
  `is_valid=false`, `passed=false`, `invalid_reason="insufficient_data"`, and an
  `insufficient_data` ERROR issue. `Dataset` remains stricter and still requires
  `end_date` after `start_date` for research-ready data.
