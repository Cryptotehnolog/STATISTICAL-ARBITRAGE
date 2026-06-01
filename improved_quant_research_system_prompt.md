# Prompt: Architecture Plan For Multi-Agent Quant Research System

You are a senior software architect, quantitative researcher, Rust/Python engineer, and trading risk reviewer.

Your task is to design a realistic, staged development plan for a multi-agent AI system that imitates a quantitative research department. The system should generate trading hypotheses, test them statistically, write or modify research code, criticize results, run backtests, maintain long-term memory, and eventually support demo trading. Do not assume that profitable live trading is guaranteed. Challenge weak assumptions and explicitly separate research goals from production trading claims.

## 1. Core Objective

Design a system for automated quantitative research focused first on statistical arbitrage and pairs trading. The first production-quality milestone is not live trading. The first milestone is a reproducible research platform that can:

- ingest market data from selected sources;
- generate and prioritize hypotheses;
- run statistical tests and backtests;
- store all decisions, results, code references, and experiment metadata;
- produce human-readable reports;
- prevent repeated testing of already-invalidated ideas;
- support manual review before any demo or live execution.

The system may later expand to demo trading and only after strict validation to limited live trading.

## 2. Required Output

Produce a detailed technical plan with the following sections:

1. Executive summary.
2. Critical review of the proposed idea, including what is unrealistic, risky, or over-engineered.
3. MVP scope for the first 4 weeks.
4. Architecture for v1, v2, and v3.
5. Agent roles and responsibilities.
6. Data architecture.
7. Research and statistical validation workflow.
8. Backtesting design.
9. Risk management and capital allocation design.
10. RAG and long-term memory design.
11. Memory write policy for every agent.
12. Dashboard and monitoring design.
13. Repository structure.
14. API boundaries between Python and Rust.
15. Database/schema proposal.
16. Testing strategy.
17. Deployment plan for local PC and Oracle Cloud Always Free.
18. Security and secrets management.
19. Cost, hardware, and operational constraints.
20. Roadmap with milestones and acceptance criteria.
21. Development workflow and CI requirements.
22. MVP acceptance criteria.
23. Data source and licensing requirements.
24. Backtest report requirements.
25. Failure, kill switch, and incident policy.
26. LLM model and token budget policy.
27. Legal, compliance, and human approval gates.
28. Open questions that must be answered before implementation.

For every major architectural choice, explain:

- why this choice is appropriate;
- what alternative was rejected;
- what risk this choice introduces;
- how to simplify it if implementation becomes too large.

## 3. Hard Constraints

Use a staged architecture. Do not design the full live-trading platform as v1.

Hardware constraints:

- Local development PC: Intel i5-1335U, 32 GB RAM, no CUDA GPU, 330 GB disk.
- Cloud target: Oracle Cloud Always Free ARM, 4 vCPU, 24 GB RAM, 200 GB disk.
- Assume limited budget and avoid paid data dependencies in v1.

Technology preferences:

- Python for orchestration, agents, research workflows, dashboards, API integration, and RAG.
- Use `uv` for Python dependency management, virtual environments, locking, and command execution. Do not use raw `pip` workflows except when documenting a fallback for unusual installation issues.
- Rust for performance-critical statistical calculations and later backtesting acceleration.
- PyO3 or a CLI boundary may be used between Python and Rust, but justify the choice.
- Prefer simple local-first infrastructure for v1.
- Use open-source tools where practical.
- During architecture planning, local design documents are acceptable. The implementation repository must be hosted on GitHub from the beginning of the implementation phase. Architecture decisions, experiment results, generated code, and LightRAG memory entries should reference Git commit hashes once the repository exists.
- Use Docker Compose for reproducible local infrastructure services from v1. Local research and development commands must still support fast `uv` and `cargo` workflows outside containers.

LightRAG is required from the beginning as the central long-term memory layer for agents and development knowledge. Do not add live execution in v1. Do not add Kafka, Redpanda, RisingWave, Memgraph, ClickHouse, Grafana, or Prometheus in v1 unless you explain why the current research stage truly needs them. Prefer Parquet, SQLite/Postgres, DuckDB, FastAPI, Streamlit, and LightRAG for v1 unless there is a strong reason not to. Streaming infrastructure may be designed as a later layer, but it should not block the first research MVP.

