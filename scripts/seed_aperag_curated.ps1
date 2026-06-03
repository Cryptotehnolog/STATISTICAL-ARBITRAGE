param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$KnowledgeDir = "docs\knowledge",
    [string]$CollectionTitle = "stat-arb-project-knowledge",
    [string]$CollectionDescription = "Curated project knowledge shards for Statistical Arbitrage agents.",
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

.\scripts\configure_aperag.ps1 -EnvFile $EnvFile | Write-Output

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
        model = "my-ai"
        model_service_provider = "stat-arb-omniroute"
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
if ($existing.items.Count -gt 0 -and -not $Force) {
    Write-Output "Документы уже есть: $($existing.items.Count). Для полной пересборки используйте -Force."
}
else {
    foreach ($file in $files) {
        $response = curl.exe -sS `
            -H "Authorization: Bearer $env:APERAG_API_KEY" `
            -F "files=@$($file.FullName)" `
            "$env:APERAG_API_BASE_URL/api/v1/collections/$($collection.id)/documents"
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Upload failed: $($file.Name)"
        }
        $uploaded = $response | ConvertFrom-Json
        $documentIds = @($uploaded.items | ForEach-Object { $_.id })
        if (-not $documentIds) {
            Write-Error "ApeRAG не вернул document id для $($file.Name): $response"
        }
        Invoke-ApeRagJson -Method "POST" -Path "/api/v1/collections/$($collection.id)/documents/confirm" -Body @{
            document_ids = $documentIds
        } | Out-Null
        Write-Output "Uploaded: $($file.Name)"
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

Write-Output "ApeRAG curated seed завершен: collection=$($collection.id), shards=$($files.Count)"
