# Данные и качество

Data layer отвечает за то, чтобы Statistical Testing Agent и Backtest Agent не получали
мусорные OHLCV bars.

## OHLCV contract

- Timestamps нормализуются в UTC.
- Duplicate timestamps запрещены.
- Missing bars фиксируются в DataQualityReport.
- Термин `duplicate timestamps` означает повторяющиеся timestamps внутри одного OHLCV
  ряда.
- Термин `missing bars` используется для пропущенных ожидаемых OHLCV интервалов.
- Impossible candles, нулевые цены и abnormal volume проверяются до использования данных.
- Resampling deterministic: open, high, low, close, volume и timestamp label считаются
  воспроизводимо.
- Pair alignment обязателен перед statistical testing и backtesting.

## One-bar diagnostic

Одна свеча не считается полноценным качественным dataset. Если в потоке есть только одна
свеча, система может создать diagnostic DataQualityReport, но он должен быть
`is_valid=false`, `passed=false`, `invalid_reason="insufficient_data"` и иметь issue
`insufficient_data`. Это сохраняет audit trace, но не дает агентам принять одну свечу за
валидные данные.

Иными словами: одна свеча дает только diagnostic след, а не подтверждение качества данных.

## Storage

- Raw/validated data хранится в Parquet.
- Provenance, validation status и report IDs пишутся в Structured Registry.
- ApeRAG получает только concise policy-safe summaries и registry references.

## Data source policy

CCXT является текущим crypto source adapter. Live exchange smoke tests должны быть opt-in,
потому что network, rate limits и exchange behavior нестабильны. Yahoo Finance не
рекомендуется для intraday research.

Стартовый crypto venue для live CCXT smoke и ручных проверок — Bybit. Binance, OKX и
Deribit остаются active planned venues для cross-venue validation и будущего расширения.
Исключенные legacy venues не входят в активный roadmap проекта.

Подробная оценка limitations, licensing, rate limits и historical depth вынесена в
`docs/data_sources.md`.
