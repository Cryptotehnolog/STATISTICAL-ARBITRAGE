# Expert Review Hardening Decisions

This shard records accepted and rejected decisions from the external review of
`tasks.md`, `requirements.md`, and `design.md`.

## DEC-0058: Implement expert review feedback through explicit contracts, not hidden defaults

Status: accepted

Decision: Accept the expert review direction on memory resilience, statistical diagnostics,
cost realism, non-functional requirements, and reproducibility schema alignment. Do not
copy expert-suggested numeric thresholds directly into production code as silent defaults.

Rationale: The project intentionally treats hidden thresholds as research risk. Values such
as half-life lower bounds, hedge-ratio R2 floors, slippage rates, leg-risk rates, and
capacity sizes may be useful, but only when passed as explicit policy/config values with
provenance and persisted in the registry.

Implementation impact:

- `requirements.md` now defines MoSCoW priorities, memory retrieval-quality checks,
  degraded memory behavior, MVP reproducibility acceptance, and non-functional runtime
  criteria.
- `design.md` now documents the Memory Agent backend boundary, degraded memory mode,
  explicit LLM fallback policy, Coordinator recovery expectations, and explicit
  statistical/cost policy rules.
- `tasks.md` now tracks MemoryBackend/degraded-mode work, Coordinator recovery details,
  resource monitoring, and expert-review research hardening.
- `BacktestResult` storage now carries the reproducibility manifest fields that were
  previously present only in the backtest manifest contract.

Alternatives considered: Implement all expert numbers immediately; reject the expert review
as too broad; keep accepted points only in chat.

Rejected approach: Hardcoding expert numbers would recreate the hidden-default problem that
the project has been removing from statistical, cost, baseline, and critic configs.

Risks: Explicit policies require more configuration effort. This is acceptable because
silent assumptions are more dangerous than visible setup.

Follow-up:

- Add `MemoryBackend` and durable memory write replay before agents depend heavily on
  memory writes.
- Add residual autocorrelation and residual distribution diagnostics.
- Add rolling hedge-ratio and cointegration stability diagnostics before promoting crypto
  pairs.
- Add capacity-adjusted cost scenarios and strategy-correlation reporting when multiple
  approved strategies exist.

## DEC-0091: Treat the second expert audit as checkpoint hardening, not a rewrite request

Status: accepted

Decision: Accept the second expert audit findings that improve enforcement and observability,
but reject broad rewrites that would distract from the MVP sequence. Immediate action is to
make CI measure CLI and dashboard coverage. Deferred action goes into tracked technical debt.

Accepted now:

- Include `stat_arb.cli` and `stat_arb.dashboard` in CI coverage measurement.
- Keep audited approval mutations behind `apply_coordinator_approval_action`.
- Keep dashboard approval UI disabled until failure handling and operator feedback are
  implemented.

Deferred:

- Do not mass-port 69 PowerShell scripts to Python before MVP. Add portable wrappers only
  for core Ubuntu/ARM workflows when Task 19/22 portability work starts.
- Do not add ProcessPool/joblib pair scanning until Coordinator task claiming is atomic.
- Do not vectorize `regime.py`, rewrite backtest loops, or cache walk-forward windows until
  profiling identifies the actual bottleneck.
- Do not add dashboard snapshot caching or query rewrites until registry size makes latency
  measurable.

Rationale: The audit correctly identifies risk areas, but speed work and broad portability
rewrites should be profile- and deployment-driven. The project should continue to prefer
explicit contracts, registry provenance, guarded memory writes, and staged implementation
over large cross-cutting rewrites.

## DEC-0094: Accept third-party audit ideas through staged contracts

Status: accepted

Decision: Accept the updated third-party audit as useful direction, but implement only the
low-risk hygiene and contract foundations immediately. Defer Kalman/Johansen/Phillips-
Perron runtime branches, event bus, heartbeat, async live data workers, macro adapters,
and dashboard analytics until their boundaries are justified by real workflow needs.

Accepted now:

- Remove debug `print` usage from production modules.
- Add a guard against future `print()` calls in production packages where logging or
  structured records should be used instead.
- Add an operator-safe `AgentAuditEvent` contract and JSONL writer foundation with
  metadata redaction.

Deferred:

- Kalman, Johansen/VECM, and Phillips-Perron belong in a model-comparison harness before
  becoming runtime options.
- Event bus and heartbeat belong after long-running worker agents or live/paper services
  exist.
- Dashboard research analytics should read factual registry/sidecar artifacts.
- Retry behavior should be unified through adapter-specific tests and shared policy
  vocabulary, not broad grep rules for every HTTP call.

Rationale: The project is tied to financial decisions, so adding impressive architecture
too early can be as dangerous as missing features. Staged contracts preserve
reproducibility, auditability, and explicit assumptions.
