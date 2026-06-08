param(
    [switch]$Build,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repoRoot "infra\free_deepseek\docker-compose.yml"
$runtimeDir = Join-Path $repoRoot "data\free_deepseek"
$authFile = Join-Path $runtimeDir "deepseek-auth.json"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker не найден. Установите/запустите Docker Desktop."
}
if (-not (Test-Path -LiteralPath $composeFile)) {
    Write-Error "FreeDeepseekAPI compose file не найден: $composeFile"
}
if (-not (Test-Path -LiteralPath $runtimeDir)) {
    New-Item -ItemType Directory -Path $runtimeDir | Out-Null
}

if ($Stop) {
    docker compose -f $composeFile down
    Write-Output "FreeDeepseekAPI container остановлен."
    exit 0
}

if (-not (Test-Path -LiteralPath $authFile)) {
    Write-Error "DeepSeek auth file не найден: $authFile. Сначала создайте DeepSeek Web session через upstream FreeDeepseekAPI npm run auth и положите deepseek-auth.json в data\free_deepseek."
}

$args = @("compose", "-f", $composeFile, "up", "-d")
if ($Build) {
    $args += "--build"
}

docker @args
Write-Output "FreeDeepseekAPI container запрошен: stat-arb-free-deepseek, http://127.0.0.1:9655"
