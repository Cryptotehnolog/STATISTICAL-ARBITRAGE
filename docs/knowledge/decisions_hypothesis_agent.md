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

## DEC-0043: Make novelty scoring deterministic before LLM ranking

Status: accepted

Decision: Implement the first novelty check as a deterministic score. The Hypothesis Agent
queries SQLite for exact rejected pair matches and queries ApeRAG through an injected
search protocol for similar past hypotheses. `HypothesisNoveltyConfig` explicitly controls
memory search depth, similarity threshold, memory-match penalty, and registry-rejection
penalty. Generated hypotheses persist `novelty_score` and `similar_hypotheses` in the
registry.

Rationale: Novelty is a research signal, not a truth oracle. A transparent deterministic
score is easier to test, audit, and reproduce than an immediate LLM judgment. Future
LLM/rerank behavior can build on the same evidence boundary after baseline behavior is
stable.

Alternatives considered: Ask an LLM to judge novelty immediately; treat any registry match
as automatic rejection; skip novelty until full Memory Agent.

Risks: The current score only handles exact rejected registry pairs and high-similarity
ApeRAG hits. Task 9.3 must add explicit graph/linking behavior for retests and related
hypotheses without converting novelty into hidden decision logic.

## DEC-0044: Link hypotheses without making final decisions

Status: accepted

Decision: Hypothesis linking uses explicit `HypothesisLinkingConfig`. When novelty evidence
finds similar prior hypotheses, the Hypothesis Agent stores those references in
`similar_hypotheses`. If an exact rejected registry pair exists, the new hypothesis is
flagged with the configured retest status and rationale text. The agent also writes a
policy-approved memory request asking ApeRAG to relate the new hypothesis to prior
hypotheses.

Rationale: Linking is relationship metadata, not a trading decision. The Hypothesis Agent
should surface retests and similar ideas, while Critic/Coordinator decide whether to reject,
quarantine, approve, or run another experiment.

Alternatives considered: Automatically reject exact retests; write graph edges directly to
ApeRAG; store links only in memory without registry references.

Risks: The current link request is represented as a memory document, not a low-level graph
edge mutation. Keep the Memory Agent policy boundary active and add richer graph APIs only
if ApeRAG exposes a safe first-class relationship-write endpoint.

## DEC-0045: Treat Hypothesis Agent edge cases as regression boundaries

Status: accepted

Decision: Keep explicit unit coverage for reverse/case-insensitive rejected pair matching,
duplicate ApeRAG memory references, novelty score floor at zero, and no-link behavior when
there are no similar hypotheses. Exact rejected pair matching uses case-insensitive symbol
comparison in both pair orientations.

Rationale: Hypothesis Agent output feeds later statistical testing and critic review.
Small linking or novelty regressions can quietly create duplicate experiments, missed
retests, or noisy memory. These edge cases are cheap to test now and expensive to debug
after Coordinator Agent orchestration exists.

Alternatives considered: Leave these as manual review cases; rely only on broad pipeline
checks; move them to slow property tests.

Risks: The tests cover deterministic boundaries, not semantic quality of ApeRAG retrieval.
Future answer-quality or retrieval-quality evaluation should stay separate from these
unit tests.

## DEC-0046: Hypothesis batch screening requires explicit p-value correction

Status: accepted

Decision: `generate_rule_based_hypotheses` requires caller-supplied candidate p-values and
an explicit `MultipleTestingMethod` plus `candidate_alpha` in `HypothesisGenerationConfig`.
The agent applies correction across the screened candidate batch and persists only
candidates whose corrected p-value is within the explicit alpha.

Rationale: Correlation, sector, and market-cap filters are screening heuristics, not
statistical approval. If a batch of candidate pairs is persisted as generated hypotheses,
the multiple-testing correction decision must be visible and reproducible instead of
hidden in planning text.

Alternatives considered: Let Hypothesis Agent compute p-values from correlation alone;
skip p-values until Statistical Testing Agent; persist all correlation-screened pairs.
Correlation alone is not enough, and skipping correction made Task 9.1 look complete while
the statistical gate was missing.

Risks: Upstream pair-screening workflows must provide candidate p-values. That is
intentional: p-value provenance belongs to the workflow that computed them.
