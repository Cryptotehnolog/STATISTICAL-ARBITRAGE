# Агенты и права доступа

Этот документ фиксирует фактические agent boundaries. Главный принцип: агент может писать
в registry или memory только через свой service/policy boundary. Ни один agent-facing
module не пишет напрямую в ApeRAG.

## Общие правила

- Structured Registry хранит точные structured records и numeric metrics.
- Memory Agent policy фильтрует записи перед ApeRAG.
- Raw logs, secrets, raw prompts, large datasets и metric-heavy payloads не пишутся в
  ApeRAG.
- Dashboard остается read-only и не мутирует registry напрямую.

## Роли

| Agent | Ответственность | Registry | Memory |
| --- | --- | --- | --- |
| Data Agent | OHLCV ingestion, quality validation, alignment, provenance | dataset IDs, DataQualityReport, provenance | policy-safe failure summaries |
| Hypothesis Agent | rule-based pair generation, novelty checks, links/retests | hypothesis records, novelty status | rationale summaries через Memory Agent policy |
| Statistical Testing Agent | cointegration, ADF, hedge ratio, half-life, z-score, diagnostics | statistical results | lessons через Memory Agent policy |
| Backtest Agent | PnL, costs, metrics, baseline, reproducibility, sidecars | backtest metrics, artifacts, config hashes | summary conclusions через Memory Agent policy |
| Critic Agent | lookahead, overfitting, weak assumptions, testing sufficiency, cost realism | review status and objections | risk summaries через Memory Agent policy |
| Report Agent | human-readable reports and artifact links | report records and artifact links | summaries через Memory Agent policy |
| Coordinator Agent | lifecycle, queue, resource policy, final decision, permissions | task state, lifecycle, decisions | final decision summaries через Memory Agent policy |
| Memory Agent | policy-controlled read/write boundary | references registry IDs | ApeRAG write/query adapter |

## Запрещенные обходы

- Агент не пишет напрямую в ApeRAG.
- Агент не обходит Structured Registry для exact metrics.
- Dashboard не делает ad-hoc registry mutations.
- CLI stage executor не создает reports без factual artifacts, если stage требует графики.
