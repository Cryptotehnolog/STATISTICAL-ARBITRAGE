# Requirements Document: Multi-Agent Quantitative Research System

## Introduction

This document specifies requirements for a multi-agent quantitative research system focused on statistical arbitrage and pairs trading. The system is designed as a staged development platform for automated hypothesis generation, statistical validation, backtesting, and long-term memory management. This is an architecture planning package, not an implementation. The first milestone is a reproducible research platform with proper data quality controls, statistical validation, and cost modeling—not live trading.

The system will operate on constrained hardware (local i5-1335U PC with 32GB RAM and Oracle Cloud Always Free ARM instance with 4 vCPU and 24GB RAM) using Python for orchestration and Rust for performance-critical components. ApeRAG provides long-term memory from the beginning. The system supports eventual demo trading after strict validation, but excludes live trading, streaming infrastructure (Kafka, RisingWave, Memgraph), and enterprise monitoring (ClickHouse, Grafana, Prometheus) from v1.

## Glossary

- **System**: The complete multi-agent quantitative research platform
- **Coordinator_Agent**: Agent responsible for task queue management and experiment lifecycle
- **Data_Agent**: Agent responsible for dataset updates and data quality validation
- **Hypothesis_Agent**: Agent that generates candidate trading pairs and rationale
- **Statistical_Testing_Agent**: Agent that executes cointegration tests, ADF tests, and hedge ratio estimation
- **Backtest_Agent**: Agent that runs reproducible backtests with cost attribution
- **Critic_Agent**: Agent that reviews results for leakage, overfitting, and weak assumptions
- **Memory_Agent**: Agent that manages ApeRAG storage and retrieval
- **Report_Agent**: Agent that generates human-readable summaries and reports
- **ApeRAG**: Long-term memory and knowledge graph system for agent decisions and development knowledge
- **Structured_Registry**: SQLite/Postgres database storing experiment metrics, dataset IDs, and test results
- **Experiment**: A complete research workflow from hypothesis through statistical testing to backtest
- **Hypothesis**: A candidate trading pair with rationale for testing
- **Data_Quality_Report**: Validation report covering timezone normalization, missing bars, outliers, and alignment
- **Backtest_Report**: Performance report including gross PnL, net PnL, cost attribution, and metrics
- **Cost_Attribution**: Breakdown of commissions, spreads, slippage, funding rates, and borrow costs
- **Promotion_Criteria**: Requirements for advancing a strategy from research to demo trading
- **Kill_Switch**: Manual emergency stop mechanism for demo or live execution
- **Human_Approval_Gate**: Required manual review before demo trading or live trading
- **Infisical**: Required secrets management system
- **Docker_Compose**: Container orchestration for local infrastructure services
- **uv**: Python dependency management tool for virtual environments and command execution
- **OHLCV**: Open, High, Low, Close, Volume bar data
- **Intraday_Data**: OHLCV bars at 15-minute, 5-minute, or 1-minute intervals
- **Lookahead_Bias**: Using future information in historical backtests
- **Walk_Forward_Validation**: Time-series validation technique using rolling train/test windows
- **Hedge_Ratio**: Coefficient determining position sizing between paired assets
- **Half_Life**: Time for mean reversion to decay by 50%
- **Z_Score**: Standardized residual signal for entry/exit decisions
- **Turnover**: Trading frequency measured as portfolio value traded per period
- **Slippage**: Difference between expected and actual execution price
- **Funding_Rate**: Periodic payment for perpetual futures positions
- **Borrow_Cost**: Fee for short positions in equities or margin products


## Requirements

### Requirement 1: Architecture Documentation

**User Story:** As a developer, I want comprehensive architecture documentation, so that I can understand system design decisions and implementation constraints.

#### Acceptance Criteria

1. THE System SHALL provide an executive summary document
2. THE System SHALL provide a critical review document identifying unrealistic, risky, or over-engineered components
3. THE System SHALL provide architecture diagrams for v1, v2, and v3 milestones
4. THE System SHALL provide agent role definitions with inputs, outputs, and tool permissions
5. THE System SHALL provide data architecture documentation including timezone handling, missing bar detection, and alignment rules
6. THE System SHALL provide API boundary specifications between Python and Rust components
7. THE System SHALL provide database schema documentation for the Structured_Registry
8. THE System SHALL provide repository structure documentation explaining each folder purpose
9. WHERE architecture decisions are documented, THE System SHALL explain the rationale, rejected alternatives, introduced risks, and simplification options


### Requirement 2: Data Ingestion and Quality Validation

**User Story:** As a quantitative researcher, I want reliable intraday OHLCV data with quality validation, so that I can trust statistical test results and backtest performance.

