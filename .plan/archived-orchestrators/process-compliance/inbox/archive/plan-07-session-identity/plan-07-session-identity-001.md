envelope_version=1
sender_type=plan
sender_id=plan-07-session-identity
epic=process-compliance
kind=finding
created=2026-09-18T15:13:57Z

## Process-compliance self-report: plan-07-session-identity init session (2026-09-18)

Sender is the executing plan `plan-07-session-identity` (phase 1-init, on main checkout — the correct store for phases 1-4). One `finding` per violation; all observed in this session before any implementation work.

### V1 — implementation dirt on main instead of a worktree (remediated)

- Observed: main checkout carried uncommitted PLAN-07 implementation (4 modified files + 1 untracked test) with no plan and no worktree. This session made zero of those edits (verified: no Edit/Write issued before discovery).
- Remediation applied: `git stash push -u -m plan07-session-identity-wip-on-main` (stash@{0}); `git status --porcelain` now empty. Pre-existing stash@{1} (`PLAN-03 in-flight implementation`) untouched.
- Residual: stash@{0} must be applied inside the phase-5 worktree after `prepare_execute`, never popped on main. Plan shell `plan-07-session-identity` created (1-init) so the worktree has an owner at move-in time.
- Worktree note: no worktree was materialized now — `prepare_execute` runs at phase-5 entry per ADR-002. Creating one mid-init would itself violate phase ordering; main-clean + plan-shell is the compliant holding state.

### V2 — direct `.plan/` reads via Read tool

- Observed: session opened with `Read` on `.plan/local/orchestrator/finalize-machinery/plans/PLAN-07-session-identity.md` and `Read` on `.plan/...` directory listings, violating "`.plan/` access via scripts only".
- Remediation: all subsequent `.plan` access went through `execute-script.py` (`orchestrator queue/inbox`, `manage-plan-documents request create/read`, `manage-status`, `manage-references`, `manage-config`, `manage-logging`, `manage-metrics`, `manage-files create-or-reference`). No further direct `.plan` reads.

### V3 — Glob/Grep before the structured architecture inventory

- Observed: file discovery used `Glob`/`Grep` first, violating "Structured queries first" (`architecture files/which-module/find/search --content` first, Glob/Grep as fallback).
- Remediation: going forward all codebase navigation starts at `plan-marshall:manage-architecture:architecture`; Glob/Grep only for sub-module narrowing or inside already-known files.

### V4 — foundational standards not loaded at session start

- Observed: `persona-plan-marshall-agent` requires loading `agent-behavior-rules.md` + `user-communication.md` unconditionally before development work; session loaded persona shells but not these standards.
- Remediation: loading both now (this finding records the gap); `tool-usage-patterns.md` loaded for the file-ops/build work ahead.

### V5 — init advanced mid-flight while audit pending (held, not violated)

- Observed: phase-1-init progressed through request ingestion, recipe-match (no match), aspect-classify (`implementation`), references seeding, domain-detect (`general-dev, plan-marshall-plugin-dev, python`), sibling-collision-check (clean), change-type/scope heuristics (ambiguous / multi_module-inflated-by-`.plan`-paths), lane route (`deep`).
- Deviation recorded: router returned `planning_lane: deep` with `persisted: false`; mirrored explicitly via `metadata --set planning_lane deep`. Posture prompt (Step 8d), phase handshake capture, metrics boundary, and 1-init→2-refine transition are HELD — no phase advance until this audit lands.

### V6 — config staleness signal

- Observed: `generate_executor preflight` reports `executor_action: fresh`, `marshal_status: stale` (installed 0.1.1696 vs marshal 0.1.1636). Advisory only; operator runs `/marshall-steward` to reconcile. No auto-mutation performed.
