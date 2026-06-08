param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$KnowledgeDir = "docs\knowledge",
    [string]$CollectionTitle = "stat-arb-project-knowledge",
    [string]$CollectionDescription = "Curated project knowledge shards for Statistical Arbitrage agents.",
    [ValidateSet("omniroute", "free_deepseek", "free_qwen")]
    [string]$CompletionBackend = "omniroute",
    [string]$CompletionProvider = "",
    [string]$CompletionModel = "",
    [switch]$EnableGraph,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot $EnvFile
$knowledgePath = Join-Path $repoRoot $KnowledgeDir
$runtimeDir = Join-Path $repoRoot "data\aperag"
$manifestFile = Join-Path $runtimeDir "curated_seed_manifest.json"

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Error "ApeRAG env file не найден: $envPath"
}
if (-not (Test-Path -LiteralPath $knowledgePath)) {
    Write-Error "Knowledge directory не найден: $knowledgePath"
}
if (-not (Test-Path -LiteralPath $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

Get-Content -LiteralPath $envPath | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)\s*$') {
        [Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
    }
}

if (-not $env:APERAG_API_BASE_URL -or -not $env:APERAG_API_KEY) {
    Write-Error "APERAG_API_BASE_URL или APERAG_API_KEY не заданы в $envPath"
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

function Get-Collection {
    $collections = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections?page=1&page_size=100"
    return $collections.items | Where-Object { $_.title -eq $CollectionTitle } | Select-Object -First 1
}

function Upload-CuratedShard {
    param(
        [object]$Collection,
        [System.IO.FileInfo]$File
    )

    $response = curl.exe -sS `
        -H "Authorization: Bearer $env:APERAG_API_KEY" `
        -F "files=@$($File.FullName)" `
        "$env:APERAG_API_BASE_URL/api/v1/collections/$($Collection.id)/documents"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Upload failed: $($File.Name)"
    }
    $uploaded = $response | ConvertFrom-Json
    $documentIds = @($uploaded.items | ForEach-Object { $_.id })
    if (-not $documentIds) {
        Write-Error "ApeRAG не вернул document id для $($File.Name): $response"
    }
    Invoke-ApeRagJson -Method "POST" -Path "/api/v1/collections/$($Collection.id)/documents/confirm" -Body @{
        document_ids = $documentIds
    } | Out-Null
    Write-Output "Uploaded: $($File.Name)"
}

if (-not $CompletionProvider) {
    $CompletionProvider = switch ($CompletionBackend) {
        "free_deepseek" { "stat-arb-free-deepseek" }
        "free_qwen" { "stat-arb-free-qwen" }
        default { "stat-arb-omniroute" }
    }
}
if (-not $CompletionModel) {
    $CompletionModel = switch ($CompletionBackend) {
        "free_deepseek" { "deepseek-chat" }
        "free_qwen" { "qwen3.7-plus" }
        default { "my-ai" }
    }
}

.\scripts\configure_aperag.ps1 `
    -EnvFile $EnvFile `
    -CompletionBackend $CompletionBackend `
    -CompletionProvider $CompletionProvider `
    -CompletionModel $CompletionModel | Write-Output

if ($Force) {
    .\scripts\recalculate_aperag_quota.ps1 -EnvFile $EnvFile | Write-Output
}

$collection = Get-Collection
if ($collection -and $Force) {
    Invoke-ApeRagJson -Method "DELETE" -Path "/api/v1/collections/$($collection.id)" | Out-Null
    Write-Output "Удалена старая ApeRAG collection: $($collection.id)"
    Start-Sleep -Seconds 2
    $collection = $null
}

$config = @{
    source = "system"
    enable_vector = $true
    enable_fulltext = $true
    enable_knowledge_graph = [bool]$EnableGraph
    enable_summary = $false
    enable_vision = $false
    language = "en-US"
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

if (-not $collection) {
    $collection = Invoke-ApeRagJson -Method "POST" -Path "/api/v1/collections" -Body @{
        title = $CollectionTitle
        description = $CollectionDescription
        type = "document"
        config = $config
    }
    Write-Output "Создана ApeRAG collection: $($collection.id)"
}
else {
    $collection = Invoke-ApeRagJson -Method "PUT" -Path "/api/v1/collections/$($collection.id)" -Body @{
        title = $CollectionTitle
        description = $CollectionDescription
        config = $config
    }
    Write-Output "Обновлена ApeRAG collection: $($collection.id)"
}

$files = Get-ChildItem -LiteralPath $knowledgePath -Filter "*.md" | Sort-Object Name
if (-not $files) {
    Write-Error "В $knowledgePath нет curated markdown shards."
}

$existing = Invoke-ApeRagJson -Method "GET" -Path "/api/v1/collections/$($collection.id)/documents?page=1&page_size=100"
$existingDocumentsByName = @{}
foreach ($document in @($existing.items)) {
    if ($document.name) {
        $existingDocumentsByName[$document.name] = $document
    }
}

$previousHashesByName = @{}
if (Test-Path -LiteralPath $manifestFile) {
    $previousManifest = Get-Content -LiteralPath $manifestFile -Raw | ConvertFrom-Json
    foreach ($document in @($previousManifest.documents)) {
        if ($document.name -and $document.sha256) {
            $previousHashesByName[$document.name] = $document.sha256
        }
    }
}

$filesToUpload = @()
foreach ($file in $files) {
    $currentHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
    $previousHash = $previousHashesByName[$file.Name]
    if (-not $existingDocumentsByName.ContainsKey($file.Name) -or $previousHash -ne $currentHash) {
        $filesToUpload += $file
    }
}

if ($existing.items.Count -gt 0 -and -not $Force -and $filesToUpload.Count -eq 0) {
    Write-Output "Документы уже актуальны: $($existing.items.Count). Для полной пересборки используйте -Force."
}
else {
    if (-not $Force) {
        Write-Output "Измененные или отсутствующие curated shards: $($filesToUpload.Count)"
    }
    $uploadSet = if ($Force -or $existing.items.Count -eq 0) { $files } else { $filesToUpload }
    foreach ($file in $uploadSet) {
        if (-not $Force -and $existingDocumentsByName.ContainsKey($file.Name)) {
            $oldDocument = $existingDocumentsByName[$file.Name]
            Invoke-ApeRagJson -Method "DELETE" -Path "/api/v1/collections/$($collection.id)/documents/$($oldDocument.id)" | Out-Null
            Write-Output "Deleted stale shard: $($file.Name)"
        }
        Upload-CuratedShard -Collection $collection -File $file
    }
}

$manifest = [ordered]@{
    collection_id = $collection.id
    collection_title = $CollectionTitle
    seeded_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    knowledge_dir = $KnowledgeDir
    enable_graph = [bool]$EnableGraph
    documents = @(
        $files | ForEach-Object {
            [ordered]@{
                name = $_.Name
                relative_path = ($_.FullName.Substring($repoRoot.Length + 1) -replace "\\", "/")
                sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash.ToLowerInvariant()
                length = $_.Length
            }
        }
    )
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestFile -Encoding UTF8

if ($EnableGraph) {
    .\scripts\enable_aperag_curated_graph.ps1 `
        -EnvFile $EnvFile `
        -CollectionTitle $CollectionTitle `
        -CompletionBackend $CompletionBackend `
        -CompletionProvider $CompletionProvider `
        -CompletionModel $CompletionModel | Write-Output
}

Write-Output "ApeRAG curated seed завершен: collection=$($collection.id), shards=$($files.Count)"