Docker and deployment requirements:

- Use Docker Compose for local infrastructure services from v1, such as databases, vector stores, LightRAG dependencies, API services, and dashboard services where applicable.
- Do not require every research script, notebook, or experiment command to run inside Docker during early development. The local workflow must support `uv run ...` for Python and `cargo ...` for Rust.
- Provide Dockerfiles for long-running services when they become deployable.
- Include `.env.example` files, service healthchecks, named volumes, and clear startup commands.
- Do not introduce Kubernetes, Helm, or complex orchestrators in v1.
- Design the Docker setup so it can later support reproducible deployment to Oracle Cloud Always Free.

Development workflow requirements:

- Use `uv sync` to create and update Python environments.
- Use `uv run ...` for Python commands, scripts, tests, and agent entrypoints.
- Use `cargo test`, `cargo clippy`, and `cargo fmt` for Rust components.
- Use Docker Compose for local infrastructure startup.
- Add GitHub Actions from the beginning for linting, tests, and reproducibility checks.
- Add pre-commit hooks if useful, but do not make them a substitute for CI.
- Include Ruff or an equivalent Python linter/formatter, pytest for Python tests, and standard Rust tooling for Rust checks.
- Every experiment record must include Git commit hash, dependency lock hash or version, config hash, dataset ID, run timestamp, and command used to launch it.
- Generated code from agents must go through tests and human review before being treated as accepted project code.
- The plan must define the standard local commands, for example `uv sync`, `uv run pytest`, `uv run ruff check`, `cargo test`, and `docker compose up`.

## 4. Trading Scope

Initial v1 scope:

- intraday OHLCV bars, not tick data;
- primary v1 timeframe: 15-minute bars;
- secondary v1 timeframe after pipeline validation: 5-minute bars;
- 1-minute bars may be added only after data quality checks, runtime limits, turnover analysis, slippage assumptions, and transaction-cost modeling are implemented;
- daily bars may be used for long-term context, regime filters, and sanity checks, but not as the only research timeframe;
- a small universe first, for example 50-200 liquid assets;
- one or two asset classes first, for example US equities/ETFs and crypto spot;
- pairs trading only;
- no real-money execution;
- no automatic order placement;
- no options or derivative execution in v1.

Later stages may add:

- broader cross-asset universes;
- multi-timeframe research across 1m, 5m, 15m, 1h, and daily bars;
- demo trading;
- execution adapters;
- portfolio-level risk optimization;
- streaming infrastructure.

## 5. Intraday Data Requirements

Design intraday data handling as a first-class part of v1. A strategy must not be accepted if its apparent performance depends on dirty, inconsistent, or unrealistic data.

Define requirements for:

- timezone normalization: all stored bars must use a single canonical timezone, preferably UTC;
- exchange calendars and trading sessions: equities, ETFs, crypto, futures, and FX have different session rules and must not be treated as if they share the same clock;
- missing bars: detect, classify, and record missing bars instead of silently forward-filling everything;
- duplicate bars: reject or reconcile duplicated timestamps deterministically;
- outliers and bad prints: detect suspicious OHLCV values, zero prices, impossible candles, and abnormal volume spikes;
- resampling: define deterministic rules for building 5m/15m/1h bars from lower-frequency or higher-frequency data, including open, high, low, close, volume, and timestamp labeling;
- alignment between pairs: pair tests and backtests must use only timestamps where both assets have valid comparable data;
- corporate actions for equities and ETFs: adjusted prices, splits, dividends, and survivorship bias must be addressed before results are trusted;
- transaction costs: every backtest must include commissions, fees, spreads, and realistic minimum cost assumptions;
- funding rates and borrow costs: for perpetual futures, margin products, short positions, and leveraged instruments, backtests must include funding payments, borrow fees, financing costs, and timestamp-accurate rate application;
- slippage: define conservative slippage models for each asset class and timeframe;
- cost attribution: every backtest report must separate gross PnL, commissions, spread/slippage cost, funding/borrow/financing cost, net PnL, and turnover;
- turnover limits: reject strategies whose expected edge disappears after realistic costs or whose trading frequency is operationally impractical;
- promotion rule: a strategy must not be promoted if profitability disappears after realistic commissions, spreads, slippage, funding, borrow fees, and financing costs;
- lookahead prevention: resampling, signal generation, hedge ratio estimation, and z-score calculation must use only information available at that time;
- data provenance: every dataset must store source, download time, symbol mapping, timeframe, adjustment mode, and validation status.

