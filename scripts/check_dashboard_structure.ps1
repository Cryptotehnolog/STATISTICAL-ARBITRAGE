$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$dashboardDir = Join-Path $repoRoot "src\stat_arb\dashboard"
$requiredFiles = @(
    "app.py",
    "data.py",
    "__init__.py"
)

Write-Output "Проверка dashboard structure..."

foreach ($file in $requiredFiles) {
    $path = Join-Path $dashboardDir $file
    if (-not (Test-Path -LiteralPath $path)) {
        Write-Error "Dashboard file не найден: $path"
    }
}

$forbiddenPatterns = @(
    "st\.button\s*\(",
    "st\.form_submit_button\s*\(",
    "MemoryAgentService",
    "ApeRAGMemoryClient",
    "insert\s+into",
    "\.add\s*\(",
    "\.delete\s*\(",
    "\.commit\s*\("
)

foreach ($file in Get-ChildItem -LiteralPath $dashboardDir -Filter "*.py") {
    $text = Get-Content -LiteralPath $file.FullName -Raw
    foreach ($pattern in $forbiddenPatterns) {
        if ($text -match $pattern) {
            Write-Error "Dashboard read-only guard failed: $($file.Name) matches '$pattern'"
        }
    }
}

Push-Location $repoRoot
try {
    uv run python -m compileall -q src\stat_arb\dashboard
}
finally {
    Pop-Location
}

Write-Output "Проверка dashboard structure прошла."
