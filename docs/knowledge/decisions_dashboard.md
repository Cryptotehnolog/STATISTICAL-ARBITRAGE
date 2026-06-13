# Dashboard Decisions

## DEC-0087: Start the dashboard as a read-only registry shell

The first dashboard layer is intentionally read-only. It may inspect registry-backed
experiments, hypotheses, reports, and pipeline state, but it must not run stages,
approve experiments, write to ApeRAG, or mutate registry rows.

Rationale:

- Task 16 should not bypass the Coordinator, registry, or Memory Agent policy boundaries.
- Human-facing monitoring can be useful before the full workflow runner exists.
- Mutation controls, approvals, and memory search need their own audited boundaries.

Implementation guard:

- `scripts/check_dashboard_structure.ps1` verifies the Streamlit scaffold exists and
  blocks mutation-oriented patterns inside `src/stat_arb/dashboard`.
- `scripts/pre_commit_check.ps1` runs the dashboard guard before commits.

## DEC-0088: Keep the local dashboard available at localhost:8501

Human operators should be able to open the dashboard by entering
`http://localhost:8501` in a browser, without remembering the Streamlit command or
the project working directory.

Implementation:

- `.streamlit/config.toml` disables Streamlit onboarding/usage prompts and pins the
  local dashboard to `localhost:8501`.
- `scripts/start_dashboard.ps1` starts the dashboard in the project root, hidden in
  the background, and is idempotent when the server is already running.
- `scripts/install_dashboard_autostart.ps1` first tries a Windows Scheduled Task and
  falls back to a user Startup shortcut when Task Scheduler registration is denied.

Boundary:

- Autostart is local operator convenience only. It must not run experiments, write
  to registry, write to ApeRAG, or bypass Coordinator/Memory Agent policy.

## DEC-0089: Keep the experiment list as a read-only registry projection

Task 16.2 adds the first useful dashboard page: an experiment list with lifecycle
status, hypothesis pair, current agent, final decision, and latest statistical,
backtest, and Critic result fields. The page supports status, asset, created-date
filters, and metric sorting.

The list is intentionally a read-only projection over the SQLite registry. It must
not start stages, approve experiments, write ApeRAG memory, mutate Coordinator tasks,
or modify lifecycle state. Interactive execution and approval controls belong to later
explicit boundaries, not to the monitoring list view.

## DEC-0090: Complete Task 16 as a safe read-only monitoring dashboard

Task 16 adds concrete dashboard pages for hypotheses, statistical tests, backtests,
report artifacts, coordinator errors, memory readiness, and the manual approval queue.
The dashboard remains an operational monitoring surface, not an execution surface.

Visualization policy:

- Show tables and metric strips directly from registry rows.
- Show cost attribution from factual backtest cost fields.
- Do not invent equity, drawdown, z-score, or trade series from aggregate metrics.
  Full charts require matching factual `backtest_series` sidecars.

Memory policy:

- The dashboard may show a read-only memory search shell and readiness context.
- It must not instantiate ApeRAG clients or MemoryAgentService directly.
- Real memory search belongs behind a dedicated read-only Memory Agent boundary.

Approval policy:

- The dashboard may display experiments eligible for human review.
- It must not mutate experiment state with ad-hoc Streamlit buttons.
- Approve/reject decisions must go through an audited Coordinator transition API
  with explicit reason capture and registry persistence.
