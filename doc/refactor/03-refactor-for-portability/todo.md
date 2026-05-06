# 03 — Refactor for Portability — TODO

## Core Rules

- Work **one item at a time**. Do not start the next item until the current one is fully implemented, tested, and documented.
- Each task has up to three checkboxes: **implementation**, **testing** (whenever a script is touched or a workflow has an exercisable surface), **documentation** (whenever the SKILL body or wizard step semantics change).
- All work happens on a dedicated feature branch (see "Setup" below). Never commit on `main`.
- The PR is created only after every task is done **and** the local quality gate has passed.

## Briefing

Read these documents in full **before touching anything**. Do not start the tasks below until you have done so.

- [ ] Read [`plan.md`](plan.md) — this cluster's behavioural rewrites: audit checklist, per-skill rewrite table, `marshal.json` template, marshall-steward wizard rewrite, phase-skills rewrite, bootstrap exception
- [ ] Read [`../00-cleanup-precondition/plan.md`](../00-cleanup-precondition/plan.md) — the precondition cluster you are layered on top of (do not redo prose work it already covers)
- [ ] Read [`../01-design-platform-api/plan.md`](../01-design-platform-api/plan.md) — every `platform-runtime` operation you will be calling from skills must match its contract
- [ ] Read [`../principles.md`](../principles.md) — boundary rules in particular ("would this work identically on both targets?")
- [ ] Read [`../README.md`](../README.md) — refactor overview, terminology, dependency graph
- [ ] Confirm to yourself you have understood the boundary between behavioural and prose changes, every operation's per-target behaviour, and the executor resolution per target
- [ ] If **any** part is unclear or contradictory, **stop and ask the user** before continuing — do not guess

## Setup

- [ ] Switch to a feature branch: `git switch -c feature/refactor-03-portability`
- [ ] Confirm clusters 00, 01, and 02 have been merged to `main` and pulled locally

## Tasks

### 1. `marshal.json` template — `runtime.target` field
- [ ] Implementation: extend `phase-1-init`'s template scaffolding to include `runtime.target` defaulting to `claude`. `project initial-setup` already accepts `--target` (cluster 01) — confirm it writes the field.
- [ ] Testing: integration test confirms a fresh-init plan has `runtime.target: claude` (or `opencode` when `--target opencode` was passed)

### 2. `phase-1-init` — call `session capture` at start
- [ ] Implementation: add `session capture` invocation as the first step of the phase
- [ ] Testing: integration test on Claude confirms `session_id` lands in `status.json` via `manage-status`; on OpenCode confirms the no-op return value is handled gracefully and the phase proceeds

### 3. `phase-5-execute` — replace `<usage>` parsing with `metrics capture`
- [ ] Implementation: remove `<usage>` tag parsing; add `session capture` at start; replace token-extraction with `platform-runtime metrics capture --phase 5-execute`
- [ ] Testing: integration tests on both targets

### 4. `phase-6-finalize` — same treatment
- [ ] Implementation: add `session capture`; replace direct `session_id = Claude UUID` assumption with `manage-status` read; use `metrics capture --phase 6-finalize`
- [ ] Testing: integration tests on both targets

### 5. `plan-retrospective` — replace transcript analysis
- [ ] Implementation: add `session capture`; replace transcript walking with `metrics capture --phase retrospective`; for permission-prompt analysis use `permission analyze --checks suspicious`; produce target-agnostic report
- [ ] Testing: integration tests on both targets; OpenCode-side asserts no transcript-walking code runs

### 6. `marshall-steward` wizard rewrite
- [ ] Implementation: rewrite the wizard steps per cluster 03 "marshall-steward Wizard Rewrite" table — Steps 1, 3, 4, 5, 13. Step 1 / 3 use bootstrap-direct invocation; Steps 4 onwards use the executor.
- [ ] Testing: end-to-end fresh-init walks both targets; verify settings/hook outputs match the target

### 7. `tools-permission-doctor` — delegate to `permission analyze`
- [ ] Implementation: replace direct settings reads with `platform-runtime permission analyze --checks <checks>`; remove Claude-specific anti-pattern lists from the skill body (now lives in the runtime)
- [ ] Testing: existing doctor tests migrated; output TOON shape unchanged

### 8. `tools-permission-fix` — delegate to `permission fix`
- [ ] Implementation: replace direct settings writes with `platform-runtime permission fix --operation <op>`. All three executor operations (`ensure-executor`, `cleanup-scripts`, `migrate-executor`) implemented on both targets per the per-target shape table in cluster 03
- [ ] Testing: per-operation tests on both targets including the OpenCode permission shape assertions

### 9. `workflow-permission-web` — delegate to `permission web-*`
- [ ] Implementation: replace `WebFetch(...)` string parsing with `permission web-analyze` / `permission web-apply` calls
- [ ] Testing: per-target tests covering analyze + apply (add and remove)

