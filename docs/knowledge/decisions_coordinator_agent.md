# Coordinator Agent Decisions

This shard records durable Coordinator Agent design decisions for the statistical
arbitrage system.

## DEC-0058: Start Coordinator with an explicit lifecycle state-machine boundary

Status: accepted

Decision: Task 13 begins with a small Coordinator lifecycle boundary instead of a broad
multi-agent workflow. The first boundary owns experiment state transitions over the
existing registry `experiments` table and writes lifecycle summaries through
`MemoryAgentService`.

The allowed lifecycle is:

```text
NEW -> DATA_VALIDATION -> STATISTICAL_TESTING -> BACKTESTING -> CRITIC_REVIEW -> REPORTING -> FINAL_DECISION
```

Rationale: A task queue, retry scheduler, tool permission system, and final decision
workflow are useful, but implementing them before a strict state machine would create a
large orchestration layer without a stable contract. The lifecycle boundary makes invalid
workflow jumps impossible and keeps recovery state in the registry.

Rules:
- Coordinator must persist lifecycle state in the structured registry.
- Coordinator must write operational memory only through `MemoryAgentService`.
- Coordinator must not call `ApeRAGMemoryClient` or ApeRAG document write APIs directly.
- Final rejected or quarantined decisions require a reason.
- Hidden lifecycle defaults are forbidden in Coordinator request contracts.

Verification:
- `tests/unit/test_coordinator_agent.py`
- `scripts/check_coordinator_agent_boundaries.ps1`
- `scripts/check_coordinator_pipeline.ps1`

## DEC-0059: Persist Coordinator task queue state in the registry

Status: accepted

Decision: Coordinator task queue state is represented by durable `coordinator_tasks`
registry rows. Each task stores experiment link, task type, assigned agent, explicit
priority, explicit retry budget, attempt count, status, payload, last error, and timestamps.
Claiming work also requires an explicit `CoordinatorResourcePolicy` with global and
per-agent running-task limits.

Rationale: The Coordinator must recover after process restarts and must not hide retry or
priority assumptions in runtime defaults. The first Task 13.1 boundary is intentionally a
small queue contract, not a full scheduler. It supports priority-based claim, resource
limit checks, completion, retryable failure, exhausted failure, and listing running tasks
that need recovery after a restart.

Rules:
- Task requests must provide priority and max attempts explicitly.
- Claiming tasks must provide `CoordinatorResourcePolicy` explicitly.
- The queue must block claims that exceed either global or per-agent running-task limits.
- Queue state belongs in the structured registry, not in ApeRAG.
- ApeRAG receives only policy-safe Coordinator lifecycle summaries, not raw queue payloads.
- Background scheduler behavior is intentionally out of scope for this boundary.

Verification:
- `tests/unit/test_coordinator_agent.py`
- `scripts/check_coordinator_pipeline.ps1`
