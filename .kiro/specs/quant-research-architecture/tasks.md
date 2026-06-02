# Implementation Plan: Multi-Agent Quantitative Research System

## Overview

This implementation plan breaks down the multi-agent quantitative research system into discrete coding tasks. The system is a reproducible research platform for statistical arbitrage and pairs trading, featuring data ingestion with quality validation, hypothesis generation, statistical testing, backtesting with cost attribution, critic review, and LightRAG memory management.

**Key Implementation Principles:**
- Python-first approach with optional Rust optimization
- Minimal infrastructure (SQLite + embedded vector store, no Docker required for MVP)
- Constrained hardware (i5-1335U with 32GB RAM, Oracle Cloud Always Free ARM)
- Focus on correctness, reproducibility, and data quality over speed
- Property-based testing for statistical functions and data validation

## First MVP Execution Scope

**The first MVP implementation pass includes tasks 1-19 and 22-23 only.**

**Required for MVP:**
- Tasks 1-19: Core system implementation (repository setup, infrastructure, all agents, CLI, dashboard, error handling, CI/CD, documentation)
- Task 22: Final MVP validation
- Task 23: Final review and handoff

**Deferred (NOT in first MVP pass):**
- Task 20: Docker Compose (optional, deferred to post-MVP or v2)
- Task 21: Risk management implementation (deferred to v2, only documentation in v1)

**Optional sub-tasks marked with `*` can be skipped for faster MVP iteration but are recommended for production quality.**

## Tasks

- [x] 1. Initialize repository structure and development environment
  - GitHub repository already exists at https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE
  - Set up `pyproject.toml` with project metadata and dependencies
  - Configure `uv` for Python dependency management
  - Create `.env.example` for environment variables (no secrets)
  - Set up `.gitignore` for Python, data files, and secrets
  - Create initial `README.md` with project overview and setup instructions
  - _Requirements: 22.1, 17.1-17.8, 27.1-27.16_

- [ ] 2. Set up core infrastructure and storage layer
  - [x] 2.1 Create SQLite database schema for Structured Registry
    - Define tables for hypotheses, datasets, statistical tests, backtests, critic reviews, experiments
    - Implement database initialization script
    - Create database migration utilities
    - _Requirements: 9.1-9.11, 27.14_

  - [ ]* 2.2 Write property test for database schema integrity
    - **Property 14: Experiment Reproducibility**
    - **Validates: Requirements 10.9**
    - Test that identical experiment data produces identical database records
  
  - [x] 2.3 Initialize LightRAG with embedded vector store
    - Configure LightRAG with FAISS or Chroma embedded backend
    - Set up sentence-transformers/all-MiniLM-L6-v2 embedding model
    - Create LightRAG initialization script
    - Configure chunk size (512 tokens) and overlap (50 tokens)
    - _Requirements: 8.1-8.12, 27.5_
  
  - [x] 2.4 Implement Infisical secrets management integration
    - Set up Infisical client for Python
    - Create secrets loading utilities
    - Document required secrets in `.env.example`
    - _Requirements: 16.1-16.10_

- [ ] 3. Implement data models and validation
  - [x] 3.1 Create Pydantic data models for all entities
    - Implement Hypothesis, Dataset, StatisticalTestResult, BacktestResult, CriticReview, Experiment models
    - Add validation rules and type constraints
    - _Requirements: 2.10, 3.1-3.7, 4.1-4.12, 5.1-5.14_
  
  - [x]* 3.2 Write unit tests for data model validation
    - Test edge cases and validation rules
    - Test serialization/deserialization
    - _Requirements: 18.8_

