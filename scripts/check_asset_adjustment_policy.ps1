$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка asset-class adjustment policy..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_domain_models.py::test_dataset_enforces_asset_class_specific_adjustment_policy `
        tests/unit/test_storage_data_quality.py::test_persist_ohlcv_ingestion_result_rejects_raw_equity_adjustments `
        tests/unit/test_check_asset_adjustment_policy.py `
        --no-cov -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}

Write-Output "Проверка asset-class adjustment policy прошла."
