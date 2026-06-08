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
