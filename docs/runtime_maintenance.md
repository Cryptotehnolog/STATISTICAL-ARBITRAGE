# Runtime maintenance

Этот документ описывает ручную чистку локальных временных файлов. Это не часть
обычного pre-commit и не фоновая автоматизация.

## Когда запускать

Используйте чистку только вручную:

- после длинной серии локальных тестов, если накопились cache/coverage artifacts;
- перед большим checkpoint-аудитом, если нужно убрать шум из рабочего дерева;
- перед оценкой размера проекта, когда важно отделить код от regenerable runtime мусора.

Не запускайте чистку автоматически перед каждым commit. Некоторые runtime files полезны
для диагностики, а persistent storage нельзя удалять вместе с cache.

## Что делает команда

Сначала всегда запускайте dry-run:

```powershell
.\scripts\clean_runtime_artifacts.ps1
```

Dry-run только показывает, что будет удалено. Он не меняет файлы.

Удаление выполняется только явным ручным флагом:

```powershell
.\scripts\clean_runtime_artifacts.ps1 -Apply
```

Скрипт удаляет только regenerable artifacts внутри репозитория:

- `.ruff_cache`;
- `.pytest_cache`;
- `.coverage*`;
- `coverage.xml`;
- `htmlcov`;
- `src/**/__pycache__`;
- `tests/**/__pycache__`;
- `data/test_tmp`;
- `data/test_registry.db`;
- старые state files viewer-сервера, если связанный процесс уже не запущен.

## Что нельзя удалять этой командой

Эта команда не должна трогать persistent state:

- `data/aperag` и любые данные active memory backend;
- registry databases с реальными experiment/result records;
- Parquet datasets, если они нужны для воспроизводимости;
- `infra/infisical/.env`;
- Docker volumes;
- Infisical keys, encryption config и backup artifacts;
- OmniRoute, FreeDeepseek или FreeQwen runtime state.

Если нужно удалить persistent state, это должна быть отдельная задача с backup/restore
планом, а не обычная runtime cleanup.

## Как проверять после чистки

После `-Apply` достаточно запустить быстрый baseline:

```powershell
.\scripts\check.ps1
```

Перед commit используйте полный локальный guard:

```powershell
.\scripts\pre_commit_check.ps1
```
