# Юридические предупреждения

Этот проект является `research tool`; он is not financial advice и не является investment
advice, brokerage service, execution system или asset-management service.

## Research-only граница

- Проект не является live trading системой.
- Проект не должен автономно отправлять ордера, управлять капиталом или менять позиции.
- Любой переход к paper trading, demo trading или live trading требует отдельного
  архитектурного решения, risk policy, secrets policy, audit trail и human approval.
- Любые результаты statistical testing, backtesting, critic review или dashboard views
  являются исследовательскими артефактами, а не рекомендацией купить, продать или держать
  актив.

## Финансовые риски и market risk

- Market risk остается на человеке, который принимает решение.
- Есть no guarantee of profitability.
- Past performance не гарантирует future results.
- Backtest может быть ошибочным из-за data quality, survivorship bias, lookahead bias,
  regime changes, costs, slippage, funding, borrow rates, liquidity и operational failures.
- Любые assumptions о costs, liquidity, latency, fills и capital allocation должны быть
  проверены отдельно перед использованием вне research.

## Human approval

- Human approval обязателен перед любым действием, которое может повлиять на реальные
  деньги, биржевые аккаунты, credentials, orders, positions или external services.
- Agent decisions не являются окончательными инвестиционными решениями.
- Coordinator approval означает только research workflow status, а не разрешение торговать
  реальным капиталом.

## Secrets, exchanges и data usage

- API keys, tokens и credentials должны храниться через Infisical или другой утвержденный
  secrets manager, а не в Git, docs, logs или memory.
- Нужно соблюдать terms of service, API usage policies, rate limits, licensing,
  redistribution rules и regional restrictions каждого data provider или exchange.
- Live CCXT smoke checks остаются opt-in и не входят в pre-commit, потому что зависят от
  внешних сервисов, credentials, rate limits и условий провайдера.

## Audit trail

- Structured Registry является source of truth для numeric metrics, experiment state,
  reproducibility metadata, dataset IDs и report artifacts.
- ApeRAG хранит project knowledge и policy-safe summaries, но не заменяет registry,
  юридическую проверку или human review.
- Logs, reports и memory summaries не должны содержать secrets, raw credentials или
  sensitive account data.
