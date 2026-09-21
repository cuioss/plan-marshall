# PLAN-07: Opencode abstraction repairs

epic: process-compliance
workstream: WS-06

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-07-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Repair what surrounds finalize-machinery PLAN-07 (session-identity resolver, never
re-staged here): the opencode runtime gaps that forced improvisation (no session id,
no transcript, hook_not_configured), the NO_SESSION_IDENTITY sentinel convention, and
unattended-order merge authorization whose consent prompt is indistinguishable from a
blocking question. A run on opencode degrades visibly instead of stranding silently.

## Deliverables

1. Opencode runtime gap repairs around PLAN-07 (no session id / no transcript / hook_not_configured degrade paths).
2. NO_SESSION_IDENTITY sentinel convention documented and enforced.
3. Unattended-order merge authorization distinguishable from a blocking question.
4. Tests pinning each degrade path and the sentinel.

## Claim Labels

- OBSERVED: Opencode runtime gaps (no session id, no transcript, hook_not_configured) forced improvisation — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material G`
  - verdict: corroborated | checked_at: e8a716501 | by: process-compliance/analyze | rescoped: n/a | evidence: opencode runtime gaps landed visibly: degrade paths + sentinel + distinct consent prompt (PR #1554)
- OBSERVED: Transcript-less handling is staged as finalize-machinery PLAN-07 and is referenced here, never re-staged — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material G`
  - verdict: corroborated | checked_at: e8a716501 | by: process-compliance/analyze | rescoped: n/a | evidence: transcript-less handling stayed referenced (finalize-machinery PLAN-07), not re-staged: PR #1554 touches only the surrounds
- OBSERVED: The merge gate's consent prompt is indistinguishable from a blocking question — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material G`
  - verdict: corroborated | checked_at: e8a716501 | by: process-compliance/analyze | rescoped: n/a | evidence: distinct unattended consent prompt with gap class + HEAD label landed in _cmd_merge_authorization.py (PR #1554)
- HYPOTHESIS: The opencode runtime seam lives in platform-runtime — confirm/refute at `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` §§ `session_capture`, `metrics_capture` (verify-at-outline; corrected 2026-09-18: no bare `runtime` symbol, entry points are the session/metrics no-ops)
  - verdict: corroborated | checked_at: e8a716501 | by: process-compliance/analyze | rescoped: n/a | evidence: NO_SESSION_IDENTITY sentinel + meaning guard landed in runtime_base.py, contract + no-op-policy docs (PR #1554)
- Verify-first clause: The consuming phase must settle the HYPOTHESIS against the implementing source before scoping — refutation loops back to re-scope. Must not re-stage PLAN-07.
  - verdict: unverifiable | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction to the consuming phase, not a checkable world premise; no implementing-source check applies

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py` — opencode runtime seam
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/platform_runtime.py` — runtime dispatch
- OBSERVED: `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` — runtime contract docs
- OBSERVED: `test/plan-marshall/platform-runtime/` — runtime regression tests

## Dependencies and Sequencing

- Depends on: PLAN-06 (all contract work settled; ordering only)
- Overlaps with: none (only plan touching platform-runtime)
- Adjacent to: finalize-machinery PLAN-07 — reference, never touch

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/process-compliance/plans/PLAN-07-opencode-repairs.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## Re-grounding instruction

Re-verify every Claim Label against the implementing source at HEAD during outline;
settle the HYPOTHESIS via `corpus set-verdict` before scoping. If PLAN-07 has landed
with a different sentinel, re-scope to it rather than inventing a second convention.

## Adjacency and overlap notes

Read finalize-machinery PLAN-07 as reference only. Any change to the resolver itself
belongs there, not here — file an inbox finding instead.

## Incorporated lessons

- `archive/lessons/2026-09-07-15-007.md` — standing unattended authorization covers
  only gates whose threshold the situation satisfies; surfacing decisions taken on
  behalf of the operator.
- `archive/lessons/2026-09-16-11-001.md` — OpenCode usage/session capture gap
  (`hook_not_configured`): implement capture or document as known limitation.
- `archive/lessons/2026-08-25-09-006.md` — transcript fallback: retry canonical
  resolution against `status.metadata.session_ids`; capture appends new sessions.

## Folded inbox evidence (drain 2026-09-18, boundary only, no new file surface)

- `lessons-pipeline-002`: `execution.md` Finalize Phase resolver aborts when
  `session capture` fails with `hook_not_configured` / `no_session_id`, one layer
  above the graceful `record-metrics` no-op — unattended opencode finalize cannot
  enter the phase that already handles the absence. Resolver changes belong to
  finalize-machinery PLAN-07 (reference-only boundary above); recorded here as the
  surrounding evidence for the sentinel convention, not as staged scope.
