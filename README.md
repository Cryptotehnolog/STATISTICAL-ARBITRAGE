# Statistical Arbitrage: Multi-Agent Quantitative Research System

A reproducible research platform for statistical arbitrage and pairs trading, featuring automated hypothesis generation, rigorous statistical validation, backtesting with detailed cost attribution, and long-term memory management via LightRAG.

## 🎯 Project Overview

This system is designed as a **staged development platform** for quantitative research:

- **v1 (Current)**: Research platform with data quality controls, statistical validation, and cost modeling
- **v2 (Future)**: Demo trading with paper accounts and risk management
- **v3 (Future)**: Limited live trading with strict approval gates

**Key Features:**
- Multi-agent architecture with specialized agents for data, hypothesis generation, statistical testing, backtesting, and review
- LightRAG-powered long-term memory and knowledge graph
- Rigorous data quality validation (timezone normalization, missing bars, outliers, alignment)
- Statistical testing (Engle-Granger cointegration, ADF tests, hedge ratio estimation)
- Walk-forward backtesting with detailed cost attribution
- Automated critic review for lookahead bias, overfitting, and weak assumptions
- Interactive dashboard for experiment monitoring and report review

## 🏗️ Architecture

### System Design Principles

1. **Correctness over speed**: Prioritize reproducibility, data quality, and statistical rigor
2. **Constrained resources**: Operate efficiently on local hardware (i5-1335U, 32GB RAM) and Oracle Cloud Always Free ARM
3. **Staged complexity**: Start simple (research), add demo trading, enable limited live trading
4. **Memory from day one**: LightRAG provides long-term memory and knowledge graph
5. **Human in the loop**: Mandatory approval gates for critical decisions
6. **Python-first with optional Rust optimization**: Start with Python, add Rust only when profiling proves necessary
7. **Minimal infrastructure for v1**: SQLite + embedded vector store (FAISS/NanoVectorDB)

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                          │
│              Dashboard (Streamlit) + CLI Tools               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Coordinator Agent                         │
│           Task Queue & Experiment Lifecycle                  │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Data Agent   │    │ Hypothesis   │    │ Statistical  │
│              │    │ Agent        │    │ Testing      │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Backtest     │    │ Critic       │    │ Report       │
│ Agent        │    │ Agent        │    │ Agent        │
└──────────────┘    └──────────────┘    └──────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Memory Agent                            │
│                  LightRAG Operations                         │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ LightRAG     │    │ SQLite       │    │ Parquet      │
│ (Memory)     │    │ (Registry)   │    │ (Data)       │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Experiment Lifecycle

```
NEW → DATA_VALIDATION → STATISTICAL_TESTING → BACKTESTING → 
CRITIC_REVIEW → REPORTING → FINAL_DECISION
```

**Final Decisions:**
- **Reject**: Critical issues detected (lookahead bias, negative net PnL, insufficient testing)
- **Quarantine**: Moderate issues detected (weak statistics, high turnover, borderline costs)
- **Approve**: No critical issues, eligible for human review

## 🚀 Quick Start

### Prerequisites

