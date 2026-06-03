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
contract for future Memory Agent writes. The helper converts a failed `DataQualityReport`
into a concise summary with issue codes and a registry reference, without calling ApeRAG
or writing storage state.

Rationale: Data Agent and registry code should not depend directly on an LLM gateway.
Structured metrics stay in the registry, while the future Memory Agent receives only a
small, memory-safe failure summary.

Alternatives considered: Write failed validation summaries directly to ApeRAG from the
quality validator; store all issue details in memory; wait until Memory Agent exists
before defining the contract.

Risks: The summary is intentionally concise. If later Memory Agent workflows need richer
context, add fields explicitly rather than passing the full raw report to ApeRAG.
