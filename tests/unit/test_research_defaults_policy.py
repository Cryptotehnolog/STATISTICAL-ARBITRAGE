"""Guards for the research defaults policy."""

from pathlib import Path

RESEARCH_CONTRACTS_PATH = Path("docs/knowledge/research_workflow_contracts.md")


def test_research_defaults_policy_is_documented() -> None:
    """The project should distinguish hidden research defaults from safe technical defaults."""
    text = RESEARCH_CONTRACTS_PATH.read_text(encoding="utf-8")

    assert "## Defaults Policy" in text
    assert "Hidden research defaults are not allowed" in text
    assert "Technical defaults are allowed" in text
    assert "named persisted preset" in text
    assert "config hash" in text
    assert "old planning examples" in text


def test_research_impacting_defaults_are_not_hidden_in_runtime_boundaries() -> None:
    """Statistical and data-quality runtime code should require explicit research assumptions."""
    forbidden_patterns = {
        "src/stat_arb/agents/statistical_testing.py": (
            "alpha: float =",
            "periods_per_day: float =",
            "regime_window: int =",
        ),
        "src/stat_arb/statistical/cointegration.py": (
            "alpha: float =",
            "multiple_testing_method: MultipleTestingMethod =",
            "method: MultipleTestingMethod =",
        ),
        "src/stat_arb/statistical/stationarity.py": (
            "alpha: float =",
            'regression: str = "',
            'autolag: str | None = "',
        ),
        "src/stat_arb/statistical/mean_reversion.py": ("periods_per_day: float =",),
        "src/stat_arb/statistical/regime.py": (
            "mean_shift_threshold: float =",
            "volatility_ratio_threshold: float =",
        ),
        "src/stat_arb/data_quality/ohlcv.py": (
            "max_missing_bar_ratio: float =",
            "max_abnormal_volume_ratio: float =",
            "volume_spike_multiplier: float =",
            "config: OHLCVQualityConfig | None = None",
            "OHLCVQualityConfig()",
        ),
        "src/stat_arb/backtest/core.py": (
            "entry_threshold: float =",
            "exit_threshold: float =",
            "exit_policy: BacktestExitPolicyConfig =",
        ),
    }

    for path, patterns in forbidden_patterns.items():
        text = Path(path).read_text(encoding="utf-8")
        for pattern in patterns:
            assert pattern not in text, f"{path} hides research-impacting default: {pattern}"
