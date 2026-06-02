"""Unit tests for the OmniRoute LightRAG benchmark helpers."""

from stat_arb.scripts.benchmark_lightrag_omniroute import BenchmarkResult, rank_results


def test_rank_results_prefers_graph_quality_before_latency() -> None:
    """Ranking should prefer better extraction quality over raw speed."""
    results = [
        BenchmarkResult("fast-weak", "passed", 1.0, 3, 1, ""),
        BenchmarkResult("slow-rich", "passed", 9.0, 6, 5, ""),
        BenchmarkResult("failed", "failed", 0.5, 0, 0, "bad"),
    ]

    ranked = rank_results(results)

    assert [result.model for result in ranked] == ["slow-rich", "fast-weak", "failed"]


def test_rank_results_uses_latency_after_equal_quality() -> None:
    """Ranking should use latency when graph quality is tied."""
    results = [
        BenchmarkResult("slow", "passed", 5.0, 4, 3, ""),
        BenchmarkResult("fast", "passed", 2.0, 4, 3, ""),
    ]

    ranked = rank_results(results)

    assert [result.model for result in ranked] == ["fast", "slow"]
