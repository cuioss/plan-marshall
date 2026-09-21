# Landing Analysis: PLAN-12 — orchestrator-archive-verb

epic: plan-optimization
workstream: WS-06
pr: #937 (merged via squash queue — commit `25a46b407`)

> Verified: `25a46b407 feat(marshall-orchestrator): add archive verb for closed epics (#937)` on main;
> `orchestrator.py` carries the `archive` subcommand + `archived-orchestrators` resolver;
> `workflow/archive.md` exists. Operator narrative corroborated. Self-referential: this is the verb the
> plan-optimization epic itself could use at close.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — archive mechanics (subcommand + resolvers + read-fallback) | shipped-as-specified | `archive` subcommand relocates a CLOSED epic to `.plan/local/archived-orchestrators/{slug}/` (`file_ops.py`, `orchestrator.py`, `_status_core.py`); status/resume/scan read-resolve archived epics; write verbs stay strict. pytest added. |
| D2 — verb surface + lifecycle docs | shipped-as-specified | SKILL.md router + canonical block, `workflow/archive.md`, `orchestration-model.md` (lifecycle: close freezes → archive relocates), `orchestrate.md`, `resume.md`. |

**Design decisions from the spec HELD:** `close` stays freeze-in-place; archive is additive/opt-in;
precondition = closed epic; read-verbs resolve archived, write-verbs strict.

**Behavioral note:** the `archive` verb is in the source bundle + regenerated executor (→ 0.1.1149) but
this running orchestrator session's cache may predate #937 — a session restart / cache sync is needed
before the verb is invokable here. Irrelevant until the epic closes; noted for the eventual close+archive.

## Metrics and Anomalies

- CodeRabbit found **4 real defects** in the initial impl (get/set mutual-exclusion gap, idempotent-rerun
  log ordering, output-contract path mismatch, archived-resume read-only branch) → fixed via loop-back
  (TASK-4..7), re-tested, merged. **Lesson `2026-07-19-12-001`**: a read-fallback must be matched by
  write-guards on every sibling mutation verb (a genuinely reusable rule).
- Merge re-review timeout → merge-anyway after 2×600s (CodeRabbit dedups an unchanged rebased diff →
  never posts a "fresh" review; comment barrier + queue CI were the safety nets). Same bot-timeout class
  as open `13-21-001`.

## Routing and Merge Behavior

- CI/merge: green; squash via queue (`25a46b407`). Disjoint from in-flight PLAN-14/15.
- **⚠ Stale-merge-lock AGAIN (class now ~n=4):** two stale cross-plan merge locks reclaimed during this
  run — held by the **parked worktrees of PLAN-11 (footprint-driven-build-gating) and PLAN-15
  (stale-merge-lock-reclaim)**, both with NO active finalize session. New variant:
  **parked-worktree-with-no-active-session holds the lock stale.** Strongly reinforces in-flight PLAN-15
  — and note the meta-irony that PLAN-15's OWN worktree was a stale holder, so PLAN-15 must cover this
  variant (and self-verify it).

## Reconciliation Actions

- [x] status.json PLAN-12 → shipped, pr=937, landing=landings/PLAN-12.md
- [x] epic.md queue row + WS-06 charter → COMPLETE
- [x] stale-merge-lock watch updated (new parked-worktree variant → PLAN-15)
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **WS-06 COMPLETE** (single-plan workstream).
- **The epic can now self-archive at close** — once PLAN-13..19 land and the epic closes, `close` then
  `archive` (after a session/cache refresh picks up #937). A tidy dogfood of the new verb.
- Provisioning stamp stale (0.1.1134 vs 0.1.1149) + session-restart recommended (agent registry
  session-pinned; executor regenerated) — operator/steward chores, not epic work.