#### Acceptance Criteria

1. WHEN market data is ingested, THE Data_Agent SHALL normalize all timestamps to UTC
2. WHEN market data is ingested, THE Data_Agent SHALL detect and record missing bars
3. WHEN market data is ingested, THE Data_Agent SHALL detect and reject duplicate timestamps
4. WHEN market data is ingested, THE Data_Agent SHALL detect outliers including zero prices, impossible candles, and abnormal volume spikes
5. WHEN resampling OHLCV bars, THE Data_Agent SHALL apply deterministic rules for open, high, low, close, volume, and timestamp labeling
6. WHEN preparing pair data, THE Data_Agent SHALL align timestamps so both assets have valid comparable data
7. THE Data_Agent SHALL generate a Data_Quality_Report before statistical testing
8. THE Data_Agent SHALL generate a Data_Quality_Report before backtesting
9. IF data quality is below the defined threshold, THEN THE Data_Agent SHALL reject or quarantine the dataset
10. THE Data_Agent SHALL store dataset provenance including source, download time, symbol mapping, timeframe, adjustment mode, and validation status


### Requirement 3: Hypothesis Generation

**User Story:** As a quantitative researcher, I want automated hypothesis generation for candidate trading pairs, so that I can explore a larger opportunity space than manual research allows.

#### Acceptance Criteria

1. THE Hypothesis_Agent SHALL generate candidate trading pairs with rationale
2. WHEN generating a hypothesis, THE Hypothesis_Agent SHALL query ApeRAG to check for similar past hypotheses
3. WHEN generating a hypothesis, THE Hypothesis_Agent SHALL query the Structured_Registry to avoid retesting invalidated pairs
4. THE Hypothesis_Agent SHALL write generated hypotheses to ApeRAG with rationale and source references
5. THE Hypothesis_Agent SHALL write hypothesis records to the Structured_Registry with novelty check results
6. THE Hypothesis_Agent SHALL link new hypotheses to similar past hypotheses in ApeRAG
7. WHERE a hypothesis is similar to a previously rejected hypothesis, THE Hypothesis_Agent SHALL flag the similarity and provide justification for retesting


### Requirement 4: Statistical Testing Workflow

**User Story:** As a quantitative researcher, I want rigorous statistical validation of trading pairs, so that I can filter out spurious correlations before backtesting.

#### Acceptance Criteria

1. WHEN testing a pair, THE Statistical_Testing_Agent SHALL verify data quality reports exist for both assets
2. WHEN testing a pair, THE Statistical_Testing_Agent SHALL apply train/test split
3. WHEN testing a pair, THE Statistical_Testing_Agent SHALL execute Engle-Granger cointegration test
4. WHEN testing a pair, THE Statistical_Testing_Agent SHALL execute ADF test on residuals
5. WHEN testing a pair, THE Statistical_Testing_Agent SHALL estimate the Hedge_Ratio
6. WHEN testing a pair, THE Statistical_Testing_Agent SHALL estimate the Half_Life
7. WHEN testing a pair, THE Statistical_Testing_Agent SHALL construct Z_Score signals
8. WHEN testing a pair, THE Statistical_Testing_Agent SHALL apply multiple-testing correction
9. WHEN testing a pair, THE Statistical_Testing_Agent SHALL check for regime changes or structural breaks
10. THE Statistical_Testing_Agent SHALL write structured test results to the Structured_Registry
11. THE Statistical_Testing_Agent SHALL write summary lessons to ApeRAG
12. THE Statistical_Testing_Agent SHALL prevent Lookahead_Bias by using only information available at each timestamp


### Requirement 5: Backtesting with Cost Attribution

**User Story:** As a quantitative researcher, I want reproducible backtests with detailed cost attribution, so that I can evaluate net profitability after realistic transaction costs.

#### Acceptance Criteria

1. WHEN running a backtest, THE Backtest_Agent SHALL verify data quality reports exist
2. WHEN running a backtest, THE Backtest_Agent SHALL apply Walk_Forward_Validation
3. WHEN running a backtest, THE Backtest_Agent SHALL calculate gross PnL
4. WHEN running a backtest, THE Backtest_Agent SHALL calculate commissions and fees
5. WHEN running a backtest, THE Backtest_Agent SHALL calculate spread and Slippage costs
6. WHERE the backtest includes perpetual futures or margin products, THE Backtest_Agent SHALL calculate Funding_Rate costs
7. WHERE the backtest includes short positions, THE Backtest_Agent SHALL calculate Borrow_Cost
8. WHEN running a backtest, THE Backtest_Agent SHALL calculate net PnL as gross PnL minus all costs
9. WHEN running a backtest, THE Backtest_Agent SHALL calculate Turnover
10. WHEN running a backtest, THE Backtest_Agent SHALL generate a Backtest_Report including all Cost_Attribution components
11. THE Backtest_Agent SHALL store experiment metadata including Git commit hash, config hash, dataset IDs, run timestamp, and execution command
12. THE Backtest_Agent SHALL write structured performance metrics to the Structured_Registry
13. THE Backtest_Agent SHALL write summary conclusions to ApeRAG
14. THE Backtest_Agent SHALL prevent Lookahead_Bias in signal generation and position sizing