### 10. `tools-script-executor` — target-aware generator
- [ ] Implementation: extend the executor generator to read `runtime.target` from `marshal.json` and emit the matching resolver template (Claude-cache resolver or OpenCode-skill-roots resolver — see cluster 01 "Executor Resolution Per Target"). Notation `{bundle}:{skill}:{script}` unchanged.
- [ ] Testing: per-target unit tests for the resolver tables; integration test that the generated executor resolves a sample notation correctly on each target

### 11. `tools-file-ops` and `manage-worktree` — `marshal.json` `worktree.path`
- [ ] Implementation: replace hardcoded `.claude/worktrees/{plan_id}/` with `marshal.json` `worktree.path` prefix (default `.claude/worktrees/` for Claude, `.opencode/worktrees/` for OpenCode). Both skills consult the same source.
- [ ] Testing: per-target tests confirming worktree creation under the expected path

### 12. `tools-input-validation` — target-specific session_id validation
- [ ] Implementation: branch validation rule on `runtime.target`. Claude validates UUID-shape token; OpenCode validates whatever shape the upstream session-id format takes (or accepts opaque strings if no documented shape exists)
- [ ] Testing: validation tests for both targets

### 13. `tools-fix-intellij-diagnostics` (command) — `health-check`
- [ ] Implementation: replace direct `mcp__ide__getDiagnostics` invocation with `platform-runtime health-check --checks mcp-diagnostics`
- [ ] Testing: command runs on Claude (real MCP); on OpenCode the no-op response surfaces as a documented user-facing message

### 14. `bootstrap_plugin.py` — multi-platform path resolution
- [ ] Implementation: extend `bootstrap_plugin.py` to walk the same target-aware root list documented in cluster 01 "Bootstrap Invocation". Convert matched location to absolute path. Default target = claude when no marshal.json exists.
- [ ] Testing: per-target path-resolution tests including the OpenCode 7-root walk

### 15. Final audit pass
- [ ] Implementation: grep `marketplace/bundles/*/skills/*/SKILL.md` for any remaining behavioural Claude-specific reference (writes, reads, hook installation outside `platform-runtime` call sites). Each remaining occurrence must be a `platform-runtime` call site or a `references/{topic}.md` pointer.
- [ ] Testing: `./pw verify` passes on all 10 bundles

## Quality Gate

Run **once**, after every task above is complete. Do not run between tasks — the gate is a single pre-ship checkpoint, not a per-task check.

- [ ] Run the quality gate: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "quality-gate"` (Bash timeout ≥ 600000 ms). Inspect TOON.
- [ ] Run full verify: `python3 .plan/execute-script.py plan-marshall:build-python:python_build run --command-args "verify"` (Bash timeout ≥ 600000 ms).
- [ ] Both `status: success` before "Ship".

## Ship

Use `PLAN_ID=refactor-03-portability` in the commands below. Capture the PR number into `PR=<n>` after `ci pr create`.

- [ ] Commit all changes (conventional commits)
- [ ] Push the feature branch:
      `git push -u origin feature/refactor-03-portability`
- [ ] Allocate a body file:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr prepare-body --plan-id refactor-03-portability`
      (write PR body to the returned path)
- [ ] Create the PR:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr create --title "refactor(skills): replace Claude-specific behaviour with platform-runtime calls" --plan-id refactor-03-portability --base main`
- [ ] Wait 5 minutes for review automation:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr wait-for-comments --pr-number $PR --timeout 300`
- [ ] Fetch unresolved comments and reviews:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr comments --pr-number $PR --unresolved-only`
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr reviews  --pr-number $PR`
- [ ] For each unresolved comment (use `thread_id` from `ci pr comments` output):
      - **Real issue + sensible fix** → apply, commit, push; reply to the inline thread:
        `... pr prepare-comment --plan-id refactor-03-portability --for thread-reply --slot reply-<n>` (write text), then
        `... pr thread-reply --pr-number $PR --thread-id <THREAD_ID> --plan-id refactor-03-portability --slot reply-<n>`,
        then `... pr resolve-thread --thread-id <THREAD_ID>` once the fix has landed.
        For PR-level (non-inline) comments use `pr prepare-comment --for reply` + `pr reply --pr-number $PR ...` instead.
      - **Wrong / out of scope** → ask the user before skipping.
- [ ] After comment handling, **wait for the user to review** the PR.

## Close

- [ ] User has approved the PR
- [ ] Merge with squash + delete branch:
      `python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci pr merge --pr-number $PR --strategy squash --delete-branch`
- [ ] `git switch main && git pull origin main`
- [ ] Mark this TODO as **completed**
