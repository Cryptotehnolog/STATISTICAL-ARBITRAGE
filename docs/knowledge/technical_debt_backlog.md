# Technical Debt Backlog Memory

This shard summarizes deferred follow-up work that must not be kept only in chat.
The full tracked backlog is `docs/technical_debt.md`.

## Operating Rule

Any "do later" item must be implemented immediately, added to `.kiro/tasks.md`, or added
to `docs/technical_debt.md`. If it matters for agent memory, also update a curated
`docs/knowledge/*.md` shard.

## Active Follow-up Themes

- Ubuntu portability: add Linux-friendly commands or shell wrappers, then verify `uv sync`,
  checks, SQLite, Parquet, LightRAG, Infisical Docker Compose, graph export, and CCXT smoke
  on Ubuntu before server deployment.
- Ubuntu migration checklist: write exact Ubuntu operator commands, expected paths,
  environment variables, and validation steps before server migration.
- Live CCXT smoke: keep live exchange checks outside fast pre-commit; add the smoke after
  data quality validation exists.
- Domain conversion helpers: add domain to parquet/storage helpers only when ingestion,
  validation, registry, or CLI code first needs that boundary.
- Runtime memory backend: revisit FAISS versus NanoVectorDB once memory-agent workflows
  are implemented.
- Chroma: run a compatibility spike before advertising Chroma as an active LightRAG backend.
- Knowledge seeding automation: consider post-commit or scheduled local seeding only after
  seed runs are stable and bounded. Use `scripts/check_lightrag_memory_fresh.ps1` before
  agent-facing memory work.
- Curated memory changes should use `scripts/rebuild_lightrag_curated.ps1` for persistent
  storage recovery, because incremental apply can create duplicate source docs.
- Curated shards: keep `docs/knowledge/*.md` synchronized with material Kiro planning
  changes and reseed LightRAG after updates.
- Infisical recovery: define backup and restore discipline before deleting Docker volumes
  or rotating encryption keys.
- Kiro skills cleanup: verify Codex can use installed `rust-skills`, then remove duplicate
  `.kiro/skills` source if no longer needed.
- Rust boundary: keep Python-first MVP; introduce Rust only after profiling identifies a
  stable compute hotspot.
- Runtime cleanup: keep cleanup manual and scoped to regenerable artifacts.
- LightRAG viewer: improve filters, labels, and readability as graph size grows.
- OmniRoute benchmarking: re-run model ordering benchmark when provider behavior changes.
- Data ingestion CLI: add user-facing ingestion command only after quality report generation
  and dataset provenance are wired to the registry.

## Closed Follow-up

- Coverage artifacts are now included in `scripts/clean_runtime_artifacts.ps1`.
- Persistent LightRAG was rebuilt from curated `docs/knowledge/*.md` shards after backing
  up the previous runtime storage. Post-rebuild status had 7 processed docs, 0 failed docs,
  0 duplicate failed docs, valid graph export, and successful control queries.
- LightRAG memory freshness guard now checks curated seed freshness, OmniRoute/doc_status,
  graph export, human-facing viewer export, and a control query in one command.
- Curated LightRAG clean rebuild now has automation in `scripts/rebuild_lightrag_curated.ps1`.