### Requirement 6: Backtest Report Content

**User Story:** As a quantitative researcher, I want comprehensive backtest reports, so that I can make informed decisions about strategy promotion or rejection.

#### Acceptance Criteria

1. THE Backtest_Report SHALL include strategy and hypothesis ID
2. THE Backtest_Report SHALL include dataset IDs and data quality report IDs
3. THE Backtest_Report SHALL include Git commit hash and config hash
4. THE Backtest_Report SHALL include tested symbols, timeframe, train/test split, and walk-forward windows
5. THE Backtest_Report SHALL include gross PnL, net PnL, commissions, spread/slippage cost, and funding/borrow costs
6. THE Backtest_Report SHALL include Turnover, number of trades, average holding time, and median holding time
7. THE Backtest_Report SHALL include exposure by asset and side
8. THE Backtest_Report SHALL include Sharpe ratio, Sortino ratio, volatility, max drawdown, win rate, profit factor, and tail-risk metrics
9. THE Backtest_Report SHALL include comparison against a naive baseline
10. THE Backtest_Report SHALL include sensitivity analysis to costs and slippage
11. THE Backtest_Report SHALL include critic comments and rejected assumptions
12. THE Backtest_Report SHALL include final decision: reject, quarantine, retest, promote, or eligible for demo review


### Requirement 7: Critic Review and Validation

**User Story:** As a quantitative researcher, I want automated review of results for leakage, overfitting, and weak assumptions, so that I can avoid deploying flawed strategies.

#### Acceptance Criteria

1. WHEN a backtest completes, THE Critic_Agent SHALL review the Backtest_Report
2. THE Critic_Agent SHALL detect potential Lookahead_Bias
3. THE Critic_Agent SHALL detect potential overfitting indicators
4. THE Critic_Agent SHALL detect weak statistical assumptions
5. THE Critic_Agent SHALL detect insufficient out-of-sample testing
6. THE Critic_Agent SHALL detect strategies where net PnL becomes negative after realistic costs
7. THE Critic_Agent SHALL detect strategies with operationally impractical Turnover
8. THE Critic_Agent SHALL write objections and detected risks to ApeRAG
9. THE Critic_Agent SHALL write final review status to the Structured_Registry
10. IF critical issues are detected, THEN THE Critic_Agent SHALL recommend rejection or quarantine


### Requirement 8: Long-Term Memory with ApeRAG

**User Story:** As a system operator, I want persistent memory of all research decisions and development knowledge, so that agents can learn from past work and avoid repeated mistakes.

#### Acceptance Criteria

1. THE System SHALL use ApeRAG as the central long-term memory layer from v1
2. THE Memory_Agent SHALL store market and fundamental knowledge in ApeRAG
3. THE Memory_Agent SHALL store development and agent memory in ApeRAG
4. THE Memory_Agent SHALL store architecture decisions in ApeRAG
5. THE Memory_Agent SHALL store all generated hypotheses with rationale in ApeRAG
6. THE Memory_Agent SHALL store statistical test summaries in ApeRAG
7. THE Memory_Agent SHALL store backtest summaries in ApeRAG
8. THE Memory_Agent SHALL store code references with commit hashes in ApeRAG
9. THE Memory_Agent SHALL store agent lessons learned in ApeRAG
10. THE Memory_Agent SHALL store manual notes and human decisions in ApeRAG
11. THE Memory_Agent SHALL reference Structured_Registry IDs instead of duplicating numeric metrics in ApeRAG
12. THE Memory_Agent SHALL NOT store raw logs, raw prompts, large datasets, or secrets in ApeRAG


### Requirement 9: Structured Experiment Registry

**User Story:** As a quantitative researcher, I want a structured database of all experiments and metrics, so that I can query, compare, and audit research results.

#### Acceptance Criteria

