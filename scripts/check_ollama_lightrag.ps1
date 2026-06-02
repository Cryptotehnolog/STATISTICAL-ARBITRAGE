param(
    [string]$Model = "qwen2.5:3b",
    [string]$OllamaExe = "C:\Users\Victor\AppData\Local\Programs\Ollama\ollama.exe",
    [string]$ModelsDir = "E:\AI_Models\Ollama",
    [string]$BaseUrl = "http://localhost:11434"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $OllamaExe)) {
    Write-Error "Ollama executable not found at $OllamaExe"
}

New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null
$env:OLLAMA_MODELS = $ModelsDir

Write-Output "Ollama executable: $OllamaExe"
Write-Output "Ollama models dir: $env:OLLAMA_MODELS"
Write-Output "Expected model: $Model"

$models = & $OllamaExe list
Write-Output $models

if ($models -notmatch [regex]::Escape($Model)) {
    Write-Error "Model $Model is not installed. Run: & `"$OllamaExe`" pull $Model"
}

$body = @{
    model = $Model
    prompt = "Return exactly OK."
    stream = $false
    options = @{
        temperature = 0
        num_predict = 8
    }
} | ConvertTo-Json -Depth 5

$response = Invoke-RestMethod `
    -Uri "$BaseUrl/api/generate" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body `
    -TimeoutSec 120

Write-Output "Ollama response: $($response.response)"
Write-Output "Ollama LightRAG check passed."
