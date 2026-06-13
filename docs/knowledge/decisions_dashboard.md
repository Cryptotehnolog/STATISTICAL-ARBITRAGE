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
