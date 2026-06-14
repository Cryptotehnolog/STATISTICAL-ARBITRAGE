param(
    [Parameter(Mandatory = $true)]
    [double]$RamBudgetGb,

    [Parameter(Mandatory = $true)]
    [double]$DiskBudgetGb,

    [Parameter(Mandatory = $true)]
    [double]$WarnUsageRatio,

    [string]$DiskName = "D"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

if ($RamBudgetGb -le 0) {
    throw "RamBudgetGb должен быть больше 0."
}
if ($DiskBudgetGb -le 0) {
    throw "DiskBudgetGb должен быть больше 0."
}
if ($WarnUsageRatio -le 0 -or $WarnUsageRatio -gt 1) {
    throw "WarnUsageRatio должен быть в диапазоне (0, 1]."
}

$os = Get-CimInstance Win32_OperatingSystem
$totalMemoryKb = [double]$os.TotalVisibleMemorySize
$freeMemoryKb = [double]$os.FreePhysicalMemory
$ramUsedGb = (($totalMemoryKb - $freeMemoryKb) / 1MB)

$drive = Get-PSDrive -Name $DiskName -ErrorAction Stop
$diskUsedGb = (($drive.Used) / 1GB)

$env:STAT_ARB_RAM_USED_GB = [string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0}", $ramUsedGb)
$env:STAT_ARB_RAM_BUDGET_GB = [string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0}", $RamBudgetGb)
$env:STAT_ARB_DISK_USED_GB = [string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0}", $diskUsedGb)
$env:STAT_ARB_DISK_BUDGET_GB = [string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0}", $DiskBudgetGb)
$env:STAT_ARB_WARN_USAGE_RATIO = [string]::Format([Globalization.CultureInfo]::InvariantCulture, "{0}", $WarnUsageRatio)

Push-Location $repoRoot
try {
    $python = @'
from __future__ import annotations

import os
from datetime import UTC, datetime

from stat_arb.agents.failure_handling import (
    ResourceBudgetPolicy,
    ResourceUsageSnapshot,
    evaluate_resource_budget,
)

snapshot = ResourceUsageSnapshot(
    observed_at=datetime.now(UTC),
    ram_used_gb=float(os.environ["STAT_ARB_RAM_USED_GB"]),
    ram_budget_gb=float(os.environ["STAT_ARB_RAM_BUDGET_GB"]),
    disk_used_gb=float(os.environ["STAT_ARB_DISK_USED_GB"]),
    disk_budget_gb=float(os.environ["STAT_ARB_DISK_BUDGET_GB"]),
)
events = evaluate_resource_budget(
    snapshot,
    policy=ResourceBudgetPolicy(
        warn_usage_ratio=float(os.environ["STAT_ARB_WARN_USAGE_RATIO"]),
    ),
)

if not events:
    print("Runtime resource budget OK.")
else:
    for event in events:
        print(f"{event.severity}: {event.summary}")
    raise SystemExit(2)
'@
    $python | uv run python -
}
finally {
    Pop-Location
}
