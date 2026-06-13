# Knowledge Decisions: Future Paper and Live Trading

This shard contains durable decisions about future paper/live trading roles. These
decisions do not expand the v1 MVP scope. They define the order and boundaries for later
work so research, simulation, and live execution are not mixed prematurely.

## DEC-0081: Treat paper/live agents as a staged roadmap, not immediate production readiness

Status: accepted

Decision: Future paper/live trading work will be introduced in stages after the research
MVP has stable data, statistical testing, backtesting, critic review, reporting, CLI, and
operator dashboard boundaries. Adding Regime Switch Detector, Execution and Slippage
Simulator, and Dynamic Risk and Capital Allocator roles is not enough to declare the
system production-ready for real money.

Rationale: The current project is a research platform. Real trading requires additional
execution gateway, kill switch, monitoring, incident handling, deployment, audit logging,
approval, and recovery controls. Calling the system production-ready after adding three
roles would blur the boundary between validated research and live capital risk.

Implementation order:
- First, add realistic execution and slippage simulation to strengthen backtest and Critic
  review.
- Second, add regime robustness checks in the research pipeline before treating regime
  changes as live trading commands.
- Third, add explicit risk policy contracts for capital allocation, exposure, drawdown,
  and correlated positions.
- Only after those boundaries are stable, consider full paper/live agents and exchange
  execution integration.

Rules:
- No future paper/live role may write directly to ApeRAG; all memory writes must pass
  through Memory Agent policy.
- Exact metrics, artifacts, approvals, cost snapshots, and trading decisions belong in the
  Structured Registry and sidecars.
- ApeRAG stores concise searchable summaries and decision references, not raw logs,
  secrets, prompts, or metric-heavy payloads.
- Human approval remains mandatory before demo/live promotion.

Alternatives considered: Add three full agents immediately; combine execution simulation,
regime detection, and risk allocation into one live trading agent; treat future live
features as implied by the existing Backtest/Critic agents.

Risks: Deferring full live-agent implementation may feel slower, but it prevents a
research platform from silently becoming an unsafe trading bot.

## DEC-0082: Add execution realism before live risk allocation

Status: accepted

Decision: Execution and slippage simulation is the first future paper/live role to
implement, but it should begin as a deterministic service boundary attached to Backtest
and Critic, not as an autonomous agent.

Rationale: Unmodeled commissions, spread, slippage, funding, borrow, liquidity, and market
impact can turn a profitable backtest into a losing live strategy. This is the most
immediate risk to research correctness. Starting with explicit simulation services keeps
the implementation testable and reproducible before any live execution layer exists.

Rules:
- Use verified or manual-approved cost snapshots as inputs.
- Keep all slippage and liquidity assumptions explicit and persisted with provenance.
- Start with scenario-based and snapshot-based simulation; require order-book data only
  when ingestion, storage, and provenance are ready for it.
- Critic Agent should be able to reject or quarantine strategies whose expected returns
  fail after realistic execution assumptions.

Alternatives considered: Require historical order-book data from the start; embed
slippage directly inside the backtest core with hidden defaults; defer execution realism
until live trading.

Risks: Early scenario-based simulation is less precise than full order-book replay, but it
is much safer than pretending fills happen at ideal prices.

## DEC-0083: Keep regime detection research-first before live monitoring

Status: accepted

Decision: Regime Switch Detector will start as research-time regime robustness validation.
It should evaluate volatility, volume, spreads, correlations, stationarity, and structural
break evidence before backtest promotion. Live monitoring and risk-off commands are future
paper/live responsibilities, not v1 behavior.

Rationale: Statistical arbitrage relies on fragile assumptions such as stationarity,
cointegration, and stable spread behavior. Regime shifts can invalidate those assumptions,
but automatically closing positions or switching models requires live execution controls
that do not exist yet.

Rules:
- In v1/v2 research, regime evidence is diagnostic input for Statistical Testing, Critic,
  and Coordinator decisions.
- No automatic live position close, model switch, or capital change is allowed until a
  paper/live execution layer, approval policy, and kill-switch design exist.
- Any future regime-exit policy must be explicit, persisted in reproducibility metadata,
  and tested against backtest behavior.

Alternatives considered: Place Regime Switch Detector only after Critic; let it send live
commands immediately; train and switch multiple models before the baseline research engine
is complete.

Risks: Diagnostic-only regime checks cannot protect live capital by themselves. That is
acceptable because live capital is outside the current MVP scope.

## DEC-0084: Introduce capital allocation as explicit risk policy before autonomous sizing

Status: accepted

Decision: Dynamic Risk and Capital Allocator will start as explicit risk policy contracts:
maximum exposure, maximum drawdown, maximum correlated exposure, capital allocation
constraints, and human approval requirements. Autonomous position sizing is deferred until
paper trading proves the execution and monitoring layers.

Rationale: Position sizing can amplify errors from statistical tests, backtests, cost
assumptions, and regime classification. Kelly-style sizing and volatility targeting are
useful research tools, but they can be dangerous when their inputs are unstable or
overfit.

Rules:
- Do not add hidden risk defaults.
- Persist every risk assumption in registry/reproducibility metadata.
- Treat Kelly, VaR, volatility targeting, and correlation-based allocation as explicitly
  configured policies, not automatic defaults.
- Human-in-the-loop approval remains required before demo/live capital allocation.

Alternatives considered: Add a full allocator agent immediately; use fixed percent sizing
as a universal fallback; use discounted Kelly as the default.

Risks: Explicit policy configuration makes early workflows more verbose. That is
intentional because sizing assumptions are capital-risk decisions, not convenience
parameters.