- [ ] 4. Build Data Agent with quality validation
  - [ ] 4.1 Implement OHLCV data ingestion from CCXT (crypto)
    - Create data source adapter for CCXT
    - Implement download logic for multiple exchanges (Binance, Coinbase, Kraken)
    - Handle rate limiting and retries with exponential backoff
    - Store raw data in Parquet format partitioned by symbol and date
    - _Requirements: 2.1-2.10, 20.1-20.12_

  - [ ]* 4.2 Write property test for timestamp normalization
    - **Property 1: Timestamp Normalization Preserves Time**
    - **Validates: Requirements 2.1**
    - Test that normalizing timestamps to UTC preserves absolute time
  
  - [ ] 4.3 Implement data quality validation functions
    - Timestamp normalization to UTC
    - Missing bar detection with configurable thresholds
    - Duplicate timestamp detection and rejection
    - Outlier detection (zero prices, impossible candles, volume spikes)
    - _Requirements: 2.1-2.4_
  
  - [ ]* 4.4 Write property tests for data quality validation
    - **Property 2: Missing Bar Detection Completeness**
    - **Property 3: Duplicate Timestamp Detection Completeness**
    - **Property 4: Outlier Detection Sensitivity**
    - **Validates: Requirements 2.2, 2.3, 2.4**
  
  - [ ] 4.5 Implement OHLCV resampling with deterministic rules
    - Create resampling function for aggregating bars (1m → 5m → 15m)
    - Apply deterministic rules for OHLC, volume, and timestamp labeling
    - _Requirements: 2.5_
  
  - [ ]* 4.6 Write property test for resampling idempotence
    - **Property 5: Resampling Idempotence**
    - **Validates: Requirements 2.5**
    - Test that resampling produces identical results when applied multiple times
  
  - [ ] 4.7 Implement timestamp alignment for pairs
    - Create alignment function ensuring both assets have matching timestamps
    - Handle partial overlaps and missing data
    - _Requirements: 2.6_
  
  - [ ]* 4.8 Write property test for timestamp alignment
    - **Property 6: Timestamp Alignment Consistency**
    - **Validates: Requirements 2.6**
    - Test that aligned timestamps exist in both series

  - [ ] 4.9 Implement data quality report generation
    - Generate comprehensive quality reports with all validation results
    - Store reports in SQLite registry with dataset IDs
    - Write validation failures to LightRAG
    - _Requirements: 2.7-2.9_
  
  - [ ] 4.10 Implement dataset provenance tracking
    - Store source, download time, symbol mapping, timeframe, adjustment mode
    - Create metadata JSON sidecar files
    - _Requirements: 2.10_

- [ ] 5. Checkpoint - Ensure data ingestion and validation works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Build Statistical Testing Agent
  - [ ] 6.1 Implement Engle-Granger cointegration test (Python)
    - Create cointegration test function using statsmodels
    - Calculate test statistic and p-value
    - Apply multiple testing correction (Bonferroni or Benjamini-Hochberg)
    - _Requirements: 4.3, 4.8_
  
  - [ ] 6.2 Implement ADF test for residuals (Python)
    - Create ADF test function using statsmodels
    - Test stationarity of spread
    - _Requirements: 4.4_
  
  - [ ]* 6.3 Write property tests for statistical functions
    - **Property 7: Cointegration Test Accuracy**
    - **Property 8: ADF Test Stationarity Detection**
    - **Validates: Requirements 4.3, 4.4, 4.5**
    - Generate synthetic cointegrated and non-cointegrated pairs
    - Verify test accuracy and hedge ratio estimation
  
  - [ ] 6.4 Implement hedge ratio estimation
    - Use OLS regression to estimate hedge ratio
    - Calculate R² for regression quality
    - _Requirements: 4.5_

  - [ ] 6.5 Implement half-life estimation
    - Calculate mean reversion speed from residuals
    - Use Ornstein-Uhlenbeck process estimation
    - _Requirements: 4.6_
  
  - [ ]* 6.6 Write property test for half-life estimation
    - **Property 9: Half-Life Estimation Accuracy**
    - **Validates: Requirements 4.6**
    - Generate OU processes with known half-lives
    - Verify estimation within 20% tolerance
  
  - [ ] 6.7 Implement Z-score signal construction
    - Calculate rolling mean and standard deviation
    - Standardize residuals to Z-scores
    - _Requirements: 4.7_
  
  - [ ]* 6.8 Write property test for Z-score properties
    - **Property 10: Z-Score Statistical Properties**
    - **Validates: Requirements 4.7**
    - Verify Z-scores have mean ≈ 0 and std ≈ 1
  
  - [ ] 6.9 Implement regime change detection
    - Use Chow test or rolling statistics to detect structural breaks
    - Flag regime changes in test results
    - _Requirements: 4.9_
  
  - [ ] 6.10 Implement train/test split and walk-forward validation
    - Create train/test split utilities (70/30 default)
    - Implement rolling window logic for walk-forward
    - Prevent lookahead bias by using only past data
    - _Requirements: 4.2, 4.12_
  
  - [ ] 6.11 Integrate Statistical Testing Agent with registry and LightRAG
    - Write structured test results to SQLite registry
    - Write summary lessons to LightRAG
    - Verify data quality reports exist before testing
    - _Requirements: 4.1, 4.10, 4.11_

