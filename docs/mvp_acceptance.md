# MVP acceptance

Этот документ фиксирует, как проект проверяет Task 22 перед user acceptance testing.

## Что проверяет локальный acceptance

Команда:

```powershell
.\scripts\check_mvp_acceptance.ps1
```

создает deterministic local registry fixture и проверяет критерии Task 22:

- 50 synthetic crypto assets с `15m` timeframe и минимум 180 дней history metadata;
- минимум 10 tested pairs;
- минимум 5 completed experiments;
- backtest report artifact для каждого completed experiment;
- registry evidence для data quality, statistical testing, backtesting, cost attribution,
  critic review, reporting и reproducibility;
- non-functional boundaries: uv/Python core, Docker-supported ApeRAG/Infisical/OmniRoute,
  no paid data dependency, secret guards и runtime/resource documentation;
- known limitations: research-only v1, deferred paper/live trading, future Rust acceleration.

Команда пишет machine-readable отчет в:

```text
data/mvp_acceptance/mvp_acceptance_report.json
```

`data/` не коммитится: это runtime artifact, а не source file.

## Что эта проверка не делает

Acceptance не ходит в live exchanges и не требует secrets. Это осознанное решение:
обычные checks не должны зависеть от сети, rate limits, региональных блокировок, текущего
состояния Docker или внешних LLM/API providers.

Live-scale проверка Bybit/Binance/OKX/Deribit остается отдельным opt-in readiness run. Она
нужна перед реальной research сессией, но не должна ломать pre-commit и CI.

## Почему это честно

Task 22 должен доказать, что MVP architecture выдерживает требуемую форму: данные,
качество, пары, experiments, reports, registry, memory boundary и ограничения. Локальный
deterministic fixture делает это воспроизводимо. Реальные market data добавляют внешний
риск, но не должны менять contract проекта.
