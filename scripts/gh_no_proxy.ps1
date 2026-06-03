param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$GhArgs
)

$ErrorActionPreference = "Stop"

$proxyEnvNames = @(
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY"
)

$previousValues = @{}
foreach ($name in $proxyEnvNames) {
    $previousValues[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    Remove-Item "Env:\$name" -ErrorAction SilentlyContinue
}

try {
    & gh @GhArgs
    exit $LASTEXITCODE
}
finally {
    foreach ($name in $proxyEnvNames) {
        if ($previousValues[$name]) {
            [Environment]::SetEnvironmentVariable($name, $previousValues[$name], "Process")
        }
    }
}
