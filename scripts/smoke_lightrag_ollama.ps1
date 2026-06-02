param(
    [string]$Model = "qwen2.5:3b",
    [double]$TimeoutSeconds = 600,
    [switch]$KeepData
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$modelsDir = "E:\AI_Models\Ollama"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Expected virtualenv Python at $python. Run 'uv sync' first."
}

$env:OLLAMA_MODELS = $modelsDir

Push-Location $repoRoot
try {
    $argsList = @(
        "-m",
        "stat_arb.scripts.smoke_lightrag_ollama",
        "--model",
        $Model,
        "--timeout",
        $TimeoutSeconds
    )
    if ($KeepData) {
        $argsList += "--keep-data"
    }
    & $python @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