- [ ] 7. Build Backtest Agent with cost attribution
  - [ ] 7.1 Implement backtest engine core (Python)
    - Signal generation from Z-scores
    - Position tracking with hedge ratio
    - Entry/exit logic based on thresholds
    - _Requirements: 5.1-5.2_

  - [ ] 7.2 Implement PnL calculation with cost attribution
    - Calculate gross PnL from position changes
    - Calculate commissions (0.1% default)
    - Calculate spread costs (0.05% default)
    - Calculate slippage (0.02% default)
    - Calculate funding rates for perpetual futures (0.01% per day)
    - Calculate borrow costs for short positions (0.5% annualized)
    - Calculate net PnL = gross PnL - all costs
    - _Requirements: 5.3-5.8_
  
  - [ ]* 7.3 Write property test for PnL conservation
    - **Property 11: Backtest PnL Conservation**
    - **Validates: Requirements 5.3-5.8**
    - Verify net_pnl + all_costs = gross_pnl within 0.01% tolerance
  
  - [ ] 7.4 Implement turnover calculation
    - Calculate total traded value per period
    - Compute turnover = traded_value / (period * avg_portfolio_value)
    - _Requirements: 5.9_
  
  - [ ]* 7.5 Write property test for turnover calculation
    - **Property 12: Turnover Calculation Consistency**
    - **Validates: Requirements 5.9**
    - Verify turnover formula correctness
  
  - [ ] 7.6 Implement walk-forward validation for backtests
    - Use rolling train/test windows (60 days train, 30 days test)
    - Non-overlapping test windows
    - Minimum 3 windows required
    - _Requirements: 5.2_
  
  - [ ] 7.7 Implement performance metrics calculation
    - Sharpe ratio, Sortino ratio, volatility
    - Max drawdown, win rate, profit factor
    - Tail-risk metrics (VaR, CVaR)
    - Average and median holding times
    - Exposure by asset and side
    - _Requirements: 6.8_

  - [ ] 7.8 Implement sensitivity analysis
    - Test backtest with 2x costs and 0.5x costs
    - Compare net PnL under different cost assumptions
    - _Requirements: 6.10_
  
  - [ ] 7.9 Implement baseline comparison
    - Create naive baseline (buy-and-hold or random entry)
    - Compare strategy Sharpe ratio against baseline
    - _Requirements: 6.9_
  
  - [ ] 7.10 Implement experiment reproducibility tracking
    - Record Git commit hash, config hash, dataset IDs
    - Record random seed, execution command, run timestamp
    - Store dependency lock file hash
    - _Requirements: 10.1-10.8, 5.11_
  
  - [ ] 7.11 Integrate Backtest Agent with registry and LightRAG
    - Write structured performance metrics to SQLite registry
    - Write summary conclusions to LightRAG
    - Verify data quality reports exist before backtesting
    - _Requirements: 5.1, 5.12, 5.13_
  
  - [ ]* 7.12 Write unit tests for backtest edge cases
    - Test empty trade sequences
    - Test single trade scenarios
    - Test extreme cost scenarios
    - _Requirements: 18.8_

