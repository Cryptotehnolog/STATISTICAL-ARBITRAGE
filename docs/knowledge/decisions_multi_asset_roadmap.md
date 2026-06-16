# Knowledge Decisions: Future Multi-Asset Roadmap

This shard captures external multi-asset statistical arbitrage suggestions that are useful
for the project roadmap but must not expand the current research MVP prematurely.

## DEC-0092: Treat multi-asset statistical arbitrage as a staged roadmap

Status: accepted

Decision: The project will remain crypto-first and research-first for the current MVP,
while keeping a staged path toward multi-asset statistical arbitrage across crypto,
equities, ETFs, futures, and macro factors. Multi-asset support should be introduced
through explicit contracts and validated service boundaries, not through a broad rewrite
or many new data providers at once.

Rationale: External reviews correctly noted that serious statistical arbitrage often
becomes multi-asset and factor-aware. However, adding equities, futures, ETFs, broker
execution, macro data, NLP, and optimization at the same time would blur the current MVP
boundaries and make errors harder to diagnose. The existing system already has registry,
quality, backtest, critic, coordinator, dashboard, and memory boundaries; future
multi-asset work must extend those boundaries instead of bypassing them.

Accepted future directions:
- Add explicit multi-leg signal contracts with assets, weights, z-score, entry and exit
  policy references, and provenance.
- Extend ingestion contracts with asset class, venue, session calendar, timezone, and
  adjustment policy before adding a second asset class.
- Add factor exposure diagnostics before portfolio-level capital allocation.
- Add portfolio-level risk allocation only through explicit risk policy contracts.
- Add asset-class-specific data adjustments, such as equity split/dividend handling and
  futures roll logic, only when those asset classes are enabled.
- Add stress testing and segment-level dashboard views after portfolio and risk
  boundaries exist.

Rejected immediate directions:
- Do not implement live broker execution, TWAP, adaptive limit orders, ETF iNAV
  arbitrage, or exchange gateway routing in the research MVP.
- Do not add hidden thresholds, hidden asset-class defaults, or fixed Kelly fractions.
- Do not add FinBERT/news filters, online Optuna optimization, or broad provider
  integrations before a measured need exists.
- Do not rename the project around generic external file names such as `data_fetcher.py`
  or `risk_agent.py`; the active package layout remains `src/stat_arb`.

Rules:
- A new asset class requires an explicit calendar/session model, adjustment policy, cost
  model, source provenance, and data-quality validation path.
- Adaptive thresholds and allocation rules must be explicit inputs with registry
  provenance, never silent defaults.
- Execution-related features stay behind the future paper/live roadmap until simulation,
  failure handling, approvals, and operator controls are stable.
- Any multi-asset memory writes must go through Memory Agent policy; exact metrics and
  artifacts remain in the Structured Registry and sidecars.

Alternatives considered: Convert the MVP immediately into a full multi-asset platform;
adopt a large provider/broker abstraction now; implement cross-asset strategies before
the current pair pipeline is accepted.

Risks: Staging multi-asset work means some useful strategies wait longer, but it protects
the MVP from becoming a fragile collection of unverified integrations.

## DEC-0093: Keep v1 crypto-first and fail closed on raw equities

Status: accepted

Decision: The active v1 data policy is crypto-first. `CCXT` crypto datasets must use
`adjustment_mode=none`. Equity-like sources (`Yahoo`, `Alpaca`, `Polygon`) must use
`adjustment_mode=split_dividend`; raw equity datasets and partial split-only or
dividend-only adjustment modes are rejected before registry persistence.

Rationale: Equity price series can contain jumps from splits and dividends that look like
statistical signals but are only corporate-action artifacts. Statistical testing and
backtesting should never consume raw equity OHLCV as if it were comparable to crypto
exchange candles. The project can still add equities later, but only through an explicit
adjusted-data and provenance boundary.

Implementation: `AdjustmentMode.SPLIT_DIVIDEND` and
`validate_dataset_adjustment_policy` define the domain rule. The `Dataset` domain model
and `persist_ohlcv_ingestion_result` registry helper both enforce the same policy.
`scripts/check_asset_adjustment_policy.ps1` is part of the local pre-commit checklist.

Alternatives considered: Treat `split` or `dividend` alone as enough; let each future
source adapter decide its own policy; keep equities in docs only without executable
guards. Those options are too easy for agents to bypass.

Risks: This blocks quick raw-equity experiments. That is intentional until an equities
pipeline can prove adjusted prices, licensing, calendars, source provenance, and data
quality semantics.
