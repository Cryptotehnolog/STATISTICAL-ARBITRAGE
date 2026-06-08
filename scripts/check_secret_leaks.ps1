param(
    [switch]$IncludeGitHistory,
    [switch]$CheckDockerEnvNames
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

$excludedPathParts = @(
    ".git",
    ".venv",
    "data",
    "htmlcov",
    ".pytest_cache",
    ".ruff_cache",
    "scripts\init_infisical_env.ps1",
    "scripts\check_secret_leaks.ps1"
)

$sensitiveFilePatterns = @(
    "(^|/|\\)\.env$",
    "(^|/|\\)\.env\.(local|production|prod|staging|dev)$",
    "(^|/|\\)credentials\.json$",
    "(^|/|\\)deepseek-auth\.json$",
    "(^|/|\\)auth\.json$",
    "(^|/|\\)\.chrome-profile-deepseek(/|\\)",
    "(^|/|\\)\.chrome-for-testing-profile-deepseek(/|\\)",
    "^secrets(/|\\)",
    "\.pem$",
    "\.key$",
    "\.crt$",
    "\.p12$",
    "\.pfx$"
)

$secretPatterns = @(
    @{ Name = "AWS access key"; Pattern = "AKIA[0-9A-Z]{16}" },
    @{ Name = "OpenAI-like API key"; Pattern = "sk-[A-Za-z0-9_-]{20,}" },
    @{ Name = "GitHub token"; Pattern = "gh[pousr]_[A-Za-z0-9_]{20,}" },
    @{ Name = "Slack token"; Pattern = "xox[baprs]-[A-Za-z0-9-]{10,}" },
    @{ Name = "Private key block"; Pattern = "-----BEGIN (RSA |OPENSSH |EC |DSA |)PRIVATE KEY-----" },
    @{ Name = "Infisical bootstrap key"; Pattern = "^(ENCRYPTION_KEY|AUTH_SECRET|INFISICAL_POSTGRES_PASSWORD)=" },
    @{ Name = "DeepSeek web token"; Pattern = "^(DEEPSEEK_TOKEN|DEEPSEEK_COOKIE|DEEPSEEK_HIF_DLIQ|DEEPSEEK_HIF_LEIM)=" },
    @{ Name = "Runtime secret assignment"; Pattern = "^[A-Za-z0-9_]*(API_KEY|API_SECRET|CLIENT_SECRET|TOKEN|PASSWORD|PRIVATE_KEY)=[^#\s].+" }
)

$placeholderPattern = "(your_|replace-with|stored_in_infisical|example|placeholder|localhost|changeme|=\.\.\.$|\$\(|^$)"

function Test-IsExcluded {
    param([string]$RelativePath)

    $normalized = $RelativePath -replace "/", "\"
    foreach ($part in $excludedPathParts) {
        if ($normalized.StartsWith($part, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Test-IsPlaceholderLine {
    param([string]$Line)

    if ($Line -match "^\s*#") {
        return $true
    }
    return $Line -match $placeholderPattern
}

function Add-Violation {
    param(
        [System.Collections.ArrayList]$Violations,
        [string]$Scope,
        [string]$Path,
        [int]$Line,
        [string]$Rule
    )

    [void]$Violations.Add([pscustomobject]@{
        Scope = $Scope
        File = $Path
        Line = $Line
        Rule = $Rule
    })
}

function Get-TrackedFiles {
    git -C $repoRoot ls-files |
        Where-Object { $_ -and -not (Test-IsExcluded -RelativePath $_) }
}

function Test-TrackedSensitiveFiles {
    param([System.Collections.ArrayList]$Violations)

    foreach ($file in Get-TrackedFiles) {
        $normalized = $file -replace "\\", "/"
        foreach ($pattern in $sensitiveFilePatterns) {
            if ($normalized -match $pattern) {
                Add-Violation `
                    -Violations $Violations `
                    -Scope "tracked-file" `
                    -Path $file `
                    -Line 0 `
                    -Rule "Sensitive file is tracked"
            }
        }
    }
}

function Test-FileContent {
    param([System.Collections.ArrayList]$Violations)

    foreach ($file in Get-TrackedFiles) {
        $fullPath = Join-Path $repoRoot $file
        if (-not (Test-Path -LiteralPath $fullPath)) {
            continue
        }

        $lineNumber = 0
        foreach ($line in Get-Content -LiteralPath $fullPath -ErrorAction Stop) {
            $lineNumber += 1
            if (Test-IsPlaceholderLine -Line $line) {
                continue
            }

            foreach ($rule in $secretPatterns) {
                if ($line -match $rule.Pattern) {
                    Add-Violation `
                        -Violations $Violations `
                        -Scope "tracked-content" `
                        -Path $file `
                        -Line $lineNumber `
                        -Rule $rule.Name
                }
            }
        }
    }
}

function Test-WorkingTreeEnvFiles {
    param([System.Collections.ArrayList]$Violations)

    $envFiles = @(".env", "infra/infisical/.env", "data/free_deepseek/deepseek-auth.json")
    foreach ($file in $envFiles) {
        $fullPath = Join-Path $repoRoot $file
        if (-not (Test-Path -LiteralPath $fullPath)) {
            continue
        }

        $trackedMatch = git -C $repoRoot ls-files -- $file
        if ($trackedMatch) {
            Add-Violation `
                -Violations $Violations `
                -Scope "working-tree" `
                -Path $file `
                -Line 0 `
                -Rule "Runtime env file is tracked"
        }

        git -C $repoRoot check-ignore -q $file
        if ($LASTEXITCODE -ne 0) {
            Add-Violation `
                -Violations $Violations `
                -Scope "working-tree" `
                -Path $file `
                -Line 0 `
                -Rule "Runtime env file is not ignored"
        }
    }
}

function Test-GitHistory {
    param([System.Collections.ArrayList]$Violations)

    $history = git -C $repoRoot log --all -p -- . ":(exclude)uv.lock"
    $lineNumber = 0
    foreach ($line in $history) {
        $lineNumber += 1
        if (Test-IsPlaceholderLine -Line $line) {
            continue
        }

        foreach ($rule in $secretPatterns) {
            if ($line -match $rule.Pattern) {
                Add-Violation `
                    -Violations $Violations `
                    -Scope "git-history" `
                    -Path "git log --all -p" `
                    -Line $lineNumber `
                    -Rule $rule.Name
            }
        }
    }
}

function Show-DockerEnvNames {
    $containers = @(
        "stat-arb-infisical-backend",
        "stat-arb-infisical-db",
        "stat-arb-infisical-redis",
        "omniroute"
    )

    $rows = @()
    foreach ($container in $containers) {
        $exists = docker ps -a --filter "name=^/$container$" --format "{{.Names}}"
        if (-not $exists) {
            $rows += [pscustomobject]@{
                Container = $container
                Exists = $false
                SensitiveEnvNames = ""
            }
            continue
        }

        $sensitiveNames = docker inspect $container --format "{{range .Config.Env}}{{println .}}{{end}}" |
            ForEach-Object { ($_ -split "=", 2)[0] } |
            Where-Object { $_ -match "(SECRET|TOKEN|PASSWORD|KEY|DB_CONNECTION_URI)" } |
            Sort-Object

        $rows += [pscustomobject]@{
            Container = $container
            Exists = $true
            SensitiveEnvNames = ($sensitiveNames -join ", ")
        }
    }

    Write-Output "Docker env audit показывает только имена переменных, значения не выводятся:"
    $rows | Format-Table -Wrap
}

Push-Location $repoRoot
try {
    $violations = [System.Collections.ArrayList]::new()

    Test-TrackedSensitiveFiles -Violations $violations
    Test-FileContent -Violations $violations
    Test-WorkingTreeEnvFiles -Violations $violations

    if ($IncludeGitHistory) {
        Write-Output "Проверка Git history на типовые секреты..."
        Test-GitHistory -Violations $violations
    }

    if ($CheckDockerEnvNames) {
        Show-DockerEnvNames
    }

    if ($violations.Count -gt 0) {
        Write-Output "Найдены возможные secret leaks. Значения не выводятся:"
        $violations | Sort-Object Scope, File, Line, Rule | Format-Table -AutoSize
        Write-Error "Проверка secret leaks не прошла."
    }

    Write-Output "Проверка secret leaks прошла."
}
finally {
    Pop-Location
}