Require a data quality report before statistical testing and before every backtest. If data quality is below an explicit threshold, the pair or experiment must be rejected or quarantined.

## 6. Statistical Research Requirements

Design a validation workflow for pairs trading. Include, at minimum:

- data quality checks;
- survivorship-bias discussion;
- train/test split;
- walk-forward validation;
- Engle-Granger cointegration test;
- ADF test on residuals;
- hedge ratio estimation;
- half-life estimation;
- z-score signal construction;
- transaction costs and slippage assumptions;
- funding, borrow, and financing cost assumptions where relevant;
- multiple-testing correction;
- regime-change or structural-break checks;
- out-of-sample performance reporting.

Do not require every possible cointegration or stationarity test in v1. Instead, classify tests into:

- required for v1;
- useful for v2;
- specialist/optional.

Explicitly warn against p-hacking and data snooping.

Experiment reproducibility requirements:

- Every research result must be reproducible from a stored experiment record.
- Store dataset version, data source, validation report ID, config, parameters, random seed where relevant, commit hash, dependency lock, and execution command.
- Separate exploratory notebooks from accepted pipelines.
- Accepted results must be produced by scripted, repeatable commands, not by manual notebook state.
- Any rerun that produces materially different metrics must be flagged for review.

## 7. Multi-Agent Design

Design agents as software roles with deterministic interfaces, not as vague personalities.

Required agents:

- Coordinator: owns task queue, experiment lifecycle, and final decisions.
- Data Agent: updates datasets and validates data quality.
- Hypothesis Agent: generates candidate pairs and rationale.
- Statistical Testing Agent: runs tests and produces structured results.
- Backtest Agent: runs reproducible backtests and reports metrics.
- Critic Agent: rejects weak results, detects leakage, overfitting, and bad assumptions.
- Memory/RAG Agent: stores and retrieves decisions, experiments, code references, and lessons.
- Report Agent: creates summaries for human review.

For each agent, define:

- inputs;
- outputs;
- tools it can use;
- what it is not allowed to do;
- how its outputs are validated;
- what gets written to memory.

## 8. Memory And RAG

Design a two-level memory architecture. LightRAG is required from the beginning as the central long-term memory and knowledge graph for all agents, but it must be paired with a structured experiment registry so numeric facts remain auditable and reproducible.

Static and historical layer: LightRAG.

LightRAG must store and connect two categories of knowledge:

1. Market and fundamental knowledge:

- macroeconomic reports;
- financial filings such as 10-K and 10-Q reports;
- news and research notes;
- academic papers;
- historical market summaries;
- references to raw historical quote datasets, without treating unverified text as a source of numeric truth.

2. Development and agent memory:

- architecture decisions, for example "deep learning deferred in v1", "Rust used for performance-critical statistical routines", or "hybrid search combines brute-force screening and agent hypotheses";
- all generated hypotheses;
- checked pairs, including why they were rejected, promoted, or quarantined;
- statistical test results and links to structured result rows;
- backtest and demo-trading results, including metrics, conclusions, errors, and lessons learned;
- code written or modified by agents, with commit hashes, annotations, versioning, and notes about what worked or failed;
- configurations and parameters that produced strong or weak results;
- CrewAI or agent logs summarized into durable lessons so restarts, model changes, or context resets do not erase prior work;
- manual notes and human decisions that future agents must respect.

Structured experiment registry: SQLite/Postgres or DuckDB plus Parquet.

The structured registry must be the source of truth for:

- hypotheses;
- dataset IDs and data quality reports;
- code version or commit hash;
- parameters;
- statistical test results;
- backtest metrics;
- cost breakdowns;
- critic review;
- final decision;
- reason for rejection or promotion;
- links to generated reports and artifacts.

