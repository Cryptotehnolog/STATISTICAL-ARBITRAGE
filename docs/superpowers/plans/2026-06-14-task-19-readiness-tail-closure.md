# Task 19 Readiness Tail Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Task 19 documentation readiness honest by closing stale plan checkboxes and moving real deferred work into a controlled checklist.

**Architecture:** Treat documentation readiness as a checkpoint, not a writing sprint. The task plan remains the execution truth; `docs/technical_debt.md` remains the detailed backlog; a human-readable deferred checklist gives the user and Codex a quick control surface.

**Tech Stack:** Markdown, Kiro task plan, existing ApeRAG curated knowledge workflow, existing PowerShell checks.

---

### Task 1: Audit Tail Inventory

**Files:**
- Read: `.kiro/specs/quant-research-architecture/tasks.md`
- Read: `docs/technical_debt.md`
- Read: `docs/knowledge/technical_debt_backlog.md`
- Read: `docs/knowledge/future_ideas.md`

- [x] **Step 1: Inspect open parent tasks**

Run:

```powershell
Select-String -Path '.kiro\specs\quant-research-architecture\tasks.md' -Pattern '^- \[[ xX]\]|Task 15|Task 18|Task 19'
```

Expected: find stale open parents before Task 19.

- [x] **Step 2: Inspect deferred work**

Run:

```powershell
rg -n "Status: open|mostly closed|Follow-up|Task 15\.3|full experiment runner" docs .kiro\specs\quant-research-architecture\tasks.md
```

Expected: identify which work is truly blocked versus stale.

### Task 2: Align Task Plan With Implemented Baseline

**Files:**
- Modify: `.kiro/specs/quant-research-architecture/tasks.md`

- [x] **Step 1: Mark Task 15 parent complete for the MVP CLI/scripted workflow baseline**

Keep an explicit note that full arbitrary experiment automation remains deferred.

- [x] **Step 2: Mark Task 15.3 complete for the current safe CLI execution boundary**

Document that `run-pipeline` is intentionally narrow and artifact-gated.

- [x] **Step 3: Mark Task 18 parent complete**

All 18.1-18.4 subtasks are already implemented and guarded.

### Task 3: Add Human-Readable Deferred Work Checklist

**Files:**
- Create: `docs/deferred_work_checklist.md`
- Modify: `docs/technical_debt.md`
- Modify: `docs/knowledge/technical_debt_backlog.md`

- [x] **Step 1: Add a Russian checklist grouped by readiness**

Include:

```markdown
## Можно закрывать до Task 19
## Делать только после нового boundary
## Не делать без отдельного решения
```

- [x] **Step 2: Add TD for full arbitrary experiment runner**

The current safe pipeline exists, but broad full-run remains premature until mature stage inputs and factual artifacts exist end to end.

- [x] **Step 3: Update curated backlog memory**

Keep ApeRAG aligned with the backlog policy.

### Task 4: Verify And Commit

**Files:**
- Verify: `.kiro/specs/quant-research-architecture/tasks.md`
- Verify: `docs/deferred_work_checklist.md`
- Verify: `docs/technical_debt.md`
- Verify: `docs/knowledge/technical_debt_backlog.md`

- [x] **Step 1: Run focused checks**

Run:

```powershell
uv run pytest tests/unit/test_github_actions_ci.py tests/unit/test_check_cli_pipeline.py -q
```

- [x] **Step 2: Run pre-commit baseline if focused checks pass**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\pre_commit_check.ps1
```

- [x] **Step 3: Seed ApeRAG if curated knowledge changed**

Run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\seed_aperag_curated.ps1 -Force
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_aperag_memory_fresh.ps1 -IndexWaitTimeoutSeconds 300
```

- [ ] **Step 4: Commit**

Run:

```powershell
git add <changed-readiness-files>
git commit -m "Align Task 19 readiness backlog"
```