- [ ] 8. Checkpoint - Ensure statistical testing and backtesting works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Build Hypothesis Agent
  - [ ] 9.1 Implement rule-based pair generation
    - Sector-based screening (same sector pairs)
    - Correlation-based screening (high correlation pairs)
    - Market cap filtering
    - _Requirements: 3.1_

  - [ ] 9.2 Implement novelty checking
    - Query LightRAG for similar past hypotheses using embedding similarity
    - Query SQLite registry for rejected pairs
    - Calculate novelty score (0.0-1.0)
    - _Requirements: 3.2, 3.3_
  
  - [ ] 9.3 Implement hypothesis linking
    - Create graph edges in LightRAG between similar hypotheses
    - Flag retests of previously rejected hypotheses
    - _Requirements: 3.6, 3.7_
  
  - [ ] 9.4 Integrate Hypothesis Agent with registry and LightRAG
    - Write generated hypotheses with rationale to LightRAG
    - Write hypothesis records to SQLite registry
    - _Requirements: 3.4, 3.5_
  
  - [ ]* 9.5 Write unit tests for hypothesis generation
    - Test sector-based screening logic
    - Test novelty checking with mock data
    - Test hypothesis linking
    - _Requirements: 18.8_

- [ ] 10. Build Critic Agent
  - [ ] 10.1 Implement lookahead bias detection
    - Check that signals use only past data
    - Verify no future information in position sizing
    - Confirm walk-forward windows don't overlap
    - _Requirements: 7.2_
  
  - [ ] 10.2 Implement overfitting detection
    - Check in-sample vs out-of-sample Sharpe ratio divergence
    - Check parameter count vs data points ratio
    - Detect perfect or near-perfect in-sample results
    - _Requirements: 7.3_
  
  - [ ] 10.3 Implement weak assumption detection
    - Check cointegration p-value proximity to threshold
    - Check half-life bounds (1-30 days)
    - Check for unaddressed regime changes
    - Check hedge ratio R² threshold
    - _Requirements: 7.4_

  - [ ] 10.4 Implement insufficient testing detection
    - Check minimum walk-forward windows (< 3)
    - Check test period length (< 30 days)
    - Check for missing sensitivity analysis
    - _Requirements: 7.5_
  
  - [ ] 10.5 Implement cost realism checks
    - Detect negative net PnL after costs
    - Detect excessive turnover (> 10x daily)
    - Check slippage assumption realism
    - _Requirements: 7.6, 7.7_
  
  - [ ] 10.6 Implement decision logic
    - Reject: critical issues (lookahead bias, negative net PnL)
    - Quarantine: moderate issues (weak statistics, high turnover)
    - Approve: no critical issues
    - _Requirements: 7.10_
  
  - [ ] 10.7 Integrate Critic Agent with registry and LightRAG
    - Write objections and detected risks to LightRAG
    - Write final review status to SQLite registry
    - _Requirements: 7.8, 7.9_
  
  - [ ]* 10.8 Write unit tests for critic detection logic
    - Test lookahead bias detection with synthetic examples
    - Test overfitting detection with mock results
    - Test decision logic for various scenarios
    - _Requirements: 18.8_

- [ ] 11. Build Memory Agent
  - [ ] 11.1 Implement LightRAG write operations
    - Store market knowledge (sectors, relationships)
    - Store development knowledge (architecture decisions)
    - Store agent decisions (hypotheses, test summaries, backtest conclusions)
    - Store manual notes from users
    - _Requirements: 8.2-8.10_

  - [ ] 11.2 Implement LightRAG query operations
    - Query by topic (retrieve relevant context)
    - Query by entity (find all info about asset/hypothesis/experiment)
    - Query by relationship (traverse graph for related hypotheses)
    - _Requirements: 8.2-8.10_
  
  - [ ] 11.3 Implement memory filtering rules
    - Prevent storing raw logs, prompts, large datasets, secrets
    - Reference registry IDs instead of duplicating numeric metrics
    - _Requirements: 8.11, 8.12_
  
  - [ ]* 11.4 Write integration tests for Memory Agent
    - Test write and query operations
    - Test memory filtering rules
    - Test graph traversal
    - _Requirements: 18.8_

