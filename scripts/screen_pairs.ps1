param(
    [Parameter(Mandatory = $true)]
    [string]$AssetsJson,

    [Parameter(Mandatory = $true)]
    [string]$CorrelationsJson,

    [Parameter(Mandatory = $true)]
    [string]$PValuesJson,

    [Parameter(Mandatory = $true)]
    [double]$MinAbsCorrelation,

    [Parameter(Mandatory = $true)]
    [long]$MinMarketCap,

    [long]$MaxMarketCap = -1,

    [Parameter(Mandatory = $true)]
    [int]$MaxPairs,

    [Parameter(Mandatory = $true)]
    [string]$MultipleTestingMethod,

    [Parameter(Mandatory = $true)]
    [double]$CandidateAlpha,

    [Parameter(Mandatory = $true)]
    [double]$InitialNoveltyScore,

    [Parameter(Mandatory = $true)]
    [string]$InitialStatus,

    [Parameter(Mandatory = $true)]
    [string]$Source,

    [Parameter(Mandatory = $true)]
    [string]$CreatedBy,

    [Parameter(Mandatory = $true)]
    [string]$DbPath,

    [switch]$RequireSameSector
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-RequiredPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$PathValue,

        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $resolved = Resolve-Path -LiteralPath $PathValue -ErrorAction Stop
    if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
        throw "$Name должен быть файлом: $PathValue"
    }
    return $resolved.Path
}

$assetsPath = Resolve-RequiredPath -PathValue $AssetsJson -Name "AssetsJson"
$correlationsPath = Resolve-RequiredPath -PathValue $CorrelationsJson -Name "CorrelationsJson"
$pValuesPath = Resolve-RequiredPath -PathValue $PValuesJson -Name "PValuesJson"

# Boundary: uv run stat-arb hypothesis generate
$generateArgs = @(
    "run", "stat-arb", "hypothesis", "generate",
    "--assets-json", $assetsPath,
    "--correlations-json", $correlationsPath,
    "--p-values-json", $pValuesPath,
    "--min-abs-correlation", ([string]$MinAbsCorrelation),
    "--min-market-cap", ([string]$MinMarketCap),
    "--max-pairs", ([string]$MaxPairs),
    "--multiple-testing-method", $MultipleTestingMethod,
    "--candidate-alpha", ([string]$CandidateAlpha),
    "--initial-novelty-score", ([string]$InitialNoveltyScore),
    "--initial-status", $InitialStatus,
    "--source", $Source,
    "--created-by", $CreatedBy,
    "--db-path", $DbPath
)

if ($RequireSameSector) {
    $generateArgs += "--require-same-sector"
}
else {
    $generateArgs += "--allow-cross-sector"
}

if ($MaxMarketCap -ge 0) {
    $generateArgs += @("--max-market-cap", ([string]$MaxMarketCap))
}

Push-Location $repoRoot
try {
    Write-Output "Запуск pair-screening workflow..."
    & uv @generateArgs
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Output "Кандидаты для testing:"
    uv run stat-arb hypothesis list --db-path $DbPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
