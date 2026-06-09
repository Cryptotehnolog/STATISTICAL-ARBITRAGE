# Knowledge Decisions: Memory And ApeRAG

This shard contains durable decisions about ApeRAG, curated project memory, operational
agent memory, OmniRoute, and Memory Agent boundaries.

## DEC-0019: Make ApeRAG the active project memory backend

Status: accepted

Decision: Use ApeRAG as the active backend for project memory, curated knowledge search,
operational agent memory, and knowledge graph extraction. The previous local memory backend
code and scripts were removed after ApeRAG agent-memory integration was committed.

Rationale: ApeRAG is already running through Docker with vector, full-text, and graph indexes
for the main `stat-arb-project-knowledge` curated collection. The full curated parity check
passed with non-empty labels, nodes, and edges, so new memory automation should target ApeRAG.

Alternatives considered: Continue optimizing the old local backend; delete it immediately
after the first ApeRAG smoke; keep both systems indefinitely.

Risks: ApeRAG depends on its Docker stack and OmniRoute for graph extraction. Keep memory
checks explicit and keep agent writes behind `MemoryAgentService`.

## DEC-0020: Remove the legacy local memory backend

Status: accepted

Decision: Remove the old local memory backend code path from `src`, `scripts`, tests, and
runtime dependencies. Keep only historical planning notes outside active code paths.

Rationale: ApeRAG now has project-memory, graph parity, a typed client boundary,
`MemoryAgentService`, and an operational agent-memory smoke path. Keeping two active memory
backends would confuse agents and operators.

Alternatives considered: Keep a dormant fallback; leave scripts but remove docs; wait until
all future agents exist.

Risks: Reintroducing a fallback would require a fresh design decision and new tests.

## DEC-0021: Use a lightweight ApeRAG graph viewer for human inspection

Status: accepted

Decision: Use `docs/knowledge_graph/index.html` as the human-facing lightweight 2D viewer
for the ApeRAG project knowledge graph. The viewer reads a generated `graph.json` exported
from the active `stat-arb-project-knowledge` collection. The desktop shortcut should
refresh the export before opening the local viewer, but it must not trigger reseeding or
LLM graph rebuilds on every browser launch.

Rationale: Human graph inspection should reflect the active ApeRAG backend and should not
depend on the removed legacy memory backend. Refreshing the export is fast and keeps the
viewer current without coupling ordinary viewing to stateful memory writes. The viewer
must avoid WebGL, 3D force layouts, and continuous animation loops because they can consume
excessive CPU on the target local development machine.

Alternatives considered: Keep the old local-memory graph viewer; use Gephi Desktop or
Gephi Lite; rebuild the ApeRAG graph every time the viewer opens; use a 3D WebGL force
graph as the default human viewer.

Risks: The viewer depends on ApeRAG API availability during export and on browser access
to local `graph.json`. Keep `scripts/check_aperag_graph_export.ps1` as the fast guard for
export health, and keep tests that forbid reintroducing 3D/WebGL/requestAnimationFrame into
the default viewer.

## DEC-0003: Keep knowledge seeding explicit but automatic

Status: accepted

Decision: Knowledge seeding should be a dedicated command that automatically gathers curated
project sources and writes changed documents to ApeRAG. It should not run as part of the
fast unit check.

Rationale: Seeding loads the embedding model and writes runtime state, so coupling it to
`scripts/check.ps1` would make every commit check slower and stateful.

Risks: Developers must run the seed command when they want local ApeRAG memory updated.
This can later be automated through a post-commit or scheduled local workflow if needed.

## DEC-0007: Use OmniRoute as the active graph LLM gateway

Status: accepted

Decision: Use OmniRoute in Docker as the active OpenAI-compatible gateway for graph
entity/relation extraction. Keep the project integration generic through the
`openai_compatible` provider and the `my-ai` combo instead of hard-coding one upstream
model.

Rationale: The earlier local CPU extractor was too slow for routine development.
OmniRoute through `my-ai` is faster on small graph extraction documents and provides model
fallback.

Alternatives considered: Keep a local CPU extractor as the primary path; use kiro-gateway
directly; wire each model as a separate container.

Risks: OmniRoute depends on external provider availability and account/session health.
Keep provider smoke tests explicit.

Benchmark result: On the same tiny extraction document, the measured model order
was `kiro/deepseek-3.2` (14 nodes / 15 edges), `kiro/glm-5` (13 nodes / 13 edges),
`kiro/claude-sonnet-4.5` (9 nodes / 13 edges), `kiro/minimax-m2.5` (10 nodes / 12 edges),
then `kiro/qwen3-coder-next` (14 nodes / 9 edges). Prefer this order for `my-ai` until a
new benchmark says otherwise.

## DEC-0008: Keep OmniRoute knowledge seeding opt-in and size-limited

Status: accepted

Decision: Use a dedicated OmniRoute seed wrapper that defaults to dry-run and applies
per-document and total character limits. Require an explicit apply flag before writing to
ApeRAG through the LLM-backed provider.