- [ ] 12. Build Report Agent
  - [ ] 12.1 Implement backtest report generation
    - Generate HTML/PDF reports with all required content
    - Include equity curves, drawdown charts, cost attribution
    - Include all metrics from requirements 6.1-6.12
    - _Requirements: 6.1-6.12, 11.9_
  
  - [ ] 12.2 Implement data quality report generation
    - Summarize validation results, missing bars, outliers, alignment
    - _Requirements: 2.7-2.9_
  
  - [ ] 12.3 Implement visualization generation
    - Equity curve with drawdown overlay
    - Z-score signals with entry/exit markers
    - Cost attribution pie chart
    - Rolling Sharpe ratio
    - Trade distribution histogram
    - _Requirements: 11.4, 11.5_
  
  - [ ] 12.4 Integrate Report Agent with registry and LightRAG
    - Write report artifact links to SQLite registry
    - Write human-readable summaries to LightRAG
    - _Requirements: 11.10, 11.11_

  - [ ]* 12.5 Write unit tests for report generation
    - Test report content completeness
    - Test visualization generation
    - _Requirements: 18.8_

- [ ] 13. Build Coordinator Agent
  - [ ] 13.1 Implement task queue management
    - Create task queue with priority support
    - Implement task assignment to agents
    - Track task status and completion
    - _Requirements: 12.1_
  
  - [ ] 13.2 Implement experiment lifecycle state machine
    - States: NEW → DATA_VALIDATION → STATISTICAL_TESTING → BACKTESTING → CRITIC_REVIEW → REPORTING → FINAL_DECISION
    - Implement state transitions and validation
    - _Requirements: 12.2_
  
  - [ ] 13.3 Implement final decision logic
    - Reject: critical issues detected
    - Quarantine: moderate issues detected
    - Approve: no critical issues, eligible for demo review
    - Prevent retesting rejected hypotheses without justification
    - _Requirements: 12.8, 12.9_
  
  - [ ] 13.4 Integrate Coordinator Agent with registry and LightRAG
    - Write task lifecycle events to LightRAG
    - Write final decisions to SQLite registry
    - Write rejection/promotion reasons to both stores
    - _Requirements: 12.3-12.7_
  
  - [ ] 13.5 Implement agent tool permission enforcement
    - Define and enforce read/write permissions per agent
    - Validate agent operations against permissions
    - _Requirements: 12.10_
  
  - [ ]* 13.6 Write integration tests for Coordinator Agent
    - Test full experiment lifecycle
    - Test state machine transitions
    - Test error handling and quarantine logic
    - _Requirements: 18.8_


- [ ] 14. Checkpoint - Ensure all agents work together
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 15. Build CLI tools and scripted workflows
  - [ ] 15.1 Create CLI for data ingestion
    - Command to download OHLCV data for specified symbols
    - Command to validate data quality
    - Command to list available datasets
    - _Requirements: 22.6, 22.7_
  
  - [ ] 15.2 Create CLI for hypothesis management
    - Command to generate hypotheses (rule-based)
    - Command to list hypotheses with status
    - Command to manually add hypothesis
    - _Requirements: 22.9_
  
  - [ ] 15.3 Create CLI for experiment execution
    - Command to run full experiment (hypothesis → backtest → report)
    - Command to run individual stages (data validation, statistical testing, backtesting)
    - Command to query experiment status
    - _Requirements: 22.10_
  
  - [ ] 15.4 Create scripted pair-screening workflow
    - Script to screen pairs by sector
    - Script to screen pairs by correlation
    - Output candidate pairs for testing
    - _Requirements: 22.9_
  
  - [ ] 15.5 Create scripted statistical testing workflow
    - Script to run cointegration and ADF tests on pairs
    - Output test results to registry
    - _Requirements: 22.10_
  
  - [ ] 15.6 Create scripted backtest workflow
    - Script to run walk-forward backtests
    - Output backtest reports
    - _Requirements: 22.10_
  
  - [ ]* 15.7 Write integration tests for CLI tools
    - Test CLI commands with mock data
    - Test scripted workflows end-to-end
    - _Requirements: 18.8_


