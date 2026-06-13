"""Dashboard-facing Memory Agent query factory."""

from __future__ import annotations

from pathlib import Path

from stat_arb.dashboard.data import (
    DashboardMemorySearchRequest,
    DashboardMemorySearchResult,
    run_dashboard_memory_search,
)
from stat_arb.memory import ApeRAGMemoryClient, MemoryAgentService, MemoryReadThroughCache


def query_dashboard_memory(
    request: DashboardMemorySearchRequest,
    *,
    cache_path: Path | str = Path("data/aperag/dashboard_memory_read_cache.json"),
) -> DashboardMemorySearchResult:
    """Run one dashboard memory query through Memory Agent and close the backend client."""
    with ApeRAGMemoryClient() as client:
        service = MemoryAgentService(
            client,
            read_through_cache=MemoryReadThroughCache(cache_path),
        )
        return run_dashboard_memory_search(request, memory_service=service)
