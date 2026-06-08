# Knowledge Decisions: Critic Agent

This shard contains durable decisions about Critic Agent policies, review boundaries, and
registry/memory responsibilities.

## DEC-0049: Start Critic Agent with explicit lookahead evidence

Status: accepted

Decision: Implement the first Critic Agent boundary as deterministic lookahead-bias
detection. The boundary uses `CriticLookaheadPolicy`, `CriticLookaheadEvidence`, and
`detect_lookahead_bias`. The evidence contract explicitly pairs each signal or position
sizing decision index with the last data index used to make that decision. Walk-forward
windows are checked through the existing no-lookahead validation helper.

Rationale: Lookahead bias is a critical blocker for quantitative research. The Critic
Agent must not infer hidden thresholds or silently assume that signals are safe. Requiring
explicit evidence makes future agent reviews reproducible and gives tests a small, stable
contract before broader overfitting and decision logic is added.

Alternatives considered: Inspect only completed backtest metrics; rely on Backtest Agent
walk-forward validation; add a broad Critic Agent service with all checks at once.

Risks: This first boundary detects chronology and future-information violations, not every
form of research leakage. Future Critic tasks must add overfitting, weak-assumption,
insufficient-testing, and cost-realism checks with explicit policy contracts.

## DEC-0050: Detect overfitting with explicit performance evidence

Status: accepted

Decision: Implement Critic Agent overfitting detection through `CriticOverfittingPolicy`,
`CriticOverfittingEvidence`, and `detect_overfitting`. The policy explicitly controls
maximum in-sample/out-of-sample Sharpe degradation, maximum parameter-to-data ratio, and
near-perfect in-sample Sharpe criteria. The evidence contract carries the Sharpe values,
parameter count, data point count, and optional in-sample trade count.

Rationale: Overfitting checks are research-impacting and must not inherit convenient
thresholds from planning notes or code defaults. The Critic Agent should return transparent
indicators that later decision logic can convert into reject/quarantine/approve outcomes.

Alternatives considered: Hard-code common thresholds in the detector; fold overfitting into
lookahead detection; wait until final Critic decision logic exists.

Risks: The first detector uses summary evidence, not full train/test distributions or
parameter search history. Future Critic tasks may add richer evidence, but they should keep
the same explicit-policy discipline.

## DEC-0051: Detect weak assumptions with explicit statistical evidence

Status: accepted

Decision: Implement Critic Agent weak-assumption detection through
`CriticWeakAssumptionPolicy`, `CriticWeakAssumptionEvidence`, and
`detect_weak_assumptions`. The policy explicitly controls cointegration p-value proximity,
half-life bounds, unaddressed regime-change flagging, and minimum hedge-ratio R2. The
evidence contract carries cointegration p-value, half-life days, regime-change status, and
hedge-ratio regression quality.

Rationale: Weak statistical assumptions can make a strategy look valid while hiding fragile
evidence. These checks must not inherit planning examples or hard-coded thresholds. The
Critic Agent should return transparent indicators that later decision logic can route into
reject, quarantine, or approval outcomes.

Alternatives considered: Let Statistical Testing Agent decide all weak assumptions; embed
thresholds in `CriticReview`; postpone weak-assumption checks until the full Coordinator
exists.

Risks: This detector uses summary statistical evidence. Later Critic work may add richer
context such as multiple-testing method, sample size, residual diagnostics, and regime
break details, but those extensions should remain explicit policy/evidence fields.

## DEC-0052: Detect insufficient testing with explicit validation evidence

Status: accepted

Decision: Implement Critic Agent insufficient-testing detection through
`CriticInsufficientTestingPolicy`, `CriticInsufficientTestingEvidence`, and
`detect_insufficient_testing`. The policy explicitly controls minimum walk-forward window
count, minimum test-period length in days, and required sensitivity-analysis scenarios.
The evidence contract carries observed walk-forward window count, observed test-period
length, and completed sensitivity scenarios.

Rationale: A strategy can pass statistical checks and still be under-tested. The Critic
Agent should make missing validation coverage visible without silently borrowing example
numbers from plans or tutorials. The detector reports transparent indicators; later
decision logic will decide whether those indicators mean reject, quarantine, or approval.

