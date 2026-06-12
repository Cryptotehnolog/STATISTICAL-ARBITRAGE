param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$KnowledgeDir = "docs\knowledge",
    [string]$ManifestFile = "data\aperag\curated_seed_manifest.json",
    [int]$IndexWaitTimeoutSeconds = 120,
    [int]$IndexPollSeconds = 10,
    [switch]$IncludeGraphSmoke,
    [switch]$RequireCuratedGraph
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$knowledgePath = Join-Path $repoRoot $KnowledgeDir
$manifestPath = Join-Path $repoRoot $ManifestFile

Write-Output "Проверка свежести ApeRAG memory..."

if (-not (Test-Path -LiteralPath $manifestPath)) {
    Write-Error "Seed manifest не найден: $manifestPath. Запустите .\scripts\seed_aperag_curated.ps1."
}
if (-not (Test-Path -LiteralPath $knowledgePath)) {
    Write-Error "Knowledge directory не найден: $knowledgePath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$files = Get-ChildItem -LiteralPath $knowledgePath -Filter "*.md" | Sort-Object Name
$manifestDocs = @($manifest.documents)

if ($files.Count -ne $manifestDocs.Count) {
    Write-Error "Количество knowledge shards изменилось: files=$($files.Count), manifest=$($manifestDocs.Count)"
}

foreach ($file in $files) {
    $relativePath = ($file.FullName.Substring($repoRoot.Length + 1) -replace "\\", "/")
    $entry = $manifestDocs | Where-Object { $_.relative_path -eq $relativePath } | Select-Object -First 1
    if (-not $entry) {
        Write-Error "Shard отсутствует в seed manifest: $relativePath"
    }
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
    if ($hash -ne $entry.sha256) {
        Write-Error "Shard изменился после seed: $relativePath"
    }
}

.\scripts\check_aperag.ps1 -IncludeGraphSmoke:$IncludeGraphSmoke | Write-Output

$indexDeadline = (Get-Date).AddSeconds($IndexWaitTimeoutSeconds)
while ($true) {
    try {
        .\scripts\check_aperag_knowledge.ps1 -EnvFile $EnvFile | Write-Output
        break
    }
    catch {
        if ((Get-Date) -ge $indexDeadline) {
            throw
        }
        Write-Output "ApeRAG indexes еще строятся; повтор через $IndexPollSeconds сек."
        Start-Sleep -Seconds $IndexPollSeconds
    }
}

if ($RequireCuratedGraph) {
    $envPath = Join-Path $repoRoot $EnvFile
    Get-Content -LiteralPath $envPath | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }

    $headers = @{ Authorization = "Bearer $env:APERAG_API_KEY" }
    $collections = Invoke-RestMethod -Uri "$env:APERAG_API_BASE_URL/api/v1/collections?page=1&page_size=100" -Headers $headers -TimeoutSec 60
    $collection = $collections.items | Where-Object { $_.title -eq $manifest.collection_title } | Select-Object -First 1
    if (-not $collection) {
        Write-Error "ApeRAG collection не найдена: $($manifest.collection_title)"
    }
    $docs = Invoke-RestMethod -Uri "$env:APERAG_API_BASE_URL/api/v1/collections/$($collection.id)/documents?page=1&page_size=100" -Headers $headers -TimeoutSec 60
    $badGraph = @($docs.items | Where-Object { $_.graph_index_status -ne "ACTIVE" })
    if ($badGraph.Count -gt 0) {
        $badGraph | Select-Object name,status,graph_index_status | Format-Table -AutoSize
        Write-Error "Curated ApeRAG graph не готов: $($badGraph.Count) document(s)."
    }
    $labels = Invoke-RestMethod -Uri "$env:APERAG_API_BASE_URL/api/v1/collections/$($collection.id)/graphs/labels" -Headers $headers -TimeoutSec 60
    $graph = Invoke-RestMethod -Uri "$env:APERAG_API_BASE_URL/api/v1/collections/$($collection.id)/graphs?max_nodes=1000&max_depth=3" -Headers $headers -TimeoutSec 120
    if (@($labels.labels).Count -eq 0 -or @($graph.nodes).Count -eq 0 -or @($graph.edges).Count -eq 0) {
        Write-Error "Curated ApeRAG graph пустой."
    }
    Write-Output "Curated ApeRAG graph OK: labels=$(@($labels.labels).Count), nodes=$(@($graph.nodes).Count), edges=$(@($graph.edges).Count)"
}

Write-Output "ApeRAG memory fresh OK: shards=$($files.Count), collection=$($manifest.collection_id)"