LightRAG must reference structured registry IDs instead of becoming the only store for numeric metrics. Agents may use LightRAG for retrieval, reasoning, multi-hop context, and avoiding repeated work, but final acceptance decisions must be traceable to structured records.

Memory write policy:

- Every agent must have an explicit write policy defining what it writes to LightRAG, what it writes to the structured registry, and what it must never write.
- The Coordinator must write task lifecycle events, final decisions, rejection reasons, promotion reasons, and links to registry records.
- The Data Agent must write dataset IDs, source metadata, data quality summaries, validation failures, and quarantine decisions.
- The Hypothesis Agent must write generated hypotheses, rationale, source references, novelty checks, and links to similar past hypotheses.
- The Statistical Testing Agent must write structured test results to the registry and summary lessons to LightRAG.
- The Backtest Agent must write structured performance metrics, cost attribution, artifact links, and summary conclusions.
- The Critic Agent must write objections, detected risks, leakage concerns, overfitting concerns, and final review status.
- The Report Agent must write report artifact links and human-readable summaries.
- Raw logs, raw prompts, large datasets, and secrets must not be dumped into LightRAG. Store references, summaries, IDs, and durable lessons instead.
- "Continual learning" means accumulating retrievable memory and structured experiment history. It must not imply automatic retraining or modification of model weights unless a separate, explicit training pipeline is designed.

Dynamic layer: design for RisingWave plus Memgraph, but defer implementation until demo or live-like streaming is justified.

The plan should describe the future dynamic layer:

- RisingWave for streaming SQL over price, volume, and event streams;
- Memgraph for a live graph of market state, such as assets, current spreads, volatility, correlations, exposures, and signal states;
- integration with Kafka or Redpanda only when real-time ingestion volume requires it.

Agents must eventually be able to query both layers:

- historical or fundamental question: LightRAG;
- development memory question: LightRAG plus structured registry;
- current market-state question: RisingWave plus Memgraph after the dynamic layer exists.

In v1, simulate the dynamic layer with batch intraday data, DuckDB/Parquet queries, and explicit interfaces so RisingWave and Memgraph can be added later without rewriting agent logic.

Do not optimize v1 for sub-100 ms live streaming latency. Optimize v1 for correctness, reproducibility, data quality, and research throughput.

## 9. Dashboard

Design a practical dashboard for v1:

- experiment list;
- hypothesis status;
- pair test results;
- backtest equity curve and drawdown;
- logs and errors;
- memory search;
- manual approval queue.

Avoid over-building drag-and-drop dashboards in v1 unless justified. Provide a path to more modular dashboards later.

## 10. Risk And Execution

No live trading in v1.

For demo trading stage, design:

- paper account balance;
- position sizing;
- max risk per trade;
- max concurrent positions;
- stop conditions;
- daily kill switch;
- manual approval mode;
- audit log;
- promotion criteria from research to demo.

For live trading, define strict gates:

- at least one month of demo trading;
- statistically defensible out-of-sample results;
- drawdown and risk limits satisfied;
- operational reliability;
- human approval;
- small capital allocation only.

State that no architecture can guarantee profit.

Human approval gates:

- AI agents may generate hypotheses, code, tests, reports, and recommendations.
- AI agents must not autonomously approve live trading, change risk limits, bypass kill switches, or deploy execution code.
- Demo trading requires explicit human approval after research-stage acceptance criteria are met.
- Live trading requires explicit human approval after demo-stage acceptance criteria are met.
- Any code touching execution, risk limits, order routing, credentials, or capital allocation must require human review.

Failure, kill switch, and incident policy:

- Define what happens during data outages, API errors, stale prices, abnormal spreads, missing funding rates, failed backtests, failed agents, and database/RAG failures.
- Define hard stop conditions for demo and live stages, including max drawdown, repeated execution errors, stale data, unexpected position exposure, and runaway order generation.
- Define token and cost runaway protection for agent loops.
- Define incident reports that record timeline, root cause, affected experiments or trades, remediation, and whether related strategies should be quarantined.
- Include a manual global kill switch for all demo/live execution paths.

Legal and compliance requirements:

