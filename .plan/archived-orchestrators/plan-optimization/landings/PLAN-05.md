# Landing Analysis: PLAN-05 — terminal-title-stale-build-busy

epic: plan-optimization
workstream: WS-02
pr: #931 (squash-merged to main — commit `ba04f4b6b`)

> Verified against ground truth: `ba04f4b6b fix(terminal-title): clear stale build-busy token on
> phase transition (#931)` on main. Operator narrative corroborated.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Fix stale `build-busy` token not clearing on phase transition | shipped-as-specified (root-cause, spec option (a)) | New `drop_stale_build_busy(status)` in `_status_core.py`, called in both `cmd_transition` + `cmd_set_phase` before `write_status`; pops `title_token` ONLY when it equals `build-busy` (lock tokens preserved). `_surface_drive` repaints without 🔨. 4 tests: transition/set-phase clear, loop-back, lock-token-preserved guard, killed-detached-build repro. |
| Correct the title-token lifecycle contract in docs | shipped + scope-expanded | Contract corrected in `status-lifecycle.md`, `terminal-title-architecture.md`, `agent-behavior-rules.md`. Q-Gate flagged the 3rd doc (terminal-title-architecture.md); operator folded it in. |

**Re-scope note:** the spec speculated BK #912's state-gate-first wake path might have dissolved the
defect. It did NOT — the killed-detached-build case genuinely leaves the token armed (clear obligation
lives after an op that never completes). So this was a real fix, not the no-op audit I'd flagged as
possible. The chosen fix is the spec's option (a) (phase-transition-safe reset), correctly scoped to
`build-busy` so the live signal for genuine in-flight builds is preserved.

## Metrics and Anomalies

- Tokens: 1.9M / 2h35m wall — lean.
- Anomalies:
  - **Phase-4 re-dispatch edited the main checkout** (planning-phase violation) while addressing a
    Q-Gate finding; reverted so the edit landed in phase-5. Lesson `2026-07-18-13-002`. → RECURRENCE
    of the "leaf/planning phase edits MAIN checkout" class (lesson 17-001, #920). See Watches.
  - **Light-lane refine didn't persist `pr_title`** → failed a handshake invariant; operator authored
    it and continued. Lesson `2026-07-18-13-001`.

## Routing and Merge Behavior

- Review: 1 comment (Sourcery rate-limit noise); review-retrospective 0 net actionable.
- CI/merge: green; squash-merged via merge queue; branch + worktree removed.
- **Collision check — adjacency prediction HELD.** PLAN-05 touched `agent-behavior-rules.md`, shared
  with PLAN-04 (which landed AFTER, #930, and rebased over it). No conflict at PLAN-05's own merge
  (sync-baseline rebased clean).
- **⚠ Stale merge-lock incident (operational defect):** PLAN-05's merge was blocked by a merge-lock
  held by the DEAD original ci-pr-safe-merge plan (the vanished PLAN-06 dir — verified absent
  everywhere; auto-reclaim had missed it). The session released the stale holder to unblock the FIFO
  queue. → Watch.

## Reconciliation Actions

- [x] status.json PLAN-05 → shipped, pr=931, landing=landings/PLAN-05.md
- [x] epic.md queue row + WS-02 charter reconciled
- [x] Watches added: stale-merge-lock-from-dead-plan; planning-phase-edits-main recurrence
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

- **marshal.json provisioning stamp was stale at session start** (0.1.1134 vs installed 0.1.1140) —
  operator flagged a steward refresh owed. This is a live instance of the **PLAN-08** executor-manifest
  fail-open class (stale `provisioned_version`) — reinforces PLAN-08's severity. Not new work; PLAN-08
  owns the root cause.
- Gemini pruned from this plan's review config (sunset) — consistent with the standing steward action.
