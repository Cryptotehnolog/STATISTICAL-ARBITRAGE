param(
    [string]$ExchangeId = "bybit",
    [int]$AssetCount = 50,
    [int]$MinSuccessfulAssets = 50,
    [int]$BarsPerAsset = 2,
    [string]$Timeframe = "15m",
    [string]$QuoteAsset = "USDT",
    [ValidateSet("swap", "spot", "future", "any")]
    [string]$MarketType = "swap",
    [string]$OutputJson = "data\live_market_data_acceptance\report.json"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repoRoot
try {
    Write-Output "Ручная opt-in проверка live market-data readiness."
    Write-Output "Эта проверка обращается к реальной бирже через CCXT и намеренно не входит в pre-commit/CI."
    Write-Output "Exchange: $ExchangeId; assets: $AssetCount; min successful: $MinSuccessfulAssets; timeframe: $Timeframe; bars: $BarsPerAsset; market type: $MarketType"

    uv run python -m stat_arb.scripts.check_live_market_data_acceptance `
        --exchange-id $ExchangeId `
        --asset-count $AssetCount `
        --min-successful-assets $MinSuccessfulAssets `
        --bars-per-asset $BarsPerAsset `
        --timeframe $Timeframe `
        --quote-asset $QuoteAsset `
        --market-type $MarketType `
        --output-json $OutputJson

    if ($LASTEXITCODE -ne 0) {
        throw "Live market-data acceptance не пройден. Отчет: $OutputJson"
    }

    Write-Output "Live market-data acceptance пройден. Отчет: $OutputJson"
}
finally {
    Pop-Location
}
