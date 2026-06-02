param(
    [string]$Query = "What is the rule for deferred do later work in this project?",
    [string[]]$Expect = @("technical_debt.md", "docs/knowledge"),
    [int]$QueryTimeoutSeconds = 240,
    [switch]$SkipQuery,
    [switch]$SkipDocker,
    [switch]$SkipViewerExport
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$seedScript = Join-Path $PSScriptRoot "seed_lightrag_curated.ps1"
$omniRouteScript = Join-Path $PSScriptRoot "check_omniroute.ps1"
$graphExportScript = Join-Path $PSScriptRoot "check_lightrag_graph_export.ps1"
$viewerExportScript = Join-Path $PSScriptRoot "export_lightrag_graph.ps1"
$queryScript = Join-Path $PSScriptRoot "query_lightrag_curated.ps1"
$docStatusPath = Join-Path $repoRoot "data\lightrag\kv_store_doc_status.json"
$knowledgeDir = Join-Path $repoRoot "docs\knowledge"

function Invoke-CheckedCommand {
    param(
        [string]$Description,
        [scriptblock]$Command
    )

    Write-Output "- $Description"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Output "Проверка свежести LightRAG memory..."

$seedOutput = & $seedScript 2>&1
$seedExit = $LASTEXITCODE
$seedOutput | ForEach-Object { Write-Output $_ }
if ($seedExit -ne 0) {
    exit $seedExit
}
$seedText = $seedOutput -join "`n"
if ($seedText -notmatch "Dry run: 0 changed document") {
    Write-Error "LightRAG memory не свежая: curated seed dry-run нашел измененные документы. Запустите .\scripts\rebuild_lightrag_curated.ps1, чтобы избежать duplicate docs."
}

if (-not (Test-Path -LiteralPath $docStatusPath)) {
    Write-Error "LightRAG doc_status не найден: $docStatusPath"
}

$expectedSources = Get-ChildItem -LiteralPath $knowledgeDir -Filter "*.md" -File |
    ForEach-Object { "docs/knowledge/$($_.Name)" } |
    Sort-Object
$docStatus = Get-Content -Raw -LiteralPath $docStatusPath | ConvertFrom-Json
$processedSources = @()
$failedCount = 0
foreach ($record in $docStatus.PSObject.Properties.Value) {
    if ($record.status -eq "failed") {
        $failedCount += 1
    }
    if ($record.status -ne "processed") {
        continue
    }
    $summary = [string]$record.content_summary
    $match = [regex]::Match($summary, '"source_id"\s*:\s*"([^"]+)"')
    if ($match.Success) {
        $processedSources += $match.Groups[1].Value
    }
}

if ($failedCount -ne 0) {
    Write-Error "LightRAG doc_status содержит failed records: $failedCount."
}
if ($processedSources.Count -ne $expectedSources.Count) {
    Write-Error "LightRAG memory содержит $($processedSources.Count) processed curated docs, ожидалось $($expectedSources.Count). Нужен clean rebuild из docs/knowledge/*.md."
}
$duplicateSources = $processedSources |
    Group-Object |
    Where-Object { $_.Count -gt 1 } |
    Select-Object -ExpandProperty Name
if ($duplicateSources) {
    Write-Error "LightRAG memory содержит duplicate source_id: $($duplicateSources -join ', '). Нужен clean rebuild."
}
$missingSources = $expectedSources | Where-Object { $_ -notin $processedSources }
if ($missingSources) {
    Write-Error "LightRAG memory не содержит curated source(s): $($missingSources -join ', ')."
}
Write-Output "- Curated doc_status fresh: $($processedSources.Count)/$($expectedSources.Count) source(s), duplicates 0, failed 0"

if (-not $SkipDocker) {
    Invoke-CheckedCommand `
        -Description "OmniRoute readiness и persistent doc_status" `
        -Command { & $omniRouteScript -SkipSmoke }
}
else {
    Write-Output "- Docker/OmniRoute readiness пропущен по флагу -SkipDocker"
}

Invoke-CheckedCommand `
    -Description "Экспорт графа LightRAG" `
    -Command { & $graphExportScript }

if (-not $SkipViewerExport) {
    Invoke-CheckedCommand `
        -Description "Обновление human-facing viewer export" `
        -Command { & $viewerExportScript }
}
else {
    Write-Output "- Human-facing viewer export пропущен по флагу -SkipViewerExport"
}

if (-not $SkipQuery) {
    Invoke-CheckedCommand `
        -Description "Контрольный query smoke" `
        -Command { & $queryScript -Query $Query -Expect $Expect -TimeoutSeconds $QueryTimeoutSeconds }
}
else {
    Write-Output "- Query smoke пропущен по флагу -SkipQuery"
}

Write-Output "Проверка свежести LightRAG memory прошла."
