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

## IDEA-0009: Evaluate Recursive Language Models as a sandboxed long-context reasoning spike

Status: proposed

Idea: Compare Recursive Language Models (RLMs) against the current ApeRAG-backed memory
path for a narrow project-memory workload, without replacing the active backend.

References:
- `alexzhang13/rlm`: official reference implementation for Recursive Language Models.
- `Recursive Language Models` paper: describes an inference-time strategy where the model
  treats long context as an external environment and recursively inspects/decomposes it.

What to adopt:
- Treat RLMs as a possible future reasoning harness for very large design/audit documents,
  long experiment traces, or deep code-review context.
- If tested, run it only in an isolated sandbox and compare against ApeRAG on the same
  curated project questions, required facts, source relevance, latency, cost, and
  hallucination checks.
- Keep ApeRAG as the durable memory store; RLMs may become an inference/query strategy, not
  the source of truth.

What not to adopt blindly:
- Do not replace ApeRAG with RLMs before a timeboxed sandbox spike proves better quality on
  our project-memory workload.
- Do not allow an RLM local REPL to access project files, secrets, Docker socket, Infisical,
  or registry writes without a strict sandbox and read-only policy.
- Do not treat RLM marketing claims as production readiness.

Why later: The project currently needs stable, inspectable, source-backed memory for
agents. RLMs are promising for long-context reasoning, but they add execution/sandbox risk
and should be evaluated only after the existing memory quality guard is stable.

## IDEA-0010: Evaluate a Context Engine routing layer

Status: proposed

Idea: Evaluate a project-native Context Engine that routes memory/reasoning requests by
workload instead of forcing every task through the same backend.

Reference:
- Vikram Moorjani, `RAG vs. RLMs vs. Context Engines: The Real Split in Enterprise AI`
  argues that the durable advantage is not choosing RAG or RLMs globally, but routing by
  workload constraints such as latency, accuracy, cost, and error tolerance.

What to adopt:
- Treat ApeRAG/RAG as the durable source-backed memory and fast retrieval path.
- Treat RLMs as a possible future long-context reasoning mode for high-accuracy,
  batch-style audit/research tasks after sandbox evaluation.
- Add a router only after there are at least two proven memory/reasoning modes and a
  measurable need to choose between them.
- Make routing decisions explicit, logged, reproducible, and tied to policy: task type,
  required accuracy, latency budget, cost budget, source requirements, and sandbox level.

What not to adopt blindly:
- Do not build a routing platform before the current ApeRAG memory and agent answer-quality
  evaluation are proven.
- Do not hide routing choices from registry/audit trails; invisible user experience is fine,
  invisible provenance is not.
- Do not let a future Context Engine bypass Memory Agent policy, registry records,
  Coordinator permissions, or secret boundaries.
- Do not route financial decisions to an experimental RLM path without strict read-only
  sandboxing and human approval.

Why later: The project currently has one active durable memory backend, ApeRAG. A Context
Engine becomes valuable only when multiple evaluated strategies exist and agents start
making real workload-specific memory/reasoning calls.
