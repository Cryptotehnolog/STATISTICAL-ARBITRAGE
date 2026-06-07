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