- [ ] 16. Build dashboard for monitoring and reporting
  - [ ] 16.1 Create Streamlit dashboard structure
    - Set up Streamlit app with navigation
    - Create page layout and styling
    - _Requirements: 11.1-11.8_
  
  - [ ] 16.2 Implement experiment list view
    - Display all experiments with status, hypothesis, and results
    - Filter by status, date, asset
    - Sort by various metrics
    - _Requirements: 11.1_
  
  - [ ] 16.3 Implement hypothesis status view
    - Display all hypotheses with novelty scores and status
    - Show similar past hypotheses
    - _Requirements: 11.2_
  
  - [ ] 16.4 Implement pair test results view
    - Display statistical test results for all pairs
    - Show cointegration p-values, hedge ratios, half-lives
    - _Requirements: 11.3_
  
  - [ ] 16.5 Implement backtest visualization view
    - Display equity curves with drawdown overlay
    - Show performance metrics table
    - Display cost attribution breakdown
    - _Requirements: 11.4, 11.5_
  
  - [ ] 16.6 Implement logs and errors view
    - Display agent logs and error messages
    - Filter by agent, severity, date
    - _Requirements: 11.6_
  
  - [ ] 16.7 Implement memory search functionality
    - Search LightRAG by topic, entity, or relationship
    - Display search results with context
    - _Requirements: 11.7_
  
  - [ ] 16.8 Implement manual approval queue
    - Display experiments eligible for demo review
    - Provide approve/reject buttons with reason input
    - Log approval decisions with timestamp
    - _Requirements: 11.8, 14.6-14.9_

  - [ ]* 16.9 Write integration tests for dashboard
    - Test dashboard pages render correctly
    - Test data loading and filtering
    - _Requirements: 18.8_

- [ ] 17. Implement failure handling and error recovery
  - [ ] 17.1 Implement data outage handling
    - Detect data outages and log them
    - Pause affected experiments
    - _Requirements: 15.1_
  
  - [ ] 17.2 Implement API error handling with retries
    - Exponential backoff for API errors
    - Log errors and retry attempts
    - _Requirements: 15.2_
  
  - [ ] 17.3 Implement stale data detection
    - Detect stale prices and reject signals
    - _Requirements: 15.3_
  
  - [ ] 17.4 Implement abnormal condition detection
    - Detect abnormal spreads and pause strategies
    - Detect missing funding rates and pause strategies
    - _Requirements: 15.4, 15.5_
  
  - [ ] 17.5 Implement experiment failure handling
    - Log backtest failures and quarantine experiments
    - Log agent failures and alert operator
    - _Requirements: 15.6, 15.7_
  
  - [ ] 17.6 Implement database and RAG failure handling
    - Detect failures and enter safe mode
    - Log failures and alert operator
    - _Requirements: 15.8_
  
  - [ ]* 17.7 Write unit tests for error handling
    - Test retry logic with mock failures
    - Test safe mode activation
    - _Requirements: 18.8_


- [ ] 18. Set up continuous integration and testing
  - [ ] 18.1 Create GitHub Actions workflow for Python
    - Run Ruff linting on all Python code
    - Run pytest with coverage reporting
    - Fail if coverage < 70% for core logic
    - _Requirements: 18.1-18.8_
  
  - [ ] 18.2 Create GitHub Actions workflow for property tests
    - Run all property-based tests with 100 iterations
    - Report failing examples with shrinking
    - _Requirements: 18.1-18.8_
  
  - [ ] 18.3 Create GitHub Actions workflow for reproducibility checks
    - Run experiments twice with same inputs
    - Verify metrics match within 0.1% tolerance
    - _Requirements: 18.6_
  
  - [ ]* 18.4 Write integration tests for CI workflows
    - Test that CI catches linting errors
    - Test that CI catches test failures
    - _Requirements: 18.1-18.8_

- [ ] 19. Create documentation and examples
  - [ ] 19.1 Write comprehensive README.md
    - Project overview and architecture
    - Setup instructions (uv sync, database init, LightRAG init)
    - Usage examples (CLI commands, scripted workflows)
    - Hardware requirements and constraints
    - _Requirements: 1.1-1.9, 22.1-22.14_
  
  - [ ] 19.2 Document repository structure
    - Explain purpose of each directory
    - Document file naming conventions
    - _Requirements: 27.1-27.16_
  
  - [ ] 19.3 Create architecture documentation
    - Executive summary
    - Agent role definitions with inputs/outputs/permissions
    - Data architecture (timezone handling, missing bars, alignment)
    - Database schema documentation
    - _Requirements: 1.1-1.9_

  - [ ] 19.4 Document data source evaluation
    - Document CCXT for crypto (exchanges, rate limits, historical depth)
    - Document Alpaca for equities (free tier limitations)
    - Document licensing and compliance considerations
    - _Requirements: 20.1-20.12_
  
  - [ ] 19.5 Create example workflows
    - Example: Ingest crypto data from Binance
    - Example: Screen pairs by sector
    - Example: Run statistical tests on pair
    - Example: Run backtest and generate report
    - _Requirements: 22.9, 22.10_
  
  - [ ] 19.6 Document legal disclaimers
    - State system is research tool, not financial advice
    - Document exchange terms of service requirements
    - Document audit log requirements
    - _Requirements: 26.1-26.10_