1. THE System SHALL maintain a Structured_Registry using SQLite, Postgres, or DuckDB
2. THE Structured_Registry SHALL store hypothesis records with IDs, rationale, and novelty check results
3. THE Structured_Registry SHALL store dataset IDs and data quality report references
4. THE Structured_Registry SHALL store code version or commit hash for each experiment
5. THE Structured_Registry SHALL store parameters and configuration for each experiment
6. THE Structured_Registry SHALL store statistical test results with p-values and test statistics
7. THE Structured_Registry SHALL store backtest metrics including gross PnL, net PnL, and cost breakdowns
8. THE Structured_Registry SHALL store critic review status and objections
9. THE Structured_Registry SHALL store final decision and reason for rejection or promotion
10. THE Structured_Registry SHALL store links to generated reports and artifacts
11. THE Structured_Registry SHALL serve as the source of truth for numeric metrics


### Requirement 10: Experiment Reproducibility

**User Story:** As a quantitative researcher, I want every experiment to be reproducible from stored metadata, so that I can verify results and debug discrepancies.

#### Acceptance Criteria

1. WHEN an experiment is executed, THE System SHALL record the dataset version and data source
2. WHEN an experiment is executed, THE System SHALL record the data quality report ID
3. WHEN an experiment is executed, THE System SHALL record the configuration and parameters
4. WHEN an experiment is executed, THE System SHALL record the random seed where applicable
5. WHEN an experiment is executed, THE System SHALL record the Git commit hash
6. WHEN an experiment is executed, THE System SHALL record the dependency lock file hash or version
7. WHEN an experiment is executed, THE System SHALL record the execution command
8. WHEN an experiment is executed, THE System SHALL record the run timestamp
9. IF an experiment rerun produces materially different metrics, THEN THE System SHALL flag the discrepancy for review
10. THE System SHALL separate exploratory notebooks from accepted pipelines
11. THE System SHALL require accepted results to be produced by scripted, repeatable commands


### Requirement 11: Dashboard and Reporting

**User Story:** As a quantitative researcher, I want a dashboard to monitor experiments, review results, and approve strategies, so that I can efficiently manage the research pipeline.

#### Acceptance Criteria

1. THE System SHALL provide a dashboard displaying the experiment list
2. THE System SHALL provide a dashboard displaying hypothesis status
3. THE System SHALL provide a dashboard displaying pair test results
4. THE System SHALL provide a dashboard displaying backtest equity curves
5. THE System SHALL provide a dashboard displaying backtest drawdown charts
6. THE System SHALL provide a dashboard displaying logs and errors
7. THE System SHALL provide a dashboard with memory search functionality
8. THE System SHALL provide a dashboard with a manual approval queue
9. THE Report_Agent SHALL generate human-readable summaries of experiments
10. THE Report_Agent SHALL write report artifact links to the Structured_Registry
11. THE Report_Agent SHALL write human-readable summaries to ApeRAG


### Requirement 12: Coordinator Agent Task Management

**User Story:** As a system operator, I want centralized task queue management and experiment lifecycle control, so that the multi-agent system operates in a coordinated manner.

#### Acceptance Criteria

1. THE Coordinator_Agent SHALL manage the task queue for all experiments
2. THE Coordinator_Agent SHALL manage experiment lifecycle from hypothesis through final decision
3. THE Coordinator_Agent SHALL write task lifecycle events to ApeRAG
4. THE Coordinator_Agent SHALL write final decisions to the Structured_Registry
5. THE Coordinator_Agent SHALL write rejection reasons to ApeRAG and the Structured_Registry
6. THE Coordinator_Agent SHALL write promotion reasons to ApeRAG and the Structured_Registry
7. THE Coordinator_Agent SHALL write links to registry records in ApeRAG
8. WHEN an experiment completes, THE Coordinator_Agent SHALL determine the next action based on results
9. IF a hypothesis is rejected, THEN THE Coordinator_Agent SHALL prevent retesting without new justification
10. THE Coordinator_Agent SHALL enforce agent tool permissions and validation rules


### Requirement 13: Risk Management and Position Sizing

**User Story:** As a risk manager, I want automated position sizing and risk limits, so that demo and live trading operate within acceptable risk parameters.

#### Acceptance Criteria

1. WHERE demo trading is enabled, THE System SHALL maintain a paper account balance
2. WHERE demo trading is enabled, THE System SHALL calculate position sizing based on risk parameters
3. WHERE demo trading is enabled, THE System SHALL enforce max risk per trade
4. WHERE demo trading is enabled, THE System SHALL enforce max concurrent positions
5. WHERE demo trading is enabled, THE System SHALL enforce stop conditions
6. WHERE demo trading is enabled, THE System SHALL provide a daily Kill_Switch
7. WHERE demo trading is enabled, THE System SHALL maintain an audit log of all decisions
8. THE System SHALL define Promotion_Criteria from research to demo trading
9. THE System SHALL define Promotion_Criteria from demo trading to live trading
10. THE System SHALL require Human_Approval_Gate before demo trading
11. THE System SHALL require Human_Approval_Gate before live trading


