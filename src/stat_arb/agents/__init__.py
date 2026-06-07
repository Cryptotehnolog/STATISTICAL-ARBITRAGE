"""Agent service boundaries."""

from stat_arb.agents.backtest import (
    BacktestAgentInput,
    BacktestAgentRunResult,
    run_backtest_agent_persistence,
)
from stat_arb.agents.hypothesis import (
    HypothesisGenerationConfig,
    HypothesisGenerationResult,
    HypothesisLinkingConfig,
    HypothesisMemorySearchResult,
    HypothesisNoveltyAssessment,
    HypothesisNoveltyConfig,
    HypothesisUniverseAsset,
    generate_rule_based_hypotheses,
)
from stat_arb.agents.statistical_testing import (
    StatisticalTestingInput,
    StatisticalTestingRunResult,
    run_statistical_testing,
)

__all__ = [
    "BacktestAgentInput",
    "BacktestAgentRunResult",
    "HypothesisGenerationConfig",
    "HypothesisGenerationResult",
    "HypothesisLinkingConfig",
    "HypothesisMemorySearchResult",
    "HypothesisNoveltyAssessment",
    "HypothesisNoveltyConfig",
    "HypothesisUniverseAsset",
    "StatisticalTestingInput",
    "StatisticalTestingRunResult",
    "generate_rule_based_hypotheses",
    "run_backtest_agent_persistence",
    "run_statistical_testing",
]
