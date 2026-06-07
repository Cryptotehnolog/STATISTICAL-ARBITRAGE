$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$roots = @(
    "src/stat_arb/agents",
    "src/stat_arb/statistics",
    "src/stat_arb/statistical_testing",
    "src/stat_arb/backtesting"
)
$boundaryPattern = "OHLCVBatch|StatisticalTestResult|cointegration|adf"
$alignmentPattern = "align_ohlcv_pair|PairAlignmentResult|aligned_timestamps"
$reviewOnlyModules = @(
    "src/stat_arb/agents/critic.py"
)
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
        $normalizedRelative = ($relative.TrimStart(".\") -replace "\\", "/")
        if ($reviewOnlyModules -contains $normalizedRelative) {
            continue
        }
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
