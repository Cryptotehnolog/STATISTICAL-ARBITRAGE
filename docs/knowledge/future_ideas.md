# Future Ideas

This file collects ideas discovered during development that should be considered later but
should not distract from the current task. Codex should append durable ideas here when they
come up during implementation or review, then the ApeRAG seed command will ingest them.

## IDEA-0001: Chroma compatibility spike

Status: proposed

Idea: Verify whether Chroma has a concrete future role as a separate memory or retrieval
backend, what dependencies are required, and whether it improves the ApeRAG-centered design.

Why later: ApeRAG is the active memory backend. Chroma should be adopted only if it provides
a clear operational or retrieval benefit.

## IDEA-0002: Automate knowledge seed after successful task commits

Status: proposed

Idea: Add an optional local workflow that runs the knowledge seed command after commits that
touch `README.md`, `.kiro/specs/`, `docs/`, or architecture-relevant source files.

Why later: The seed command writes local runtime state and may load embeddings, so it should
remain opt-in until the workflow is proven stable and fast enough.

## IDEA-0003: Benchmark graph extraction providers

Status: proposed

Idea: Add a benchmark command that runs the same tiny graph extraction document
through each configured OpenAI-compatible model or combo and records latency, extracted
nodes, extracted edges, and status.

Why later: The OmniRoute smoke test validates the current active combo, but model ordering
inside `my-ai` should be based on extraction quality and latency measured on the real
ApeRAG graph extraction workload, not only dashboard ping tests.

## IDEA-0004: Split large Kiro design knowledge into curated memory shards

Status: implemented

Idea: Extract durable architecture decisions, interface contracts, and implementation notes
from large Kiro design files into smaller markdown shards under `docs/knowledge/`.

Outcome: Added curated shards for MVP scope, agent memory contracts, research workflow
contracts, and safety/testing acceptance. Added a suggestion script to identify future
large markdown candidates.

## IDEA-0005: Controlled rebuild for clean graph memory

Status: implemented

Idea: Add a safe rebuild command that backs up current memory runtime state, creates clean
runtime storage, and reseeds only `docs/knowledge/*.md` through the OpenAI-compatible
provider.

Outcome: Superseded by ApeRAG curated seeding and graph freshness checks.

## IDEA-0006: Agent execution observability inspired by patoles/agent-flow

Status: proposed

Idea: Evaluate `patoles/agent-flow` as a developer tool for visualizing Codex sessions, then
decide whether to build a project-native agent observability view for Statistical
Arbitrage. The native view should follow the same concept of a live graph, timeline,
transcript, tool calls, and file attention, but use our own name, branding, and data model.

Why later: Real project agents are not implemented yet. Building the UI now would risk
visualizing mostly empty flows. The better moment is after Statistical Testing Agent,
Backtest Agent, Critic Agent, and Memory Agent boundaries start emitting structured events.

Notes: Do not copy the Agent Flow trademark, logo, or exact branding. Apache-2.0 makes the
technical approach reusable, but the project should keep its own design identity.
