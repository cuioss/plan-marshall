# WS-05: User-facing surface remediation

epic: operator-ux

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-05-surface-remediation.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Apply the standards WS-03 and WS-04 establish to the surfaces users actually meet, in ONE pass
per site rather than one pass per rule. The heaviest prompt sites carry both defects at once —
the pasted api-sheriff prompt was simultaneously context-poor and vocabulary-leaking — so
splitting them into a "context" sweep and a "vocabulary" sweep would edit the same files twice
and collide with itself. The workstream closes when every surviving user-facing prompt and
report at the census'd sites conforms to both standards, verified by the WS-03 doctor rule
rather than by reading.

## Scope

- In scope: the prompt-dense sites — `marshall-steward/references/menu-configuration.md` (29
  prompt references), `phase-6-finalize/standards/branch-cleanup.md` (24),
  `phase-1-init/SKILL.md` (20), `plan-marshall/workflow/planning.md` (18),
  `marshall-steward/references/wizard-flow.md` (12), and the remaining sites the WS-03 rule
  flags; the user-facing report/summary text emitted at phase boundaries.
- Out of scope: authoring the standards themselves (WS-03, WS-04); prompts that WS-01 or WS-02
  delete outright — a deleted prompt needs no remediation, which is why this workstream is
  sequenced last; developer-facing documentation.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-08-remediate-user-facing-sites | staged | One-pass conformance sweep of the prompt-dense sites against the WS-03 + WS-04 standards |

## Sequencing and Surface Notes

- **Depends on PLAN-05, PLAN-06 and PLAN-07 — all three.** This is the epic's terminal plan by
  construction: it conforms to standards, so it cannot start before they exist.
- **Should also run after PLAN-01 and PLAN-04**, which each remove prompts. Remediating a
  prompt that a sibling plan is about to delete is pure waste, and the deletion is the better
  outcome for the same complaint.
- Collides broadly — `menu-configuration.md` and `wizard-flow.md` are shared with WS-02, and
  `phase-1-init/SKILL.md` sits next to WS-01's detector call site. **Expect this plan to run
  alone**, with the second concurrency slot left deliberately unfilled.
- Scope-bloat risk is real here: the site list is long. If the WS-03 doctor rule flags
  materially more than the six named sites, split along bundle boundaries
  (`plan-marshall` / `marshall-steward` / everything else) rather than growing one plan.
