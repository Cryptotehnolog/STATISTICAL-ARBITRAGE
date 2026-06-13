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
