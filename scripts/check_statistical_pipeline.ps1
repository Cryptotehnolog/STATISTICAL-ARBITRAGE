$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Write-Output "Проверка statistical testing pipeline..."

Push-Location $repoRoot
try {
    uv run pytest `
        tests/unit/test_statistical_testing_agent.py `
        tests/unit/test_cointegration.py `
        tests/unit/test_stationarity.py `
        tests/unit/test_hedge_ratio.py `
        tests/unit/test_mean_reversion.py `
        tests/unit/test_regime.py `
        tests/unit/test_zscore.py `
        tests/unit/test_validation_windows.py `
        tests/unit/test_statistical_properties.py `
        --no-cov -p no:cacheprovider
}
finally {
    Pop-Location
}

Write-Output "Проверка statistical testing pipeline прошла."