### Requirement 14: Human Approval Gates

**User Story:** As a system operator, I want mandatory human approval for critical decisions, so that AI agents cannot autonomously deploy risky changes.

#### Acceptance Criteria

1. THE System SHALL allow AI agents to generate hypotheses, code, tests, reports, and recommendations
2. THE System SHALL NOT allow AI agents to autonomously approve live trading
3. THE System SHALL NOT allow AI agents to autonomously change risk limits
4. THE System SHALL NOT allow AI agents to autonomously bypass Kill_Switch mechanisms
5. THE System SHALL NOT allow AI agents to autonomously deploy execution code
6. WHEN Promotion_Criteria for demo trading are met, THEN THE System SHALL require explicit human approval
7. WHEN Promotion_Criteria for live trading are met, THEN THE System SHALL require explicit human approval
8. WHERE code touches execution, risk limits, order routing, credentials, or capital allocation, THE System SHALL require human review
9. THE System SHALL log all human approval decisions with timestamp and approver identity


### Requirement 15: Failure Handling and Kill Switch

**User Story:** As a system operator, I want automated failure detection and manual kill switch capability, so that I can stop execution during anomalies or emergencies.

#### Acceptance Criteria

1. WHEN a data outage occurs, THEN THE System SHALL log the outage and pause affected experiments
2. WHEN an API error occurs, THEN THE System SHALL log the error and retry with exponential backoff
3. WHEN stale prices are detected, THEN THE System SHALL reject signals based on stale data
4. WHEN abnormal spreads are detected, THEN THE System SHALL flag the condition and pause affected strategies
5. WHEN missing funding rates are detected, THEN THE System SHALL reject cost calculations and pause affected strategies
6. WHEN a backtest fails, THEN THE System SHALL log the failure and quarantine the experiment
7. WHEN an agent fails, THEN THE System SHALL log the failure and alert the operator
8. WHEN a database or RAG failure occurs, THEN THE System SHALL log the failure and enter safe mode
9. WHERE demo or live trading is active, THE System SHALL provide a manual global Kill_Switch
10. WHEN the Kill_Switch is activated, THEN THE System SHALL immediately halt all demo and live execution
11. THE System SHALL define hard stop conditions including max drawdown, repeated execution errors, stale data, unexpected position exposure, and runaway order generation
12. THE System SHALL generate incident reports recording timeline, root cause, affected experiments or trades, remediation, and quarantine decisions


### Requirement 16: Security and Secrets Management

**User Story:** As a security engineer, I want all secrets managed through Infisical, so that credentials are never exposed in code, logs, or memory stores.

#### Acceptance Criteria

1. THE System SHALL use Infisical as the required secrets management system
2. THE System SHALL NOT store secrets in Git repositories
3. THE System SHALL NOT store secrets in ApeRAG
4. THE System SHALL NOT store secrets in experiment reports
5. THE System SHALL NOT store secrets in logs
6. THE System SHALL provide `.env.example` files documenting variable names only
7. THE System SHALL load secrets through Infisical for local deployments
8. THE System SHALL load secrets through Infisical for cloud deployments
9. THE System SHALL manage API keys, exchange credentials, database passwords, webhook tokens, Telegram tokens, and LLM keys through Infisical
10. THE System SHALL separate execution-related credentials by environment: research, demo, and live


### Requirement 17: Development Workflow and Dependency Management

**User Story:** As a developer, I want standardized development commands and dependency management, so that I can work efficiently and reproducibly.

#### Acceptance Criteria

1. THE System SHALL use `uv` for Python dependency management
2. THE System SHALL use `uv` for Python virtual environment creation
3. THE System SHALL use `uv` for Python dependency locking
4. THE System SHALL use `uv` for Python command execution
5. THE System SHALL provide `pyproject.toml` for Python project configuration
6. THE System SHALL provide `uv.lock` for reproducible Python dependencies
7. THE System SHALL support `uv sync` to create and update Python environments
8. THE System SHALL support `uv run` for Python commands, scripts, tests, and agent entrypoints
9. THE System SHALL use `cargo test` for Rust testing
10. THE System SHALL use `cargo clippy` for Rust linting
11. THE System SHALL use `cargo fmt` for Rust formatting
12. THE System SHALL use Docker Compose for local infrastructure startup
13. THE System SHALL NOT require every research script to run inside Docker during development


### Requirement 18: Continuous Integration and Testing

**User Story:** As a developer, I want automated testing and linting in CI, so that code quality is maintained and regressions are caught early.

#### Acceptance Criteria

