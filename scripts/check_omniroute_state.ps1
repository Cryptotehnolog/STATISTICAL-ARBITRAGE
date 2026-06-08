param(
    [string]$ContainerName = "omniroute",
    [string[]]$ForbiddenConnectionIds = @(
        "fc868537-fd75-42c6-9b8f-051196f1ed3c",
        "02402742-c217-4167-907f-ec358477ba80",
        "2fda8409-2145-4f72-8df5-f130843589a8",
        "a6868470-cc9c-4d3d-b4e2-14b933b87aae"
    ),
    [switch]$RequireMyAiCombo
)

$ErrorActionPreference = "Stop"

Write-Output "Проверка OmniRoute state: $ContainerName"

$containerId = docker ps -a --filter "name=^/$ContainerName$" --format "{{.ID}}"
if (-not $containerId) {
    Write-Error "Docker container '$ContainerName' не найден."
}

$tempDir = Join-Path $env:TEMP "omniroute-state-check-$([guid]::NewGuid())"
try {
    New-Item -ItemType Directory -Force -Path $tempDir | Out-Null

    $tempDb = Join-Path $tempDir "storage.sqlite"
    docker cp "${ContainerName}:/app/data/storage.sqlite" $tempDb | Out-Null
    if (-not (Test-Path $tempDb)) {
        Write-Error "Не удалось скопировать OmniRoute storage.sqlite для проверки."
    }
    foreach ($sqliteSidecar in @("storage.sqlite-wal", "storage.sqlite-shm")) {
        $target = Join-Path $tempDir $sqliteSidecar
        docker cp "${ContainerName}:/app/data/$sqliteSidecar" $target 2>$null
    }

    $env:OMNIROUTE_STATE_DB = $tempDb
    $env:OMNIROUTE_FORBIDDEN_IDS = ($ForbiddenConnectionIds -join ",")
    $env:OMNIROUTE_REQUIRE_MY_AI = if ($RequireMyAiCombo) { "1" } else { "0" }

    $pythonScript = @'
import json
import os
import sqlite3
import sys

db_path = os.environ["OMNIROUTE_STATE_DB"]
forbidden_ids = [
    item.strip()
    for item in os.environ.get("OMNIROUTE_FORBIDDEN_IDS", "").split(",")
    if item.strip()
]
require_my_ai = os.environ.get("OMNIROUTE_REQUIRE_MY_AI") == "1"

connection_patterns = forbidden_ids

def like_any(column):
    return " or ".join([f"{column} like ?" for _ in connection_patterns])

def params():
    return [f"%{item}%" for item in connection_patterns]

checks = {}
with sqlite3.connect(db_path) as con:
    cur = con.cursor()
    existing_tables = {
        row[0]
        for row in cur.execute("select name from sqlite_master where type = 'table'")
    }
    required_tables = {
        "combos",
        "session_account_affinity",
        "key_value",
        "usage_history",
        "call_logs",
        "semantic_cache",
    }
    missing_tables = sorted(required_tables - existing_tables)
    if missing_tables:
        print(
            "OmniRoute SQLite schema еще не готова или скопирована без WAL: "
            + ", ".join(missing_tables),
            file=sys.stderr,
        )
        sys.exit(1)

    checks["combos_with_forbidden_connection_ids"] = cur.execute(
        f"""
        select count(*)
        from combos
        where {like_any("data")}
        """,
        params(),
    ).fetchone()[0]

    checks["my_ai_combo_present"] = cur.execute(
        "select count(*) from combos where lower(name) = 'my-ai'"
    ).fetchone()[0]

    checks["session_account_affinity_forbidden_ids"] = cur.execute(
        f"""
        select count(*)
        from session_account_affinity
        where {like_any("connection_id")}
        """,
        params(),
    ).fetchone()[0]

    checks["key_value_forbidden_ids"] = cur.execute(
        f"""
        select count(*)
        from key_value
        where {like_any("key")}
           or {like_any("value")}
        """,
        params() + params(),
    ).fetchone()[0]

    checks["usage_history_forbidden_ids"] = cur.execute(
        f"""
        select count(*)
        from usage_history
        where {like_any("connection_id")}
        """,
        params(),
    ).fetchone()[0]

    checks["call_logs_forbidden_ids"] = cur.execute(
        f"""
        select count(*)
        from call_logs
        where {like_any("path")}
        """,
        params(),
    ).fetchone()[0]

    checks["semantic_cache_forbidden_ids"] = cur.execute(
        f"""
        select count(*)
        from semantic_cache
        where {like_any("model")}
           or {like_any("response")}
        """,
        params() + params(),
    ).fetchone()[0]

my_ai_combo_present = checks.pop("my_ai_combo_present")
print(json.dumps({**checks, "my_ai_combo_present": my_ai_combo_present}, ensure_ascii=False, indent=2))
failed = {key: value for key, value in checks.items() if value}
if my_ai_combo_present < 1 and require_my_ai:
    failed["my_ai_combo_missing"] = 1
if failed:
    print("Найдены stale OmniRoute записи:", json.dumps(failed, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)
'@

    $pythonScript | python -
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Проверка OmniRoute state завершилась с ошибкой."
    }
    Write-Output "OmniRoute state OK: stale Kiro/my-ai привязки не найдены."
}
finally {
    if (Test-Path $tempDir) {
        Remove-Item -LiteralPath $tempDir -Force -Recurse
    }
    Remove-Item Env:\OMNIROUTE_STATE_DB -ErrorAction SilentlyContinue
    Remove-Item Env:\OMNIROUTE_FORBIDDEN_IDS -ErrorAction SilentlyContinue
    Remove-Item Env:\OMNIROUTE_REQUIRE_MY_AI -ErrorAction SilentlyContinue
}