- State clearly that the system is a research and decision-support tool, not a guarantee of profit or financial advice.
- Require review of exchange/API terms of service before using data or execution endpoints.
- Require audit logs for all human approvals, rejected signals, accepted signals, parameter changes, and execution-related decisions.

## 11. Data Source And Licensing Requirements

Require the plan to evaluate every data source before use:

- license and terms of service;
- whether storage, transformation, and derived research use are allowed;
- rate limits;
- historical depth;
- intraday availability;
- timezone and session metadata;
- adjusted versus unadjusted prices;
- funding rate availability where relevant;
- data reliability and known gaps;
- fallback source or retry strategy;
- cost now and expected cost after scaling.

Do not assume that free APIs are sufficient for all markets. If a market cannot be researched reliably with free data, mark it as deferred or paid-data-dependent.

## 12. Backtest Report Requirements

Every backtest report must include:

- strategy and hypothesis ID;
- dataset IDs and data quality report IDs;
- Git commit hash and config hash;
- tested symbols, timeframe, train/test split, and walk-forward windows;
- gross PnL;
- net PnL;
- commissions and fees;
- spread and slippage cost;
- funding, borrow, and financing cost where relevant;
- turnover;
- number of trades;
- average and median holding time;
- exposure by asset and side;
- Sharpe, Sortino, volatility, max drawdown, win rate, profit factor, and tail-risk metrics;
- comparison against a naive baseline;
- sensitivity to costs and slippage;
- rejected assumptions and critic comments;
- final decision: reject, quarantine, retest, promote to more validation, or eligible for demo review.

Strategies must be rejected or quarantined if the report lacks cost attribution, data quality evidence, or reproducibility metadata.

## 13. MVP Acceptance Criteria

Define the smallest useful MVP with measurable acceptance criteria. At minimum, v1 should demonstrate:

- repository initialized on GitHub before implementation work begins;
- Python environment managed by `uv` with `pyproject.toml` and `uv.lock`;
- Docker Compose starts required local infrastructure services;
- LightRAG configured as central long-term memory;
- structured experiment registry created;
- at least one data source integrated;
- intraday OHLCV ingestion for a small asset universe;
- data quality reports generated before tests and backtests;
- at least one scripted pair-screening workflow;
- at least one scripted backtest workflow;
- all results written to the structured registry and summarized into LightRAG;
- dashboard or report view showing experiments, pair results, and backtest reports;
- tests and linting run in GitHub Actions.

The plan must define exact numeric MVP targets, such as number of assets, timeframe, number of pairs, runtime target, and required reports.

## 14. LLM Model And Budget Policy

Design LLM usage with explicit control:

- define which agents use LLMs and which must be deterministic;
- define local versus API model choices if applicable;
- define token, cost, and runtime budgets per agent and per run;
- define retry limits and fallback behavior;
- log prompts, responses, tool calls, model name, model version, token counts, and cost estimates where available;
- prevent infinite agent loops;
- require critic review for agent-generated hypotheses and code;
- store useful summaries in LightRAG without storing unnecessary raw noise forever.

## 15. Security And Secrets

Use Infisical as the required secrets-management system.

Requirements:

- no secrets in Git;
- no secrets in LightRAG;
- no secrets in experiment reports;
- no secrets in logs;
- `.env.example` may document variable names only, never real values;
- local and cloud deployments must load secrets through Infisical;
- API keys, exchange credentials, database passwords, webhook tokens, Telegram tokens, and LLM keys must be managed through Infisical;
- execution-related credentials must be separated by environment: research, demo, and live.

## 16. Repository Structure

Propose a repository layout, for example:

- .github/
- apps/
- services/
- agents/
- research/
- rust/
- data/
- configs/
- tests/
- reports/
- docs/
- docker-compose.yml
- Dockerfiles where needed
- pyproject.toml
- uv.lock

Include a brief explanation of each folder.

## 17. Deliverable Style

Be direct and skeptical. If a proposed component is unnecessary or dangerous at the current stage, say so plainly.

The final plan must be implementable by one developer with AI assistance. Prefer staged, testable milestones over an impressive but fragile architecture.

End with:

- the smallest useful MVP;
- the first five implementation tasks;
- what can be automated immediately;
- what decisions require human input.
