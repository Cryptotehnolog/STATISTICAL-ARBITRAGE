"""Tests for the asset-class adjustment policy checkpoint script."""

from pathlib import Path


def test_asset_adjustment_policy_script_covers_domain_and_storage_guards() -> None:
    """The guard should prove equities cannot bypass adjusted-data policy."""
    script = Path("scripts/check_asset_adjustment_policy.ps1")

    assert script.exists()
    content = script.read_text(encoding="utf-8")

    assert (
        "tests/unit/test_domain_models.py::"
        "test_dataset_enforces_asset_class_specific_adjustment_policy"
    ) in content
    assert (
        "tests/unit/test_storage_data_quality.py::"
        "test_persist_ohlcv_ingestion_result_rejects_raw_equity_adjustments"
    ) in content
    assert "tests/unit/test_check_asset_adjustment_policy.py" in content
