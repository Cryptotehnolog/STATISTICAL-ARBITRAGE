"""Guards for Task 19 documentation slices."""

from pathlib import Path

README_PATH = Path("README.md")
ARCHITECTURE_PATH = Path("docs/architecture.md")
AGENTS_PATH = Path("docs/agents.md")
DATA_PATH = Path("docs/data.md")
SCHEMA_PATH = Path("docs/schema.md")
DATA_SOURCES_PATH = Path("docs/data_sources.md")


def test_readme_links_core_task_19_documentation() -> None:
    """README should point users to real Task 19 docs, not phantom placeholders."""
    readme = README_PATH.read_text(encoding="utf-8")

    for path in (
        "docs/architecture.md",
        "docs/agents.md",
        "docs/data.md",
        "docs/data_sources.md",
        "docs/schema.md",
    ):
        assert f"`{path}`" in readme
        assert Path(path).exists()


def test_architecture_doc_describes_current_boundaries() -> None:
    """Architecture docs should describe the actual v1 boundaries."""
    text = ARCHITECTURE_PATH.read_text(encoding="utf-8")

    assert "ApeRAG" in text
    assert "Memory Agent policy" in text
    assert "SQLite" in text
    assert "Parquet" in text
    assert "Python-first" in text
    assert "Rust" in text
    assert "OmniRoute" in text
    assert "Infisical" in text
    assert "не является live trading" in text


def test_agents_doc_lists_agent_permissions_and_forbids_direct_memory_writes() -> None:
    """Agent docs should preserve registry/memory permission boundaries."""
    text = AGENTS_PATH.read_text(encoding="utf-8")

    for agent_name in (
        "Data Agent",
        "Hypothesis Agent",
        "Statistical Testing Agent",
        "Backtest Agent",
        "Critic Agent",
        "Report Agent",
        "Coordinator Agent",
        "Memory Agent",
    ):
        assert agent_name in text

    assert "не пишет напрямую в ApeRAG" in text
    assert "Structured Registry" in text
    assert "Memory Agent policy" in text


def test_data_doc_covers_quality_rules_and_one_bar_diagnostic() -> None:
    """Data docs should explain data quality and one-bar diagnostic behavior."""
    text = DATA_PATH.read_text(encoding="utf-8")

    assert "UTC" in text
    assert "missing bars" in text
    assert "duplicate timestamps" in text
    assert "alignment" in text
    assert "insufficient_data" in text
    assert "одна свеча" in text
    assert "Parquet" in text


def test_schema_doc_documents_registry_as_numeric_source_of_truth() -> None:
    """Schema docs should keep structured metrics in registry, not memory."""
    text = SCHEMA_PATH.read_text(encoding="utf-8")

    assert "Structured Registry" in text
    assert "SQLite" in text
    assert "source of truth" in text
    assert "ApeRAG" in text
    assert "не хранит raw metrics" in text
    assert "hypotheses" in text
    assert "experiments" in text
    assert "backtest" in text


def test_data_source_doc_sets_bybit_first_policy_and_excludes_coinbase_kraken() -> None:
    """Task 19.4 should document the actual crypto exchange roadmap."""
    text = DATA_SOURCES_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")

    assert "Bybit" in text
    assert "primary стартовая crypto exchange" in text
    assert "Binance" in text
    assert "OKX" in text
    assert "Deribit" in text
    assert "Coinbase Pro" not in text
    assert "Kraken" not in text
    assert "--exchange bybit" in readme
    assert "Coinbase Pro" not in readme
    assert "Kraken" not in readme


def test_data_source_doc_keeps_live_exchange_smoke_opt_in() -> None:
    """Live exchange checks should stay outside deterministic commit checks."""
    text = DATA_SOURCES_PATH.read_text(encoding="utf-8")

    assert "live CCXT smoke" in text
    assert "opt-in" in text
    assert "pre-commit" in text
    assert "rate limits" in text
    assert "terms of service" in text
