# Landing Analysis: PLAN-46 — orchestrator title-repaint routed through the primary channel

epic: truthful-signals
workstream: WS-01
pr: #994 (https://github.com/cuioss/plan-marshall/pull/994) — squash-merged, 76c4e39e7

> Landing record for one shipped plan. Corroborated against the merged diff at
> 76c4e39e7 and the commit narrative. This is the REAL FIX for the triple-archetype
> defect: orchestrator title state was computed correctly then handed to a channel
> (/dev/tty fallback) that structurally cannot deliver without a controlling tty.

## Deliverable Fidelity vs Spec

Spec re-scoped to 5 deliverables (D1 gate + D2–D5). All shipped; corroborated against
the merged file set.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 gate — session-slug-binding hypothesis; separate plan-side residual? | shipped-as-specified | session_binding.py (+177) adds a parallel `active-orchestrator` session slot, kind-disjoint (plan read path byte-unchanged) |
| D2 — persisted non-delivery log | shipped-as-specified | _status_core.py (+31) routes the drive-seam non-delivery through a persisted `log_entry` (no longer stderr→void) |
| D3 — orchestrator branch in the hook-driven render = THE REAL FIX | shipped-as-specified | _claude_runtime_impl.py (+73) `_read_active_orchestrator` + render-title orchestrator fallback into the PRIMARY hook channel; claude_runtime.py (+14); push-title-token --store orchestrator binds the epic and distinguishes `reason=feature_inactive` from `no_controlling_tty` |
| D4 — stop reporting a dead-channel no-op as success + reconcile contract wording | shipped-as-specified | terminal-title-architecture.md (+82), orchestration-model.md (±4), platform-runtime/contract.md (+23) — self-review caught a 3rd doc gap D4 initially missed (contract.md feature_inactive outcome) → fixed |
| D5 — tests | shipped-as-specified | test_title_token.py (+216), test__claude_runtime_impl.py (+176), test_claude_runtime.py (+38), test_session_binding.py (+137) |

## Metrics and Anomalies

- Tokens: 2,479,038 total. Duration: 3h54m wall / 2h27m worked. Diff 825 insertions /
  146 deletions, 11 files — the biggest of the three landings.
- Routing: planning lane escalated light→deep at init (scope heuristic under-counted 1 path
  for a genuinely 5-deliverable multi-module change; D1 was an investigation gate).
- Anomalies: none blocking. Self-review folded a recurrence into flagship doc-contract
  lesson 2026-06-29-16-001 (a doc gap D4's own sweep missed) — an in-plan catch, not a defect.

## Routing and Merge Behavior

- Review: not separately captured; merged clean.
- CI/merge: green, squash-merged via merge queue. Surface (platform-runtime session/render +
  manage-status _status_core + terminal-title docs) disjoint from concurrently-launched
  PLAN-45 (build-execute) — no collision.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated → shipped, pr 994, landing landings/PLAN-46.md
- [x] epic.md queue reconciled from status.json
- [x] Watch (6) title-repaint non-delivery logged-to-void: RESOLVED — D2 persists the
      non-delivery; D3 delivers on the primary channel
- [x] Triple-archetype instance (confident-signal + vacuous-guard + doc-contract-divergence) closed
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- ⚠ Orchestrator titles now repaint via the PRIMARY hook channel **in sessions running the
  fixed cache**. This live session still returned `pushed:false reason:no_controlling_tty`
  at resume — the running cache/daemon predates the fix; the source defect is closed, the
  running binary catches up on the next upgrade. Do not re-report as a new defect.
- The nine-verb repaint contract's best-effort framing is now truthful (feature_inactive vs
  no_controlling_tty distinguished), retiring the vacuous-guard sub-instance.
