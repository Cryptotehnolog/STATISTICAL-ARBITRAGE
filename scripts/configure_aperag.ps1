param(
    [string]$EnvFile = "data\aperag\.env",
    [string]$EmbeddingProvider = "stat-arb-local-embeddings",
    [string]$CompletionProvider = "stat-arb-omniroute",
    [string]$EmbeddingModel = "sentence-transformers/all-MiniLM-L6-v2",
    [string]$CompletionModel = "my-ai"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot $EnvFile

if (-not (Test-Path -LiteralPath $envPath)) {
    Write-Error "ApeRAG env file не найден: $envPath"
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
        return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -TimeoutSec 30
    }

    $json = $Body | ConvertTo-Json -Depth 20
    return Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -Body $json -TimeoutSec 30
}

try {
    $embeddingHealth = Invoke-RestMethod -Uri "http://127.0.0.1:18101/health" -TimeoutSec 5
    if ($embeddingHealth.status -ne "healthy") {
        Write-Error "Local embedding server не healthy."
    }
}
catch {
    Write-Error "Local embedding server недоступен. Запустите .\scripts\start_aperag_embedding_server.ps1"
}

$providers = (Invoke-ApeRagJson -Method "GET" -Path "/api/v1/llm_configuration").providers

if (-not ($providers | Where-Object { $_.name -eq $EmbeddingProvider })) {
    Invoke-ApeRagJson -Method "POST" -Path "/api/v1/llm_providers" -Body @{
        name = $EmbeddingProvider
        label = "Stat Arb Local Embeddings"
        completion_dialect = "openai"
        embedding_dialect = "openai"
        rerank_dialect = "jina_ai"
        allow_custom_base_url = $true
        base_url = "http://host.docker.internal:18101/v1"
        api_key = "local-not-secret"
        status = "enable"
    } | Out-Null
    Write-Output "Создан ApeRAG provider: $EmbeddingProvider"
}

if (-not ($providers | Where-Object { $_.name -eq $CompletionProvider })) {
    Invoke-ApeRagJson -Method "POST" -Path "/api/v1/llm_providers" -Body @{
        name = $CompletionProvider
        label = "Stat Arb OmniRoute"
        completion_dialect = "openai"
        embedding_dialect = "openai"
        rerank_dialect = "jina_ai"
        allow_custom_base_url = $true
        base_url = "http://host.docker.internal:20128/v1"
        api_key = "local-not-secret"
        status = "enable"
    } | Out-Null
    Write-Output "Создан ApeRAG provider: $CompletionProvider"
}

$models = (Invoke-ApeRagJson -Method "GET" -Path "/api/v1/llm_provider_models").items

if (-not ($models | Where-Object { $_.provider_name -eq $EmbeddingProvider -and $_.api -eq "embedding" -and $_.model -eq $EmbeddingModel })) {
    Invoke-ApeRagJson -Method "POST" -Path "/api/v1/llm_providers/$EmbeddingProvider/models" -Body @{
        provider_name = $EmbeddingProvider
        api = "embedding"
        model = $EmbeddingModel
        custom_llm_provider = "openai"
        context_window = 512
        max_input_tokens = 512
        tags = @("stat-arb", "local", "embedding")
    } | Out-Null
    Write-Output "Создан ApeRAG embedding model: $EmbeddingModel"
}

if (-not ($models | Where-Object { $_.provider_name -eq $CompletionProvider -and $_.api -eq "completion" -and $_.model -eq $CompletionModel })) {
    Invoke-ApeRagJson -Method "POST" -Path "/api/v1/llm_providers/$CompletionProvider/models" -Body @{
        provider_name = $CompletionProvider
        api = "completion"
        model = $CompletionModel
        custom_llm_provider = "openai"
        context_window = 200000
        max_input_tokens = 180000
        max_output_tokens = 8192
        tags = @("stat-arb", "omniroute", "completion")
    } | Out-Null
    Write-Output "Создан ApeRAG completion model: $CompletionModel"
}

Write-Output "ApeRAG providers/models настроены."
