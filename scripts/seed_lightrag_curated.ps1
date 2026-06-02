param(
    [switch]$Apply,
    [string]$Model = "my-ai",
    [string]$BaseUrl = "http://localhost:20128/v1",
    [string]$ApiKey = $env:OMNIROUTE_API_KEY,
    [int]$MaxDocumentChars = 12000,
    [int]$MaxTotalChars = 30000,
    [int]$MaxWorkers = 1,
    [switch]$Force,
    [switch]$AllowModelDownload
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Expected virtualenv Python at $python. Run 'uv sync' first."
}

Push-Location $repoRoot
try {
    $argsList = @(
        "-m",
        "stat_arb.scripts.seed_lightrag",
        "--llm-provider",
        "openai_compatible",
        "--openai-compatible-model",
        $Model,
        "--openai-compatible-base-url",
        $BaseUrl,
        "--max-document-chars",
        $MaxDocumentChars,
        "--max-total-chars",
        $MaxTotalChars,
        "--max-workers",
        $MaxWorkers,
        "--source-pattern",
        "docs/knowledge/*.md"
    )
    if ($ApiKey) {
        $argsList += @("--openai-compatible-api-key", $ApiKey)
    }
    if ($AllowModelDownload) {
        $argsList += "--allow-model-download"
    }
    if ($Force) {
        $argsList += "--force"
    }
    if (-not $Apply) {
        $argsList += "--dry-run"
        Write-Output "Dry-run mode. Pass -Apply to write curated docs/knowledge shards to LightRAG."
    }
    & $python @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