- [ ] 20. **[OPTIONAL/DEFERRED]** Implement Docker Compose for production-like testing
  - **NOTE: This task is OPTIONAL and should NOT block MVP. Defer to post-MVP or v2.**
  - [ ] 20.1 Create docker-compose.yml with profiles
    - Optional Postgres service (profile: postgres)
    - Optional Chroma server (profile: chroma)
    - Services only start when explicitly requested
    - _Requirements: 19.1-19.12_
  
  - [ ] 20.2 Create Dockerfiles for deployable services
    - Dockerfile for dashboard service
    - Dockerfile for agent services (if needed)
    - _Requirements: 19.1-19.12_
  
  - [ ] 20.3 Document Docker Compose usage
    - When to use Docker (production-like testing, cloud deployment)
    - When NOT to use Docker (local MVP development)
    - Startup commands and profiles
    - _Requirements: 19.10, 19.11_
  
  - [ ]* 20.4 Write integration tests for Docker deployment
    - Test services start correctly
    - Test health checks pass
    - _Requirements: 19.8_


- [ ] 21. **[DEFERRED/v2]** Document risk management and position sizing criteria
  - **NOTE: This task is DEFERRED to v2. For v1 MVP, only document criteria and assumptions. Do NOT implement demo/live execution logic.**
  - [ ] 21.1 Document position sizing assumptions
    - Document risk parameters for future demo trading
    - Document max risk per trade assumptions
    - Document max position size assumptions
    - _Requirements: 13.2, 13.3_
  
  - [ ] 21.2 Define promotion criteria documentation
    - Criteria for research → demo trading (documentation only)
    - Criteria for demo → live trading (documentation only)
    - Document required metrics and thresholds
    - _Requirements: 13.8, 13.9, 30.1-30.12_
  
  - [ ] 21.3 Document human approval gate requirements
    - Document approval workflow requirements for v2
    - Document approval logging requirements
    - Document integration points with dashboard
    - _Requirements: 13.10, 13.11, 14.6-14.9_

- [ ] 22. Final checkpoint and MVP validation
  - [ ] 22.1 Run end-to-end MVP validation
    - Ingest data for 50-100 assets (crypto or equities)
    - Generate and test at least 10 pairs
    - Complete at least 5 full experiments
    - Generate backtest reports for all experiments
    - _Requirements: 22.1-22.14_
  
  - [ ] 22.2 Verify MVP numeric targets
    - Assets: 50-100 liquid stocks or crypto pairs ✓
    - Timeframe: 15-minute bars ✓
    - Data history: Minimum 6 months per asset ✓
    - Pairs tested: Minimum 10 pairs ✓
    - Experiments completed: Minimum 5 ✓
    - Runtime: Full experiment < 5 minutes ✓
    - Reports: All 5 experiments have reports ✓
    - _Requirements: 22.14_

  - [ ] 22.3 Verify MVP functional criteria
    - Data ingestion works for CCXT (crypto) or Alpaca (equities) ✓
    - Data quality validation detects missing bars, outliers, duplicates ✓
    - Statistical tests correctly identify cointegrated pairs ✓
    - Backtests produce reproducible results ✓
    - Cost attribution breaks down all cost components ✓
    - Critic agent detects at least one issue ✓
    - Reports are human-readable and complete ✓
    - LightRAG stores and retrieves agent decisions ✓
    - Registry enables querying and comparison ✓
    - _Requirements: 22.1-22.14_
  
  - [ ] 22.4 Verify MVP non-functional criteria
    - System runs on local PC without Docker ✓
    - System runs on Oracle Cloud Always Free ARM ✓
    - Memory usage < 8GB during operation ✓
    - Disk usage < 20GB for MVP dataset ✓
    - No paid data dependencies ✓
    - All secrets managed through Infisical ✓
    - _Requirements: 22.1-22.14, 23.1-23.11_
  
  - [ ] 22.5 Document known limitations and future work
    - Document v1 scope boundaries
    - Document v2 planned features (demo trading)
    - Document v3 planned features (live trading)
    - Document optional Rust optimization path
    - _Requirements: 24.1-24.12_