Alternatives considered: Hard-code a common walk-forward count and test length; make the
Backtest Agent reject under-tested strategies directly; wait for full Coordinator logic.

Risks: This detector validates coverage metadata, not the quality of each sensitivity
scenario. Future Critic work may add checks for scenario relevance, cost realism, and
stress-test completeness, but those additions should remain explicit policy/evidence
fields.

## DEC-0053: Detect cost realism with explicit approved cost evidence

Status: accepted

Decision: Implement Critic Agent cost-realism detection through
`CriticCostRealismPolicy`, `CriticCostRealismEvidence`, and `detect_cost_realism`. The
policy explicitly controls negative-net-PnL flagging, maximum turnover, allowed cost
snapshot statuses, and maximum slippage difference versus an approved snapshot. The
evidence contract carries gross PnL, net PnL, turnover, assumed slippage, snapshot
slippage, cost snapshot status, and cost snapshot source.

Rationale: Cost assumptions can turn a paper strategy into a loss after realistic fees,
slippage, borrow, or funding. The Critic Agent must not invent acceptable turnover,
slippage, or cost-source rules. Those review rules are research assumptions and must be
passed explicitly from verified/manual-approved configuration.

Alternatives considered: Reject negative net PnL directly inside the Backtest Agent;
hard-code common turnover and slippage limits; defer cost realism until full Critic
decision logic.

Risks: This detector reviews summary evidence and snapshot provenance, not live market
microstructure. Future Cost Assumption Agent work should collect, refresh, and verify
venue/account-specific snapshots before production usage, while Critic remains responsible
for transparent review indicators.

## DEC-0054: Route final Critic decisions through explicit decision policy

Status: accepted

Decision: Implement final Critic review routing through `CriticDecisionPolicy`,
`CriticDecisionEvidence`, and `decide_critic_review`. The policy explicitly lists reject
and quarantine issue prefixes and separately controls whether a clean review may be
approved. Unknown indicators are quarantined instead of being silently approved.

Rationale: Reject/quarantine/approve is a research governance decision, not a hidden
implementation detail. Critical issues such as lookahead or negative net PnL can be routed
to rejection, moderate or uncertain issues can be quarantined, and clean approval must
remain explicit so later agents cannot inherit accidental defaults.

Alternatives considered: Hard-code issue severities inside individual detectors; approve
any review with no matched critical prefixes; postpone decision routing to the future
Coordinator.

Risks: Prefix-based routing is intentionally simple. Future Coordinator work may replace
prefix matching with richer severity objects, but it must preserve explicit policy and
unknown-indicator quarantine semantics.

## DEC-0055: Persist Critic reviews in registry before memory summaries

Status: accepted

Decision: Implement `run_critic_agent_persistence` as the Critic Agent boundary for
completed reviews. It requires an existing `BacktestResult`, stores structured review
fields in `CriticReview`, and writes only a concise summary through the Memory Agent
policy-compatible writer. Critic Agent code must not call ApeRAG directly.

Rationale: The registry is the source of truth for metrics, objections, statuses, and
provenance. ApeRAG memory should carry searchable summaries and references, not duplicate
metric-heavy payloads. This keeps future agent memory useful while preserving exact audit
data in the database.

Alternatives considered: Write all review details directly into ApeRAG; keep Critic
results in memory only; let Backtest Agent own the final rejection decision.

Risks: The first persistence boundary writes completed reviews rather than orchestrating
the full Critic workflow. Future Task 11 Memory Agent work should add richer query/write
operations without allowing direct ApeRAG writes from agent modules.

## DEC-0056: Treat Critic Agent 10.1-10.8 as one checkpoint baseline

Status: accepted

Decision: Expand `scripts/check_critic_pipeline.ps1` to cover lookahead, overfitting,
weak-assumption, insufficient-testing, cost-realism, final decision, registry persistence,
memory-boundary, and checkpoint-script tests in one command.

Rationale: Critic Agent failures are governance failures. A single checkpoint command makes
it cheap to verify that detection, routing, persistence, and memory boundaries still work
together before moving to later agents.

Alternatives considered: Keep separate ad hoc pytest commands; rely only on full
pre-commit; test persistence only in integration scripts.

Risks: The checkpoint remains a unit-level baseline. It does not prove real ApeRAG writes
or live registry migrations, which are covered by separate memory/backend checks.