- **Python**: 3.11 or higher
- **uv**: Python dependency manager ([installation guide](https://github.com/astral-sh/uv))
- **Hardware**: Minimum 8GB RAM, 20GB disk space
- **OS**: Windows, Linux, or macOS

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE.git
   cd STATISTICAL-ARBITRAGE
   ```

2. **Install dependencies with uv:**
   ```bash
   uv sync
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Set up Infisical for secrets management:**
   - Create an account at [Infisical](https://app.infisical.com)
   - Create a project and get your credentials
   - Add credentials to `.env`:
     ```
     INFISICAL_CLIENT_ID=your_client_id
     INFISICAL_CLIENT_SECRET=your_client_secret
     INFISICAL_PROJECT_ID=your_project_id
     ```

5. **Initialize the database:**
   ```bash
   uv run python -m stat_arb.scripts.init_database
   ```

6. **Initialize LightRAG:**
   ```bash
   uv run python -m stat_arb.scripts.init_lightrag
   ```
   For a heavier local verification that loads the embedding model and performs
   an insert/query smoke test:
   ```bash
   uv run python -m stat_arb.scripts.init_lightrag --smoke-test
   ```
   To populate LightRAG with curated project knowledge from README, docs, and
   `.kiro/specs` using the Windows-friendly NanoVectorDB backend:
   ```bash
   .\scripts\seed_lightrag.ps1
   ```
   On the first machine run, allow the embedding model download once:
   ```bash
   .\scripts\seed_lightrag.ps1 --allow-model-download
   ```
   To enable LightRAG entity/relation extraction through an OpenAI-compatible gateway:
   ```bash
   .\scripts\seed_lightrag.ps1 --llm-provider openai_compatible --openai-compatible-model my-ai
   ```
   To run the same graph extraction smoke test through OmniRoute:
   ```bash
   .\scripts\smoke_lightrag_omniroute.ps1
   ```

### Running the System

**Start the dashboard:**
```bash
uv run streamlit run src/stat_arb/dashboard/app.py
```

**Run CLI commands:**
```bash
# Ingest data
uv run stat-arb data ingest --symbols BTC/USDT,ETH/USDT --exchange binance --timeframe 15m

# Generate hypotheses
uv run stat-arb hypothesis generate --method sector --limit 10

# Run full experiment
uv run stat-arb experiment run --hypothesis-id <uuid>

# View experiment status
uv run stat-arb experiment list --status completed
```

## 📊 Data Sources

### Cryptocurrency (Primary)
- **CCXT Library**: Multi-exchange support (Binance, Coinbase Pro, Kraken)
- **Advantages**: Free, reliable, excellent intraday coverage
- **Limitations**: Rate limits vary by exchange
- **Intraday availability**: Excellent (1-minute to 1-hour bars)
- **Historical depth**: 1-2 years for minute data

### US Equities
- **Alpaca API**: Free tier available
- **Advantages**: Good intraday data, reliable
- **Limitations**: US stocks only, rate limits on free tier
- **Intraday availability**: Good (1-minute to 1-hour bars)
- **Historical depth**: Limited on free tier (recent months)

**Note**: Yahoo Finance is NOT recommended for intraday data due to significant gaps and reliability issues.

## 🧪 Testing

**Run all tests:**
```bash
uv run pytest
```

**Run with coverage:**
```bash
uv run pytest --cov=stat_arb --cov-report=html
```

**Run property-based tests:**
```bash
uv run pytest -m property
```

**Run specific test categories:**
```bash
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m "not slow"    # Skip slow tests
```

## 🔧 Development

**Linting and formatting:**
```bash
uv run ruff check .
uv run ruff format .
```

**Type checking:**
```bash
uv run mypy src/stat_arb
```

**Pre-commit checks:**
```bash
uv run pytest && uv run ruff check . && uv run mypy src/stat_arb
```

## 📁 Repository Structure

```
.
├── src/stat_arb/           # Main source code
│   ├── agents/             # Agent implementations
│   ├── models/             # Pydantic data models
│   ├── storage/            # Database and LightRAG interfaces
│   ├── data/               # Data ingestion and validation
│   ├── statistical/        # Statistical testing functions
│   ├── backtest/           # Backtesting engine
│   ├── dashboard/          # Streamlit dashboard
│   ├── cli/                # CLI commands
│   └── utils/              # Shared utilities
├── tests/                  # Test suite
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── property/           # Property-based tests
├── data/                   # Data storage (gitignored)
│   ├── parquet/            # OHLCV data
│   ├── lightrag/           # LightRAG storage
│   ├── vector_store/       # Embedded vector store
│   └── reports/            # Generated reports
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── .github/                # GitHub Actions CI/CD
├── pyproject.toml          # Project configuration
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 🔒 Security and Secrets Management

**All secrets MUST be managed through Infisical:**
- API keys for exchanges (Binance, Coinbase, Kraken, Alpaca)
- Database passwords (if using PostgreSQL)
- LLM API keys (if using OpenAI)
- Webhook tokens and Telegram bot tokens

**Never commit secrets to Git:**
- `.env` is gitignored
- Use `.env.example` for documentation only
- Secrets are loaded from Infisical at runtime

## 📈 Hardware Requirements

### Local Development (Minimum)
- **CPU**: Intel i5 or equivalent
- **RAM**: 8GB (16GB recommended)
- **Disk**: 20GB free space
- **Network**: Standard residential internet

### Recommended Configuration
- **CPU**: Intel i5-1335U or better
- **RAM**: 32GB
- **Disk**: 100GB SSD
- **Network**: Stable connection for data ingestion

### Oracle Cloud Always Free (Production)
- **CPU**: 4 vCPU ARM
- **RAM**: 24GB
- **Disk**: 200GB
- **Cost**: Free tier

## 🎓 Example Workflows

### 1. Ingest Cryptocurrency Data
```bash
# Download 6 months of 15-minute bars for BTC and ETH
uv run stat-arb data ingest \
  --symbols BTC/USDT,ETH/USDT \
  --exchange binance \
  --timeframe 15m \
  --start-date 2024-07-01 \
  --end-date 2025-01-01
```

### 2. Screen Pairs by Sector
```bash
# Generate candidate pairs from same sector
uv run stat-arb hypothesis generate \
  --method sector \
  --sector technology \
  --limit 20
```

### 3. Run Statistical Tests
```bash
# Test cointegration for a specific pair
uv run stat-arb test statistical \
  --asset-a BTC/USDT \
  --asset-b ETH/USDT \
  --train-window 60 \
  --test-window 30
```

### 4. Run Backtest and Generate Report
```bash
# Run full backtest with walk-forward validation
uv run stat-arb backtest run \
  --hypothesis-id <uuid> \
  --entry-threshold 2.0 \
  --exit-threshold 0.5 \
  --generate-report
```

### 5. View Results in Dashboard
```bash
# Start dashboard and navigate to experiments page
uv run streamlit run src/stat_arb/dashboard/app.py
```

## 📚 Documentation

- **Architecture**: See `docs/architecture.md` for detailed system design
- **Agent Roles**: See `docs/agents.md` for agent responsibilities and interfaces
- **Data Architecture**: See `docs/data.md` for data quality validation and alignment rules
- **API Reference**: See `docs/api.md` for Python API documentation
- **Database Schema**: See `docs/schema.md` for SQLite registry structure

## ⚠️ Legal Disclaimers

**This system is a research tool, not financial advice:**
- No guarantees of profitability or performance
- Past performance does not indicate future results
- Use at your own risk

**Exchange Terms of Service:**
- Comply with all exchange terms of service
- Respect rate limits and API usage policies
- Ensure proper licensing for data usage

**Audit Logs:**
- All agent decisions are logged to LightRAG
- All experiments are tracked in the SQLite registry
- Maintain audit trails for compliance

## 🛣️ Roadmap

### v1 (Current): Research Platform
- ✅ Data ingestion with quality validation
- ✅ Hypothesis generation and novelty checking
- ✅ Statistical testing (cointegration, ADF, hedge ratio)
- ✅ Walk-forward backtesting with cost attribution
- ✅ Critic review for bias and overfitting
- ✅ LightRAG memory and knowledge graph
- ✅ Interactive dashboard and CLI tools

### v2 (Future): Demo Trading
- ⏳ Paper trading with simulated execution
- ⏳ Risk management and position sizing
- ⏳ Real-time data feeds
- ⏳ Kill switch and emergency stop
- ⏳ Human approval gates

### v3 (Future): Limited Live Trading
- ⏳ Live execution with strict risk limits
- ⏳ Advanced monitoring and alerting
- ⏳ Multi-strategy portfolio management
- ⏳ Performance attribution and reporting

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass (`uv run pytest`)
5. Run linting (`uv run ruff check .`)
6. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- **LightRAG**: Long-term memory and knowledge graph framework
- **CCXT**: Unified cryptocurrency exchange API
- **Statsmodels**: Statistical testing and econometrics
- **Streamlit**: Interactive dashboard framework

## 📧 Contact

- **GitHub**: [Cryptotehnolog](https://github.com/Cryptotehnolog)
- **Repository**: [STATISTICAL-ARBITRAGE](https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE)
- **Issues**: [Report bugs or request features](https://github.com/Cryptotehnolog/STATISTICAL-ARBITRAGE/issues)

---

**Built with ❤️ for quantitative researchers**
