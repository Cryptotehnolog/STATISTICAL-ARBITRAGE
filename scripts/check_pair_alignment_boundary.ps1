$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$roots = @(
    "src/stat_arb/agents",
    "src/stat_arb/statistics",
    "src/stat_arb/statistical_testing",
    "src/stat_arb/backtesting"
)
$boundaryPattern = "OHLCVBatch|StatisticalTestResult|cointegration|adf|hedge_ratio"
$alignmentPattern = "align_ohlcv_pair|PairAlignmentResult|aligned_timestamps"
$violations = @()

Write-Output "Проверка pair alignment boundary..."

foreach ($root in $roots) {
    $path = Join-Path $repoRoot $root
    if (-not (Test-Path -LiteralPath $path)) {
        continue
    }

    $files = Get-ChildItem -LiteralPath $path -Recurse -File -Filter "*.py"
    foreach ($file in $files) {
        $relative = Resolve-Path -LiteralPath $file.FullName -Relative
        $content = Get-Content -LiteralPath $file.FullName -Raw
        if ($content -match $boundaryPattern -and $content -notmatch $alignmentPattern) {
            $violations += $relative
        }
    }
}

if ($violations.Count -gt 0) {
    Write-Error (
        "Найдены pair/statistical modules без явного timestamp alignment через align_ohlcv_pair: " +
        ($violations -join ", ")
    )
}

Write-Output "Проверка pair alignment boundary прошла."
