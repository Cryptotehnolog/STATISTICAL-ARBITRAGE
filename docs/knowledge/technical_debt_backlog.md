# Technical Debt Backlog Memory

This shard summarizes deferred follow-up work that must not be kept only in chat.
The full tracked backlog is `docs/technical_debt.md`.

## Operating Rule

Any "do later" item must be implemented immediately, added to `.kiro/tasks.md`, or added
to `docs/technical_debt.md`. If it matters for agent memory, also update a curated
`docs/knowledge/*.md` shard.

## Active Follow-up Themes

- Ubuntu portability: add Linux-friendly commands or shell wrappers, then verify `uv sync`,
  checks, SQLite, Parquet, ApeRAG, Infisical Docker Compose, graph export, and CCXT smoke
  on Ubuntu before server deployment.
- Ubuntu migration checklist: write exact Ubuntu operator commands, expected paths,
  environment variables, and validation steps before server migration.
- Live CCXT smoke: keep live exchange checks outside fast pre-commit; add the smoke after
  data quality validation exists.
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
- GitHub Actions Node.js 24 migration: CI is green, but GitHub warns Node.js 20 actions are
  deprecated and must be updated before the enforced Node.js 24 transition.
- Infisical recovery: define backup and restore discipline before deleting Docker volumes
  or rotating encryption keys.
- Rust boundary: keep Python-first MVP; introduce Rust only after profiling identifies a
  stable compute hotspot with Python reference tests, stable API boundary, benchmark, and
  Ubuntu/Windows build check.
- Runtime cleanup: keep cleanup manual and scoped to regenerable artifacts.
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
- One-bar data quality reports: decide whether a single OHLCV bar should be invalid input
  or a valid diagnostic `DataQualityReport`; current domain validation rejects equal
  `start_date` and `end_date`.
- Cost Assumption Agent: collect, verify, store, and refresh exchange/account-specific cost
  snapshots; Backtest Agent must not use old planning percentages as trusted market data.
- Agent RAG answer-quality evaluation: add an eval script only after the first agent
  generates answers from ApeRAG context; current checks validate retrieval readiness, not
  final answer quality.
- ApeRAG human graph view: ApeRAG UI is the default inspection path; build a local viewer only
  if the UI proves insufficient.

## Closed Follow-up

- Coverage artifacts are now included in `scripts/clean_runtime_artifacts.ps1`.
- Historical local memory rebuild work was superseded by ApeRAG.
- Decisions memory is split into thematic shards:
  `decisions_memory_aperag.md`, `decisions_infra_ci_secrets.md`, and
  `decisions_data_pipeline.md`.
- ApeRAG graph parity is proven for the main curated collection. `stat-arb-project-knowledge`
  has vector, full-text, and graph indexes active for all 10 curated shards, and graph endpoints
  returned non-empty labels, nodes, and edges.
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
