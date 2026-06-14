# Knowledge Decisions: Failure Handling

This shard records durable decisions for Task 17 failure handling, safe mode, retry,
and local resource budget boundaries.

## DEC-0092: Keep failure handling as an explicit policy boundary

Status: accepted

Decision: Task 17 failure handling is implemented as `stat_arb.agents.failure_handling`,
a small deterministic boundary with explicit policies for data freshness, API retries,
abnormal market conditions, runtime dependency failures, and local resource budgets.
The module classifies events and routes state changes through the existing Coordinator
and Memory Agent boundaries.

Rationale: Failure handling is safety-critical. Hidden thresholds would let agents inherit
unverified assumptions, so `DataFreshnessPolicy`, `RetryPolicy`,
`FailureHandlingPolicy`, and `ResourceBudgetPolicy` require explicit values. Registry
state changes use `transition_experiment_lifecycle` or `fail_coordinator_task`; memory
summaries use the `MemoryWriter`/Memory Agent policy path instead of direct ApeRAG writes.

Alternatives considered: Add a broad background failure supervisor; store failures only
in ApeRAG; add implicit defaults for common retry and freshness values.

Risks: The current layer is deterministic and does not run a continuous scheduler. Future
runtime orchestration may need to call these policies from a real experiment runner or
operator monitor.

Verification:

- `scripts/check_failure_handling_pipeline.ps1`
- `tests/unit/test_failure_handling.py`
- `tests/unit/test_check_failure_handling_pipeline.py`
- `tests/unit/test_check_runtime_resource_budget.py`

## DEC-0093: Keep runtime resource budget checks outside ordinary pre-commit

Status: accepted

Decision: Local RAM and disk budget monitoring lives in
`scripts/check_runtime_resource_budget.ps1` and is not part of `pre_commit_check.ps1`.
The script requires explicit `RamBudgetGb`, `DiskBudgetGb`, and `WarnUsageRatio`.

Rationale: Docker, WSL, ApeRAG, OmniRoute, and local browser processes can legitimately
change runtime resource usage while code remains correct. Ordinary commits should test
code quality and deterministic contracts, not fail because the operator currently has
heavy infrastructure running.

Alternatives considered: Put Docker/WSL resource checks in pre-commit; hard-code an 80%
threshold; rely only on Windows Task Manager.

Risks: Operators must run the resource check manually during heavy local work. If a future
dashboard or scheduler owns runtime monitoring, it should call the same explicit policy
instead of inventing a second threshold.
