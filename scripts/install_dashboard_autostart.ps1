param(
    [string]$TaskName = "StatArbDashboard"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$launcherPath = Join-Path $PSScriptRoot "start_dashboard.ps1"
$isWindowsVariable = Get-Variable IsWindows -ErrorAction SilentlyContinue
$runningOnWindows = if ($isWindowsVariable) { [bool]$IsWindows } else { $true }

function New-DashboardStartupShortcut {
    $startupDir = [Environment]::GetFolderPath("Startup")
    $shortcutPath = Join-Path $startupDir "$TaskName.lnk"
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = "powershell.exe"
    $shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$launcherPath`""
    $shortcut.WorkingDirectory = $repoRoot
    $shortcut.WindowStyle = 7
    $shortcut.Description = "Запускает Statistical Arbitrage dashboard на http://localhost:8501"
    $shortcut.Save()

    Write-Output "Dashboard autostart установлен через Startup shortcut: $shortcutPath"
    Write-Output "URL: http://localhost:8501"
}

if (-not $runningOnWindows) {
    Write-Output "Autostart installer предназначен для Windows. На Linux используйте systemd/user service."
    exit 0
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$launcherPath`"" `
    -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Description "Запускает Statistical Arbitrage dashboard на http://localhost:8501" `
        -Force `
        -ErrorAction Stop | Out-Null

    Write-Output "Dashboard autostart установлен через Scheduled Task: $TaskName"
    Write-Output "URL: http://localhost:8501"
}
catch {
    Write-Output "Scheduled Task недоступен: $($_.Exception.Message)"
    New-DashboardStartupShortcut
}