- [ ] 23. Final review and handoff
  - Ensure all tests pass, ask the user if questions arise.
  - Review all documentation for completeness
  - Verify all MVP acceptance criteria met
  - Prepare system for user acceptance testing

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- **Task 20 (Docker Compose) is OPTIONAL/DEFERRED and should NOT block MVP**
- **Task 21 (Risk Management) is DEFERRED to v2 - only documentation in v1, no execution logic**
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties (14 properties total)
- Unit tests validate specific examples and edge cases
- Python is used for all implementations (Rust optimization is optional and not required for MVP)
- System must run without Docker using uv, SQLite, Parquet, and embedded LightRAG/vector storage
- Focus on correctness, reproducibility, and data quality over speed
- GitHub repository already exists at https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE


## Task Dependency Graph

**Note: This dependency graph excludes deferred tasks (20, 21). The first MVP execution follows waves 0-22 only.**

```json
{
  "waves": [
    {
      "id": 0,
      "tasks": ["1", "2.1"]
    },
    {
      "id": 1,
      "tasks": ["2.2", "2.3", "2.4", "3.1"]
    },
    {
      "id": 2,
      "tasks": ["3.2", "4.1", "4.3"]
    },
    {
      "id": 3,
      "tasks": ["4.2", "4.4", "4.5", "4.7", "4.9", "4.10"]
    },
    {
      "id": 4,
      "tasks": ["4.6", "4.8", "6.1", "6.2", "6.4", "6.5", "6.7", "6.9", "6.10"]
    },
    {
      "id": 5,
      "tasks": ["6.3", "6.6", "6.8", "6.11"]
    },
    {
      "id": 6,
      "tasks": ["7.1", "7.2", "7.4", "7.6", "7.10"]
    },
    {
      "id": 7,
      "tasks": ["7.3", "7.5", "7.7", "7.8", "7.9", "7.11"]
    },
    {
      "id": 8,
      "tasks": ["7.12", "9.1", "9.2"]
    },
    {
      "id": 9,
      "tasks": ["9.3", "9.4", "9.5"]
    },
    {
      "id": 10,
      "tasks": ["10.1", "10.2", "10.3", "10.4", "10.5"]
    },
    {
      "id": 11,
      "tasks": ["10.6", "10.7", "10.8"]
    },
    {
      "id": 12,
      "tasks": ["11.1", "11.2", "11.3"]
    },
    {
      "id": 13,
      "tasks": ["11.4", "12.1", "12.2", "12.3"]
    },
    {
      "id": 14,
      "tasks": ["12.4", "12.5"]
    },
    {
      "id": 15,
      "tasks": ["13.1", "13.2", "13.3"]
    },
    {
      "id": 16,
      "tasks": ["13.4", "13.5", "13.6"]
    },
    {
      "id": 17,
      "tasks": ["15.1", "15.2", "15.3", "15.4", "15.5", "15.6"]
    },
    {
      "id": 18,
      "tasks": ["15.7", "16.1"]
    },
    {
      "id": 19,
      "tasks": ["16.2", "16.3", "16.4", "16.5", "16.6", "16.7", "16.8"]
    },
    {
      "id": 20,
      "tasks": ["16.9", "17.1", "17.2", "17.3", "17.4", "17.5", "17.6"]
    },
    {
      "id": 21,
      "tasks": ["17.7", "18.1", "18.2", "18.3"]
    },
    {
      "id": 22,
      "tasks": ["18.4", "19.1", "19.2", "19.3", "19.4", "19.5", "19.6", "22.1"]
    },
    {
      "id": 23,
      "tasks": ["22.2", "22.3", "22.4", "22.5", "23"]
    }
  ]
}
```
