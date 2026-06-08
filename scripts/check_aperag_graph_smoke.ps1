param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$CollectionTitle = "stat-arb-graph-smoke",
    [ValidateSet("omniroute", "free_deepseek")]
    [string]$CompletionBackend = "omniroute",
    [string]$CompletionProvider = "",
    [string]$CompletionModel = "",
    [int]$TimeoutSeconds = 180,
    [switch]$KeepCollection
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot $EnvFile
$runtimeDir = Join-Path $repoRoot "data\aperag"
$smokeFile = Join-Path $runtimeDir "aperag_graph_smoke.md"

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Error "ApeRAG env file не найден: $envPath"
}
if (-not (Test-Path -LiteralPath $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

Get-Content -LiteralPath $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)\s*$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

$headers = @{
    Authorization = "Bearer $env:APERAG_API_KEY"
    "Content-Type" = "application/json"
}

function Invoke-ApeRagJson {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $uri = "$env:APERAG_API_BASE_URL$Path"
    if ($null -eq $Body) {
        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -TimeoutSec 60
    }

    $json = $Body | ConvertTo-Json -Depth 30
    return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -Body $json -TimeoutSec 60
}

function Get-SmokeCollection {
    $collections = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections?page=1&page_size=100"
    return $collections.items | Where-Object { $_.title -eq $CollectionTitle } | Select-Object -First 1
}

Write-Output "Проверка ApeRAG graph smoke..."

if (-not $CompletionProvider) {
    $CompletionProvider = if ($CompletionBackend -eq "free_deepseek") {
        "stat-arb-free-deepseek"
    }
    else {
        "stat-arb-omniroute"
    }
}
if (-not $CompletionModel) {
    $CompletionModel = if ($CompletionBackend -eq "free_deepseek") {
        "deepseek-chat"
    }
    else {
        "my-ai"
    }
}

.\scripts\configure_aperag.ps1 `
    -EnvFile $EnvFile `
    -CompletionBackend $CompletionBackend `
    -CompletionProvider $CompletionProvider `
    -CompletionModel $CompletionModel | Write-Output

$existing = Get-SmokeCollection
if ($existing) {
    Invoke-ApeRagJson -Method "DELETE" -Path "/api/v1/collections/$($existing.id)" | Out-Null
    Write-Output "Удалена старая smoke collection: $($existing.id)"
    Start-Sleep -Seconds 2
}

$config = @{
    source = "system"
    enable_vector = $true
    enable_fulltext = $true
    enable_knowledge_graph = $true
    enable_summary = $false
    enable_vision = $false
    language = "en-US"
    knowledge_graph_config = @{
        entity_types = @("organization", "person", "event", "technology", "category")
    }
    embedding = @{
        model = "sentence-transformers/all-MiniLM-L6-v2"
        model_service_provider = "stat-arb-local-embeddings"
        custom_llm_provider = "openai"
        timeout = 60
    }
    completion = @{
        model = $CompletionModel
        model_service_provider = $CompletionProvider
        custom_llm_provider = "openai"
        temperature = 0.1
        max_tokens = 2048
        timeout = 120
    }
}

$collection = Invoke-ApeRagJson -Method "POST" -Path "/api/v1/collections" -Body @{
    title = $CollectionTitle
    description = "Small bounded graph extraction smoke for Statistical Arbitrage memory migration."
    type = "document"
    config = $config
}

@"
# ApeRAG Graph Smoke

The Statistical Arbitrage project uses ApeRAG as the project memory backend.
The Memory Agent writes curated project decisions into ApeRAG.
OmniRoute provides OpenAI-compatible completion for graph extraction.
The local embedding endpoint provides all-MiniLM-L6-v2 vectors for vector search.
The Data Agent must read validated OHLCV datasets before research workflows continue.
"@ | Set-Content -LiteralPath $smokeFile -Encoding UTF8

$upload = curl.exe -sS `
    -H "Authorization: Bearer $env:APERAG_API_KEY" `
    -F "files=@$smokeFile" `
    "$env:APERAG_API_BASE_URL/api/v1/collections/$($collection.id)/documents"
if ($LASTEXITCODE -ne 0) {
    Write-Error "ApeRAG graph smoke upload failed."
}
$uploaded = $upload | ConvertFrom-Json
$documentIds = @($uploaded.items | ForEach-Object { $_.id })
if (-not $documentIds) {
    Write-Error "ApeRAG graph smoke не получил document id: $upload"
}

Invoke-ApeRagJson -Method "POST" -Path "/api/v1/collections/$($collection.id)/documents/confirm" -Body @{
    document_ids = $documentIds
} | Out-Null

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
do {
    Start-Sleep -Seconds 5
    $docs = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/documents?page=1&page_size=10"
    $doc = $docs.items | Select-Object -First 1
    Write-Output "Status: document=$($doc.status), vector=$($doc.vector_index_status), fulltext=$($doc.fulltext_index_status), graph=$($doc.graph_index_status)"
    if ($doc.status -eq "FAILED" -or $doc.graph_index_status -eq "FAILED") {
        Write-Error "ApeRAG graph smoke failed."
    }
    if ($doc.status -eq "COMPLETE" -and $doc.graph_index_status -eq "ACTIVE") {
        break
    }
} while ((Get-Date) -lt $deadline)

if (-not ($doc.status -eq "COMPLETE" -and $doc.graph_index_status -eq "ACTIVE")) {
    Write-Error "ApeRAG graph smoke timeout after $TimeoutSeconds seconds."
}

$labels = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/graphs/labels"
$graph = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/graphs?max_nodes=200&max_depth=2"

$nodeCount = @($graph.nodes).Count
$edgeCount = @($graph.edges).Count
if ($nodeCount -eq 0 -or $edgeCount -eq 0) {
    Write-Error "ApeRAG graph smoke вернул пустой graph: nodes=$nodeCount, edges=$edgeCount"
}

if (-not $KeepCollection) {
    Invoke-ApeRagJson -Method "DELETE" -Path "/api/v1/collections/$($collection.id)" | Out-Null
    Write-Output "Smoke collection удалена: $($collection.id)"
}

Write-Output "ApeRAG graph smoke OK: labels=$(@($labels.labels).Count), nodes=$nodeCount, edges=$edgeCount"
