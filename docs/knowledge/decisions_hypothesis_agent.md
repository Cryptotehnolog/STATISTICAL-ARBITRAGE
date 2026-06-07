# Knowledge Decisions: Hypothesis Agent

This shard contains durable decisions about Hypothesis Agent boundaries, deterministic
pair generation, registry persistence, and Memory Agent writes.

## DEC-0041: Start Hypothesis Agent with deterministic rule-based generation

Status: accepted

Decision: Implement the first Hypothesis Agent boundary as deterministic rule-based pair
generation. The boundary accepts explicit asset universe metadata, explicit pair
correlations, and an explicit `HypothesisGenerationConfig`. It filters candidates by
same-sector requirement, absolute correlation, market-cap bounds, and maximum pair count,
then persists selected `Hypothesis` rows to the SQLite registry.

Rationale: The project needs a reliable agent boundary before broad autonomous hypothesis
generation. Deterministic rules make the behavior testable, reproducible, and safe to
connect to downstream statistical testing. LLM-generated hypotheses, novelty scoring, and
graph linking are separate tasks and should not be mixed into the first boundary.

Alternatives considered: Start with LLM-generated hypotheses; generate pairs ad hoc inside
the CLI; store generated ideas only in ApeRAG.

Risks: The current boundary does not calculate novelty or link similar hypotheses. Tasks
9.2 and 9.3 must add those features without bypassing the registry or Memory Agent policy
layer.

## DEC-0042: Keep Hypothesis Agent writes behind registry and Memory Agent policy

Status: accepted

Decision: The Hypothesis Agent writes structured hypothesis records to SQLite and writes
concise rationale summaries through `MemoryAgentService`-compatible `MemoryWriteRequest`.
It must not call `ApeRAGMemoryClient` or `write_markdown_document` directly.

Rationale: The registry remains the source of truth for hypothesis IDs, assets, status,
source, created-by, and novelty metadata. ApeRAG stores only high-level memory summaries
and links back to the registry. This keeps operational memory useful without filling it
with raw screening tables or hidden configuration.

Alternatives considered: Direct ApeRAG writes from the agent; no memory write until the
full Memory Agent exists; storing every correlation and rejected candidate in memory.

Risks: If future novelty/linking code bypasses this policy, agent memory can become noisy
or unsafe. Keep `scripts/check_hypothesis_agent_boundaries.ps1` active in pre-commit and
CI.