Rationale: Curated project sources include large Kiro design documents. Sending those
documents through the LLM extraction path accidentally would make seed runs slow, expensive,
and hard to review.

Alternatives considered: Make the base seed command dry-run by default; seed every changed
document through OmniRoute automatically.

Risks: Large but useful sources may be skipped until they are split into smaller curated
documents.

## DEC-0022: Add FreeDeepseekAPI only as an explicit experimental graph fallback

Status: accepted

Decision: Keep OmniRoute as the default ApeRAG graph completion gateway, but add
FreeDeepseekAPI as an explicit experimental fallback selected with
`-CompletionBackend free_deepseek`. FreeDeepseekAPI must run in its own Docker container
named `stat-arb-free-deepseek`, expose an OpenAI-compatible endpoint on local port `9655`,
and keep DeepSeek Web session files under ignored runtime storage
`data/free_deepseek/`.

Rationale: OmniRoute can become unavailable when its upstream accounts or quotas fail.
ApeRAG graph rebuilds should have a tested fallback integration path, but it must not
silently replace the default backend or become a hidden production dependency.

Alternatives considered: Delete OmniRoute immediately; embed FreeDeepseekAPI inside the
ApeRAG container; switch all agent LLM traffic to FreeDeepseekAPI; keep retrying OmniRoute
without a fallback boundary.

Risks: FreeDeepseekAPI depends on a local DeepSeek Web session and may break when the web
service changes. The start script must fail fast when `deepseek-auth.json` is missing so
Docker does not enter a noisy restart loop. Treat this backend as experimental until
`scripts/check_free_deepseek.ps1` and an ApeRAG graph rebuild smoke pass.

Benchmark result: `deepseek-chat` remains the preferred FreeDeepseekAPI fallback model for
curated ApeRAG graph rebuilds. A full rebuild with sequential FreeDeepseek mode completed
in about 169 seconds and produced 230 nodes / 241 edges. A full rebuild with
`deepseek-v3` completed but took about 587 seconds and produced 203 nodes / 206 edges.
Short chat latency alone is not enough to choose the model because ApeRAG graph extraction
is a different workload.

## DEC-0025: Add FreeQwenApi as a third explicit experimental graph fallback

Status: accepted

Decision: Keep OmniRoute as the default ApeRAG graph completion gateway and keep
FreeDeepseekAPI as the first verified fallback, but add FreeQwenApi as a third explicit
experimental fallback selected with `-CompletionBackend free_qwen`. FreeQwenApi must run
in its own Docker container named `stat-arb-free-qwen`, expose an OpenAI-compatible endpoint
on local port `3264`, and keep Qwen Web session files under ignored runtime storage
`data/free_qwen/`.

Rationale: FreeDeepseekAPI graph rebuilds worked, but `deepseek-chat` behaved sequentially
on the ApeRAG workload. FreeQwenApi exposes a page pool and may provide better concurrency,
so it is worth testing as a fallback without replacing the default provider.

Alternatives considered: Replace OmniRoute immediately; put FreeQwenApi inside the ApeRAG
container; skip Qwen because DeepSeek already works; make Qwen the default backend before
benchmarking the full curated rebuild.

Risks: FreeQwenApi depends on a local Qwen Web session and on an upstream repository that
currently does not ship a `package-lock.json`, so the Docker image uses
`npm install --omit=dev --no-audit --no-fund` instead of `npm ci`. Treat this backend as
experimental until `scripts/check_free_qwen.ps1` and bounded ApeRAG graph smoke checks pass
reliably. Do not make it the default without a full curated benchmark and dependency review.

Verification result: `scripts/check_free_qwen.ps1` passed against `qwen3.7-plus`, and
`scripts/check_aperag_graph_smoke.ps1 -CompletionBackend free_qwen -CompletionModel
qwen3.7-plus` produced an active smoke graph with non-empty labels, nodes, and edges.

## DEC-0026: Keep OmniRoute primary and keep web-session providers as explicit fallbacks

Status: accepted

Decision: Use OmniRoute `my-ai` as the primary ApeRAG graph completion backend after
the clean OmniRoute reinstall and fresh Kiro OAuth connection. Keep FreeDeepseekAPI and
FreeQwenApi installed only as explicit fallback backends selected with
`-CompletionBackend free_deepseek` or `-CompletionBackend free_qwen`; do not silently
promote either fallback to default.

Rationale: A clean OmniRoute state plus a fresh AWS/Kiro account restored real chat and
ApeRAG graph extraction. `scripts/check_aperag_graph_smoke.ps1 -CompletionBackend
omniroute -CompletionModel my-ai` completed with a non-empty graph, proving that OmniRoute
is again suitable for bounded ApeRAG graph work. FreeDeepseekAPI and FreeQwenApi remain
useful insurance, but both depend on browser/web sessions that can expire or change without
notice.

