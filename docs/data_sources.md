# Источники данных

Этот документ фиксирует policy для выбора market data sources в research MVP. Он не
обещает live trading и не заменяет юридическую проверку terms of service, лимитов API и
условий бирж.

## Crypto через CCXT

Для старта проекта используется **Bybit** как `primary стартовая crypto exchange`.
Если на раннем этапе нужен один venue для live CCXT smoke или ручной проверки ingestion,
выбираем Bybit.

Активный crypto roadmap:

| Venue | Статус | Почему нужен | Ограничения |
| --- | --- | --- | --- |
| Bybit | primary стартовая crypto exchange | Первый venue для crypto OHLCV smoke и pairs research | Нужно соблюдать rate limits, category/symbol rules и terms of service |
| Binance | planned secondary exchange | Высокая ликвидность и полезный cross-venue baseline | Лимиты зависят от endpoint weights; live проверки остаются opt-in |
| OKX | planned secondary exchange | Альтернативный venue для cross-check и будущей устойчивости источников | Нужно учитывать правила instrument IDs и API limits |
| Deribit | planned derivatives exchange | Полезен для derivatives/options контекста и future volatility research | Не должен смешиваться со spot OHLCV без явного instrument contract |

Исключенные legacy venues не входят в активный roadmap проекта. Их не используем в
README, скриптах, examples и документации как рекомендуемые источники.

## Alpaca

Alpaca остается кандидатом для equities/paper-market-data сценариев, но не является
заменой crypto ingestion. Для equities нужны отдельные license, historical depth,
subscription и rate-limit проверки.

## Free/public datasets

Free datasets можно использовать для deterministic tests, examples и offline smoke.
Их нельзя автоматически считать production-quality market data: часто ограничены
history depth, survivorship bias, corporate actions, delayed data и условиями лицензии.

Для v1 research MVP действует **No paid data dependency**: acceptance, CI, scripted examples и
pre-commit должны проходить без платных market data subscriptions. Платные источники можно
рассматривать позже только как отдельный approved data-source task с явной проверкой
лицензии, стоимости, historical depth и rate limits.

## Почему live CCXT smoke остается opt-in

`live CCXT smoke` не входит в `pre-commit`, потому что он зависит от внешней сети,
доступности exchange API, rate limits, региональных ограничений, terms of service и
текущего состояния credentials. Pre-commit должен оставаться deterministic и быстрым.
Live checks запускаются вручную или отдельным readiness workflow, когда нужно проверить
реальную интеграцию с venue.

## Проверенные источники

- Bybit API docs: <https://bybit-exchange.github.io/docs/v5/market/kline>
- Bybit rate limits: <https://bybit-exchange.github.io/docs/v5/rate-limit>
- Binance market data endpoints: <https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints>
- Binance rate limits: <https://developers.binance.com/docs/binance-spot-api-docs/websocket-api/rate-limits>
- OKX API docs: <https://www.okx.com/docs-v5/en/>
- Alpaca Market Data API: <https://docs.alpaca.markets/us/docs/about-market-data-api>
