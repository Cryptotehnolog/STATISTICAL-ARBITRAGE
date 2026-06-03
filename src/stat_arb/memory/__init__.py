"""Memory module for long-term project memory integration.

This module exposes the active ApeRAG memory boundary plus legacy LightRAG classes kept
temporarily for migration and tests.
"""

from stat_arb.memory.aperag_client import (
    ApeRAGCollection,
    ApeRAGDocumentStatus,
    ApeRAGError,
    ApeRAGGraphSummary,
    ApeRAGMemoryClient,
    ApeRAGSearchResult,
    MemoryRecordType,
    MemoryWriteRequest,
)
from stat_arb.memory.config import ApeRAGConfig, LightRAGConfig
from stat_arb.memory.lightrag_client import LightRAGClient

__all__ = [
    "ApeRAGCollection",
    "ApeRAGConfig",
    "ApeRAGDocumentStatus",
    "ApeRAGError",
    "ApeRAGGraphSummary",
    "ApeRAGMemoryClient",
    "ApeRAGSearchResult",
    "LightRAGClient",
    "LightRAGConfig",
    "MemoryRecordType",
    "MemoryWriteRequest",
]