Operational policy: Run `scripts/check_omniroute_readiness.ps1` before OmniRoute-backed
ApeRAG graph rebuilds. Treat quota, cooldown, missing `my-ai`, missing models, failing chat,
or recent `402`/quota log patterns as early warning signs. If OmniRoute readiness fails,
use FreeDeepseekAPI as the first fallback for reliability and FreeQwenApi as the experimental
fallback for concurrency testing.

Alternatives considered: Delete FreeDeepseekAPI and FreeQwenApi after OmniRoute recovery;
make FreeQwenApi the default because it may offer parallelism; rotate providers silently
inside scripts.

Risks: OmniRoute can still fail when Kiro quota expires or AWS/Kiro auth changes. Web-session
fallbacks can fail when upstream sites change their UI or session model. Keep backend
selection explicit so failures are visible and reproducible.

## DEC-0027: Make Memory Agent the agent-facing memory boundary

Status: accepted

Decision: Agent-facing modules must depend on `MemoryAgentService` and the `MemoryBackend`
adapter boundary instead of calling ApeRAG write APIs directly. `ApeRAGMemoryClient`
remains the concrete v1 backend, but the Memory Agent owns record typing, collection
routing, retrieval-quality checks, filtering, and degraded write handling.

Rationale: Project knowledge and operational agent memory have different lifecycles.
Architecture decisions, market knowledge, and manual notes belong in
`stat-arb-project-knowledge`; hypotheses, test summaries, backtest conclusions, critic
reviews, and lessons belong in `stat-arb-agent-memory`. Keeping this routing inside
Memory Agent prevents future agents from duplicating policy logic or writing raw data into
ApeRAG.

Operational policy: Memory writes must be concise and reference registry IDs for precise
metrics. The policy blocks secrets, raw prompts, raw logs, large dataset dumps, and
metric-heavy payloads. If ApeRAG write operations fail after a request passes policy, the
request may be written to a durable JSONL write-ahead queue for later operator-controlled
replay instead of being silently dropped.

Verification: `scripts/check_memory_agent_pipeline.ps1` runs deterministic Memory Agent
contract tests and boundary guards without requiring ApeRAG runtime health. Use
`-IncludeRuntimeHealth` only when an operator wants to include the external ApeRAG smoke.

Alternatives considered: Let every agent call ApeRAG directly; store all memory in one
collection; drop failed memory writes and rely only on registry records; couple ordinary
commit checks to ApeRAG runtime availability.

Risks: Queued writes still require a future replay workflow and operator review. Keep
agent answer-quality evaluation separate from retrieval readiness until a real RAG answer
boundary exists.

## DEC-0028: Memory reads may degrade through an explicit read-through cache

Status: accepted

Decision: `MemoryAgentService` supports an optional `MemoryReadThroughCache`. Successful
queries can populate a local JSON cache, and temporary ApeRAG read failures can return the
last cached result with `degraded=True` and a failure reason. If no cache is configured or
no cached result exists, the ApeRAG error is raised.

Rationale: Coordinator and future agents should not silently lose all context when ApeRAG
has a short outage, but first-read failures must remain visible. Degraded reads are
therefore explicit, auditable, and marked in the result instead of being treated as fresh
memory.

Alternatives considered: Always fail reads; hide backend failures behind empty results;
store a broad persistent memory mirror.

Risks: Cached results can become stale. Agent decisions must treat degraded memory as lower
confidence and preserve the degraded flag in run artifacts when it affects a decision.

## DEC-0009: Use curated knowledge shards instead of seeding large Kiro specs directly

Status: accepted

Decision: Keep `.kiro` specs as planning source documents and create smaller curated
markdown shards under `docs/knowledge/` for ApeRAG seeding.

Rationale: Large design and requirements files contain useful context but are too bulky for
routine LLM-backed graph extraction. Curated shards produce cleaner entities and
relationships while preserving source references back to the original specs.

Alternatives considered: Split the `.kiro` specs themselves; seed the full design and
requirements files directly; rely only on README and decisions.

Risks: Curated shards can drift from source specs if not reviewed after major planning
changes. Use the shard suggestion script to find large sections that deserve extraction.

## DEC-0018: Keep data-quality failure summaries as pure contracts

Status: accepted

Decision: Use `DataQualityFailureSummary` and `summarize_data_quality_failure` as a pure
contract for policy-controlled Memory Agent writes. The helper converts a failed `DataQualityReport`
into a concise summary with issue codes and a registry reference, without calling ApeRAG
or writing storage state.

Rationale: Data Agent and registry code should not depend directly on an LLM gateway.
Structured metrics stay in the registry, while `MemoryAgentService` receives only a small,
memory-safe failure summary.

Alternatives considered: Write failed validation summaries directly to ApeRAG from the
quality validator; store all issue details in memory; wait until Memory Agent exists
before defining the contract.

Risks: The summary is intentionally concise. If later Memory Agent workflows need richer
context, add fields explicitly rather than passing the full raw report to ApeRAG.
