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

## IDEA-0007: Evaluate Jesse MCP as an external trading-tool reference

Status: proposed

Idea: Use `bkuri/jesse-mcp` as a reference for future MCP tool-server boundaries around
trading workflows, especially pairs trading, risk analysis, async job tracking, and
strategy certification gates.

What is useful:
- Pairs-trading tool taxonomy: correlation matrix, pairs backtest, factor analysis,
  regime detection, cointegration-oriented workflow ideas, and strategy generation.
- Risk-tool taxonomy: Monte Carlo, VaR, stress testing, leverage review, drawdown recovery,
  and portfolio concentration checks.
- Operational patterns: MCP tool registration, health endpoint, long-running job progress,
  and certification-style gates before paper/live promotion.

What must not be copied blindly:
- Hidden defaults for capital, fees, leverage, thresholds, windows, and simulation counts.
- Mock fallback results that could be mistaken for real research evidence.
- Live trading tools or order/session controls before the project has explicit paper/live
  execution policy, kill switch, approval gates, and registry audit logging.
- Direct LLM tool access that bypasses Coordinator, registry, Critic, or Memory Agent
  policy boundaries.

Why later: The current MVP already has a native research pipeline. Jesse MCP should be
evaluated after dashboard and failure-handling baselines exist, and only as a sandboxed
external adapter or checklist source. It should not replace the current Backtest,
Statistical Testing, Hypothesis, Critic, Coordinator, or Memory Agent boundaries.

## IDEA-0008: Evaluate external RAG and AI evaluation repositories as methodology references

Status: proposed

Idea: Use external evaluation resources as methodology input for project-native memory and
agent evaluation checks.

References:
- `hparreao/Awesome-AI-Evaluation-Guide`: useful as a broad guide for evaluating LLM,
  RAG, and agentic systems, especially its separation of retrieval quality, generation
  quality, domain-specific evaluation, and multi-agent evaluation.
- `AIAnytime/rag-evaluator`: useful as a simple reference for traditional
  reference-answer metrics such as BLEU, ROUGE, BERTScore-style similarity, readability,
  and diversity.

What to adopt:
- Keep project-native memory quality checks split into runtime health, freshness, graph
  readiness, retrieval checks, and later answer-quality checks.
- Use curated project questions with required facts and forbidden hallucinations before
  adding any LLM-as-judge dependency.
- Treat reference-answer metrics as optional future diagnostics, not as proof that project
  memory is correct.

What not to adopt blindly:
- Do not add `rag-evaluator` as a dependency before a small spike proves value on our
  ApeRAG/project-memory workload.
- Do not rely on BLEU/ROUGE-style overlap as the main quality signal for project decisions;
  our memory needs decision recall, citation/source relevance, and hallucination checks.
- Do not send secrets, raw logs, registry dumps, or metric-heavy payloads to external eval
  providers.

Why later: The immediate need is a lightweight local memory-quality guard over curated
project decisions. Full answer-quality evaluation should wait until real agents generate
answers from ApeRAG context.