1. THE System SHALL use GitHub Actions for continuous integration
2. WHEN code is pushed, THEN THE System SHALL run Python linting
3. WHEN code is pushed, THEN THE System SHALL run Python tests
4. WHEN code is pushed, THEN THE System SHALL run Rust linting
5. WHEN code is pushed, THEN THE System SHALL run Rust tests
6. WHEN code is pushed, THEN THE System SHALL run reproducibility checks
7. THE System SHALL use Ruff or equivalent for Python linting and formatting
8. THE System SHALL use pytest for Python tests
9. THE System SHALL use standard Rust tooling for Rust checks
10. WHERE pre-commit hooks are used, THE System SHALL NOT use them as a substitute for CI
11. THE System SHALL require generated code from agents to pass tests and human review before acceptance


### Requirement 19: Docker and Container Orchestration

**User Story:** As a developer, I want Docker Compose for local infrastructure services, so that I can run databases, vector stores, and APIs reproducibly.

#### Acceptance Criteria

1. THE System SHALL use Docker Compose for local infrastructure services from v1
2. THE System SHALL provide Docker Compose configuration for databases
3. THE System SHALL provide Docker Compose configuration for vector stores
4. THE System SHALL provide Docker Compose configuration for ApeRAG dependencies
5. THE System SHALL provide Docker Compose configuration for API services where applicable
6. THE System SHALL provide Docker Compose configuration for dashboard services where applicable
7. THE System SHALL provide `.env.example` files for Docker services
8. THE System SHALL provide service healthchecks in Docker Compose
9. THE System SHALL provide named volumes in Docker Compose
10. THE System SHALL provide clear startup commands for Docker services
11. THE System SHALL NOT require Kubernetes, Helm, or complex orchestrators in v1
12. THE System SHALL support reproducible deployment to Oracle Cloud Always Free


### Requirement 20: Data Source Licensing and Compliance

**User Story:** As a compliance officer, I want all data sources evaluated for licensing and terms of service, so that the system operates within legal boundaries.

#### Acceptance Criteria

1. WHEN evaluating a data source, THE System SHALL document the license and terms of service
2. WHEN evaluating a data source, THE System SHALL document whether storage, transformation, and derived research use are allowed
3. WHEN evaluating a data source, THE System SHALL document rate limits
4. WHEN evaluating a data source, THE System SHALL document historical depth
5. WHEN evaluating a data source, THE System SHALL document intraday availability
6. WHEN evaluating a data source, THE System SHALL document timezone and session metadata
7. WHEN evaluating a data source, THE System SHALL document adjusted versus unadjusted price availability
8. WHEN evaluating a data source, THE System SHALL document funding rate availability where relevant
9. WHEN evaluating a data source, THE System SHALL document data reliability and known gaps
10. WHEN evaluating a data source, THE System SHALL document fallback source or retry strategy
11. WHEN evaluating a data source, THE System SHALL document current cost and expected cost after scaling
12. IF a market cannot be researched reliably with free data, THEN THE System SHALL mark it as deferred or paid-data-dependent


### Requirement 21: LLM Model and Token Budget Control

**User Story:** As a system operator, I want explicit control over LLM usage and costs, so that agent operations remain within budget and do not enter infinite loops.

#### Acceptance Criteria

1. THE System SHALL define which agents use LLMs and which must be deterministic
2. THE System SHALL define local versus API model choices where applicable
3. THE System SHALL define token budgets per agent
4. THE System SHALL define token budgets per run
5. THE System SHALL define cost budgets per agent where applicable
6. THE System SHALL define cost budgets per run where applicable
7. THE System SHALL define runtime budgets per agent
8. THE System SHALL define retry limits for LLM calls
9. THE System SHALL define fallback behavior for LLM failures
10. THE System SHALL log prompts, responses, tool calls, model name, model version, token counts, and cost estimates
11. THE System SHALL prevent infinite agent loops
12. THE System SHALL require critic review for agent-generated hypotheses and code
13. THE System SHALL store useful summaries in ApeRAG without storing unnecessary raw noise


### Requirement 22: MVP Scope and Acceptance Criteria

**User Story:** As a project manager, I want clearly defined MVP acceptance criteria, so that I can determine when v1 is complete and ready for use.

#### Acceptance Criteria

1. THE System SHALL initialize a repository on GitHub before implementation work begins
2. THE System SHALL manage Python environment with `uv`, `pyproject.toml`, and `uv.lock`
3. THE System SHALL start required local infrastructure services with Docker Compose
4. THE System SHALL configure ApeRAG as central long-term memory
5. THE System SHALL create a Structured_Registry
6. THE System SHALL integrate at least one data source
7. THE System SHALL ingest intraday OHLCV data for a small asset universe
8. THE System SHALL generate Data_Quality_Report before tests and backtests
9. THE System SHALL provide at least one scripted pair-screening workflow
10. THE System SHALL provide at least one scripted backtest workflow
11. THE System SHALL write all results to the Structured_Registry and summarize into ApeRAG
12. THE System SHALL provide a dashboard or report view showing experiments, pair results, and Backtest_Report
13. THE System SHALL run tests and linting in GitHub Actions
14. THE System SHALL define exact numeric MVP targets for number of assets, timeframe, number of pairs, runtime target, and required reports


