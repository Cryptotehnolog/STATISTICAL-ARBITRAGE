param(
    [switch]$Build,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$composeFile = Join-Path $repoRoot "infra\free_qwen\docker-compose.yml"
$runtimeDir = Join-Path $repoRoot "data\free_qwen"
$sessionDir = Join-Path $runtimeDir "session"
$tokensFile = Join-Path $sessionDir "tokens.json"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Error "Docker не найден. Установите/запустите Docker Desktop."
}
if (-not (Test-Path -LiteralPath $composeFile)) {
    Write-Error "FreeQwenApi compose file не найден: $composeFile"
}
foreach ($dir in @($runtimeDir, $sessionDir, (Join-Path $runtimeDir "logs"), (Join-Path $runtimeDir "uploads"))) {
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
}

if ($Stop) {
    docker compose -f $composeFile down
    Write-Output "FreeQwenApi container остановлен."
    exit 0
}

if (-not (Test-Path -LiteralPath $tokensFile)) {
    Write-Error "Qwen session tokens не найдены: $tokensFile. Ожидаемый путь: data\free_qwen\session\tokens.json. Сначала создайте Qwen Chat session через upstream FreeQwenApi npm run auth -- --add и сохраните session в data\free_qwen\session."
}

$args = @("compose", "-f", $composeFile, "up", "-d")
if ($Build) {
    $args += "--build"
}

docker @args
Write-Output "FreeQwenApi container запрошен: stat-arb-free-qwen, http://127.0.0.1:3264/api"
