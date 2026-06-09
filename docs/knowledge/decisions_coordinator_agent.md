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
