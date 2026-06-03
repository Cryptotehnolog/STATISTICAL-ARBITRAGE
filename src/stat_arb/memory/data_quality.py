"""Memory Agent helpers for data quality failure records."""

from __future__ import annotations

from stat_arb.data_quality import summarize_data_quality_failure
from stat_arb.domain import DataQualityFailureSummary, DataQualityReport
from stat_arb.memory.aperag_client import MemoryRecordType, MemoryWriteRequest
from stat_arb.memory.policy import MemoryAgentService, MemoryWriteResult


def data_quality_failure_memory_request(
    report: DataQualityReport,
) -> MemoryWriteRequest:
    """Convert a failed quality report into a policy-safe Memory Agent request."""
    summary = summarize_data_quality_failure(report)
    return _summary_to_memory_request(summary)


def write_data_quality_failure_memory(
    service: MemoryAgentService,
    report: DataQualityReport,
) -> MemoryWriteResult:
    """Write a failed data-quality summary through the Memory Agent policy layer."""
    return service.write(data_quality_failure_memory_request(report))


def _summary_to_memory_request(summary: DataQualityFailureSummary) -> MemoryWriteRequest:
    return MemoryWriteRequest(
        record_type=MemoryRecordType.DATA_QUALITY_FAILURE,
        title=f"Data quality failure: {summary.symbol} {summary.timeframe}",
        body=summary.summary,
        source_id=f"data-quality-report-{summary.report_id}",
        registry_reference=f"registry:{summary.registry_reference}",
        tags=["data-quality", "failure", summary.symbol.lower(), summary.timeframe],
        metadata={
            "dataset_id": str(summary.dataset_id),
            "report_id": str(summary.report_id),
            "source": str(summary.source),
            "timeframe": summary.timeframe,
        },
    )
