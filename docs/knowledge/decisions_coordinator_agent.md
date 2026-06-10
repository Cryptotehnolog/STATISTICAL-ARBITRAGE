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

## DEC-0068: Start experiment CLI with lifecycle visibility before a full runner

Status: accepted

Decision: Task 15.3 starts with `stat-arb experiment list`,
`stat-arb experiment status`, and `stat-arb experiment advance`. The `advance` command
uses `transition_experiment_lifecycle` so the CLI cannot skip Coordinator state-machine
rules or mutate `experiments.status` directly.

Rationale: A full `experiment run` command needs real stage execution, artifact sidecars,
registry writes, and Memory Agent policy summaries. Adding that as one broad command would
risk bypassing boundaries that already exist. The first CLI slice gives operators status
visibility and a safe lifecycle control surface while keeping stage execution open until a
runner can preserve factual evidence.

Rules:
- Experiment CLI commands must read lifecycle state from the structured registry.
- Lifecycle changes must go through the Coordinator transition boundary.
- Full runner commands must not be documented as available until they are implemented and
  covered by `scripts/check_cli_pipeline.ps1`.
- Future stage execution must persist factual artifacts before Report Agent graphing or
  summaries depend on them.

Verification:
- `tests/unit/test_cli_data.py`
- `scripts/check_cli_pipeline.ps1`

## DEC-0063: Treat Coordinator integration smoke as the Task 13 checkpoint

Status: accepted

Decision: `check_coordinator_pipeline.ps1` is the single local checkpoint for Task 13.
It must run the Coordinator boundary guard, unit contracts, its own static guard, and a
local SQLite integration smoke that exercises queue claim, tool permission enforcement,
final decision persistence, and Memory Agent policy summary in one scenario.

Rationale: The Coordinator has several small boundaries that are individually tested, but
future workflow code needs confidence that they work together. A local integration smoke is
fast, deterministic, and does not depend on Docker, ApeRAG runtime, or external LLM
providers. It gives us end-to-end confidence without turning Task 13 into a full
multi-agent runner.

Rules:
- Coordinator integration tests must use local registry state and a fake Memory Agent
  service, not live ApeRAG.
- The checkpoint must include `tests/integration/test_coordinator_agent_integration.py`.
- The checkpoint must stay in pre-commit and CI.
- New Coordinator workflow behavior should extend this checkpoint instead of creating a
  separate untracked script.

Verification:
- `tests/integration/test_coordinator_agent_integration.py`
- `tests/unit/test_check_coordinator_pipeline.py`
- `scripts/check_coordinator_pipeline.ps1`

## DEC-0064: Use a Task 14 all-agents checkpoint before CLI workflows

Status: accepted

Decision: Before building CLI/workflow commands, Task 14 introduces
`scripts/check_agents_checkpoint.ps1` as the local checkpoint that composes implemented
agent boundaries from Tasks 1-13. The command runs existing pipeline guards and a local
cross-agent integration smoke through Hypothesis, Statistical Testing, Backtest, Critic,
Report, and Coordinator boundaries using one in-memory registry and a fake Memory Agent
service.

Rationale: The project now has several reliable but separate agent boundaries. Moving
straight to CLI workflows without a cross-agent checkpoint would risk discovering registry
ID mismatches, memory-policy bypasses, or final-decision inconsistencies too late. The
checkpoint is intentionally not a full workflow runner; it proves compatibility while
keeping orchestration behavior for the next stage.

Rules:
- Task 14 must stay deterministic and local; no live ApeRAG, Docker, exchange, or LLM
  dependency is allowed in the cross-agent smoke.
- Agent memory writes must use `MemoryAgentService`-compatible requests with registry
  references.
- Structured details remain in the registry; memory receives concise summaries only.
- CLI/workflow tasks should extend this checkpoint rather than creating a disconnected
  validation path.

Verification:
- `scripts/check_agents_checkpoint.ps1`
- `tests/integration/test_agents_checkpoint_integration.py`
- `tests/unit/test_check_agents_checkpoint.py`

## DEC-0062: Enforce agent tool permissions with an explicit allow list

Status: accepted

Decision: Coordinator owns a small `AgentToolPermissionPolicy` boundary before the future
workflow runner starts invoking tools on behalf of agents. The policy maps each agent name
to explicit `AgentToolPermissionScope` values covering registry, memory, data artifacts,
reports, and secrets. Every permission request must include an operator-readable reason.

Rationale: Agent orchestration should fail closed. Without a dedicated permission boundary,
future workflow code could accidentally let a reporting or critic component read secrets,
write data artifacts, or bypass registry/memory separation. A small allow-list contract is
enough for this stage; a broader role system would add complexity before a runner exists.

Rules:
- Unknown agents have no permissions.
- Missing scopes raise `PermissionError`.
- Policies must not contain empty agent scope sets.
- Tool access requests must include a reason suitable for audit logs.
- This boundary validates permission only; actual tool execution remains a future runner
  concern.

Verification:
- `tests/unit/test_coordinator_agent.py`
- `scripts/check_coordinator_agent_boundaries.ps1`
- `scripts/check_coordinator_pipeline.ps1`

## DEC-0061: Apply Coordinator final decisions only through lifecycle transition and memory policy

Status: accepted

Decision: Coordinator final decision integration uses `apply_coordinator_final_decision`.
The function builds a final decision from `CoordinatorFinalDecisionEvidence` and
`CoordinatorFinalDecisionPolicy`, then persists it only through
`transition_experiment_lifecycle` with a required `MemoryAgentService`-compatible writer.

Rationale: Final decisions affect both the structured registry and operational memory.
Allowing direct mutation of `Experiment.final_decision` from higher-level workflows would
create two paths for the same state change and make audit trails unreliable. Keeping one
apply boundary preserves state-machine validation, completion timestamps, rejection reasons,
and policy-controlled memory summaries.

Rules:
- Final decision persistence must go through `apply_coordinator_final_decision` or the lower
  `transition_experiment_lifecycle` state-machine boundary.
- `apply_coordinator_final_decision` must require a Memory Agent policy-compatible writer.
- Coordinator must not call ApeRAG write APIs directly.
- Invalid final decision evidence, including unjustified retests, must fail before registry
  mutation and before memory writes.

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

## DEC-0060: Keep Coordinator final decision logic explicit before persistence wiring

Status: accepted

Decision: Coordinator final decisions use a separate `CoordinatorFinalDecisionPolicy` and
`CoordinatorFinalDecisionEvidence` boundary. The policy maps explicit Critic statuses to
`rejected`, `quarantined`, or `approved` decisions. Retests of previously rejected
hypotheses require a non-empty justification before any final decision can be planned.

Rationale: The Critic Agent detects and classifies research issues, but the Coordinator owns
the final experiment-level decision. A separate decision boundary prevents hidden defaults,
keeps retest approval auditable, and avoids mixing final-decision policy with registry or
ApeRAG persistence before Task 13.4.

Rules:
- Coordinator final decisions must be derived from explicit policy, not built-in status
  defaults.
- Unknown Critic statuses must fail closed instead of being silently approved.
- Retest hypotheses require a human or agent-provided justification when policy requires it.
- The decision boundary returns a plan; registry and memory writes remain a separate
  integration boundary.

Verification:
- `tests/unit/test_coordinator_agent.py`
- `scripts/check_coordinator_agent_boundaries.ps1`
- `scripts/check_coordinator_pipeline.ps1`