### Requirement 23: Hardware and Operational Constraints

**User Story:** As a system architect, I want the system designed for constrained hardware, so that it operates efficiently on available resources.

#### Acceptance Criteria

1. THE System SHALL operate on Intel i5-1335U with 32 GB RAM
2. THE System SHALL operate without CUDA GPU requirements
3. THE System SHALL operate within 330 GB disk on local PC
4. THE System SHALL operate on Oracle Cloud Always Free ARM with 4 vCPU and 24 GB RAM
5. THE System SHALL operate within 200 GB disk on Oracle Cloud
6. THE System SHALL avoid paid data dependencies in v1
7. THE System SHALL use Python for orchestration, agents, research workflows, dashboards, API integration, and RAG
8. THE System SHALL use Rust for performance-critical statistical calculations
9. THE System SHALL use Rust for performance-critical backtesting acceleration where justified
10. THE System SHALL prefer simple local-first infrastructure for v1
11. THE System SHALL use open-source tools where practical


### Requirement 24: Staged Architecture and Scope Management

**User Story:** As a system architect, I want a staged development approach, so that complexity is managed and each milestone delivers value.

#### Acceptance Criteria

1. THE System SHALL define v1 scope as a reproducible research platform without live trading
2. THE System SHALL define v2 scope to include demo trading capabilities
3. THE System SHALL define v3 scope to include limited live trading after strict validation
4. THE System SHALL NOT include Kafka, Redpanda, RisingWave, or Memgraph in v1 unless justified
5. THE System SHALL NOT include ClickHouse, Grafana, or Prometheus in v1 unless justified
6. THE System SHALL prefer Parquet, SQLite/Postgres, DuckDB, FastAPI, Streamlit, and ApeRAG for v1
7. THE System SHALL support 15-minute bars as primary v1 timeframe
8. THE System SHALL support 5-minute bars as secondary v1 timeframe after pipeline validation
9. THE System SHALL support 1-minute bars only after data quality checks, runtime limits, turnover analysis, slippage assumptions, and transaction-cost modeling are implemented
10. THE System SHALL focus on pairs trading only in v1
11. THE System SHALL support a small universe of 50-200 liquid assets in v1
12. THE System SHALL support one or two asset classes in v1


### Requirement 25: Python and Rust API Boundaries

**User Story:** As a developer, I want clear API boundaries between Python and Rust, so that I can optimize performance-critical components without rewriting the entire system.

#### Acceptance Criteria

1. THE System SHALL use Python for orchestration and agent coordination
2. THE System SHALL use Python for research workflows and notebooks
3. THE System SHALL use Python for dashboards and reporting
4. THE System SHALL use Python for API integration
5. THE System SHALL use Python for RAG and ApeRAG integration
6. THE System SHALL use Rust for performance-critical statistical calculations
7. THE System SHALL use Rust for performance-critical backtesting acceleration where justified
8. THE System SHALL define API boundaries using PyO3 or CLI interfaces
9. THE System SHALL document the rationale for choosing PyO3 versus CLI boundaries
10. THE System SHALL document performance requirements that justify Rust implementation
11. THE System SHALL provide Python fallback implementations for Rust components during development


### Requirement 26: Legal, Compliance, and Disclaimers

**User Story:** As a legal advisor, I want clear disclaimers and compliance requirements, so that the system is positioned as a research tool and not financial advice.

#### Acceptance Criteria

1. THE System SHALL state clearly that it is a research and decision-support tool
2. THE System SHALL state clearly that it is not a guarantee of profit or financial advice
3. THE System SHALL require review of exchange and API terms of service before using data or execution endpoints
4. THE System SHALL require audit logs for all human approvals
5. THE System SHALL require audit logs for all rejected signals
6. THE System SHALL require audit logs for all accepted signals
7. THE System SHALL require audit logs for all parameter changes
8. THE System SHALL require audit logs for all execution-related decisions
9. THE System SHALL NOT guarantee profitable live trading
10. THE System SHALL document that no architecture can guarantee profit


### Requirement 27: Repository Structure and Organization

**User Story:** As a developer, I want a well-organized repository structure, so that I can navigate the codebase efficiently.

#### Acceptance Criteria

