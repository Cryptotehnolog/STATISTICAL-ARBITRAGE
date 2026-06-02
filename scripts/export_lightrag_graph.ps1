param(
    [string]$GraphMl = "",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    Write-Error "Ожидался Python из virtualenv: $python. Сначала выполните 'uv sync'."
}

Push-Location $repoRoot
try {
    $argsList = @(
        "-m",
        "stat_arb.scripts.export_lightrag_graph"
    )
    if ($GraphMl) {
        $argsList += @("--graphml", $GraphMl)
    }
    if ($OutputDir) {
        $argsList += @("--output-dir", $OutputDir)
    }
    & $python @argsList
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
