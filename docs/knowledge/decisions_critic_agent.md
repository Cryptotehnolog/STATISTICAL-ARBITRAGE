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