1. THE System SHALL provide a `.github/` directory for GitHub Actions and workflows
2. THE System SHALL provide an `apps/` directory for application entrypoints
3. THE System SHALL provide a `services/` directory for long-running services
4. THE System SHALL provide an `agents/` directory for agent implementations
5. THE System SHALL provide a `research/` directory for research scripts and notebooks
6. THE System SHALL provide a `rust/` directory for Rust components
7. THE System SHALL provide a `data/` directory for data storage and caching
8. THE System SHALL provide a `configs/` directory for configuration files
9. THE System SHALL provide a `tests/` directory for test suites
10. THE System SHALL provide a `reports/` directory for generated reports
11. THE System SHALL provide a `docs/` directory for documentation
12. THE System SHALL provide a `docker-compose.yml` file for infrastructure services
13. THE System SHALL provide Dockerfiles where needed for deployable services
14. THE System SHALL provide `pyproject.toml` for Python project configuration
15. THE System SHALL provide `uv.lock` for Python dependency locking
16. THE System SHALL document the purpose of each directory


### Requirement 28: Agent Memory Write Policies

**User Story:** As a system architect, I want explicit memory write policies for each agent, so that memory stores remain clean, auditable, and useful.

#### Acceptance Criteria

1. THE Coordinator_Agent SHALL write task lifecycle events to ApeRAG
2. THE Coordinator_Agent SHALL write final decisions and rejection/promotion reasons to the Structured_Registry and ApeRAG
3. THE Data_Agent SHALL write dataset IDs, source metadata, and data quality summaries to the Structured_Registry
4. THE Data_Agent SHALL write validation failures and quarantine decisions to ApeRAG
5. THE Hypothesis_Agent SHALL write generated hypotheses with rationale to ApeRAG
6. THE Hypothesis_Agent SHALL write hypothesis records and novelty checks to the Structured_Registry
7. THE Statistical_Testing_Agent SHALL write structured test results to the Structured_Registry
8. THE Statistical_Testing_Agent SHALL write summary lessons to ApeRAG
9. THE Backtest_Agent SHALL write structured performance metrics and cost attribution to the Structured_Registry
10. THE Backtest_Agent SHALL write summary conclusions to ApeRAG
11. THE Critic_Agent SHALL write objections, detected risks, and review status to ApeRAG and the Structured_Registry
12. THE Report_Agent SHALL write report artifact links to the Structured_Registry
13. THE Report_Agent SHALL write human-readable summaries to ApeRAG
14. THE Memory_Agent SHALL NOT write raw logs, raw prompts, large datasets, or secrets to ApeRAG


### Requirement 29: Future Dynamic Layer Design

**User Story:** As a system architect, I want a design for future streaming infrastructure, so that the system can scale to real-time processing without rewriting agent logic.

#### Acceptance Criteria

1. THE System SHALL describe the future dynamic layer architecture
2. THE System SHALL describe RisingWave for streaming SQL over price, volume, and event streams
3. THE System SHALL describe Memgraph for live graph of market state
4. THE System SHALL describe integration with Kafka or Redpanda for real-time ingestion
5. THE System SHALL describe agent query patterns for historical questions using ApeRAG
6. THE System SHALL describe agent query patterns for development memory using ApeRAG and Structured_Registry
7. THE System SHALL describe agent query patterns for current market state using RisingWave and Memgraph
8. THE System SHALL simulate the dynamic layer in v1 using batch intraday data and DuckDB/Parquet queries
9. THE System SHALL design explicit interfaces so RisingWave and Memgraph can be added later without rewriting agent logic
10. THE System SHALL NOT optimize v1 for sub-100 ms live streaming latency
11. THE System SHALL optimize v1 for correctness, reproducibility, data quality, and research throughput


### Requirement 30: Strategy Promotion Criteria

**User Story:** As a risk manager, I want explicit criteria for promoting strategies from research to demo to live, so that only validated strategies advance.

#### Acceptance Criteria

1. THE System SHALL define Promotion_Criteria from research to demo trading
2. THE System SHALL require statistically significant out-of-sample results for promotion to demo
3. THE System SHALL require positive net PnL after realistic costs for promotion to demo
4. THE System SHALL require acceptable Turnover for promotion to demo
5. THE System SHALL require passing critic review for promotion to demo
6. THE System SHALL require at least one month of demo trading before promotion to live
7. THE System SHALL require statistically defensible out-of-sample results for promotion to live
8. THE System SHALL require drawdown and risk limits satisfied for promotion to live
9. THE System SHALL require operational reliability demonstrated for promotion to live
10. THE System SHALL require human approval for promotion to demo
11. THE System SHALL require human approval for promotion to live
12. THE System SHALL require small capital allocation only for initial live trading

