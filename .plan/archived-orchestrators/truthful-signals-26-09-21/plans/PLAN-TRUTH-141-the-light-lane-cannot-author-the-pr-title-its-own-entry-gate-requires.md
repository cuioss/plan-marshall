# PLAN-TRUTH-141: The light lane cannot author the PR title its own entry gate requires, and no transition checks the phase array

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-11 from the cross-repo lessons drain, inbox message
`api-sheriff-deployment-configurability-008` (API-Sheriff's `deployment-configurability` epic, relaying
its lesson `2026-09-06-07-001` observed on API-Sheriff PLAN-15). It is the **third independent sighting**
of the `pr_title` half: this repository's own corpus already carries two active lessons for it —
`2026-09-04-12-001` (*"Light-lane envelope never authors pr_title, so the 3-outline handshake capture
fails"*) and `2026-09-08-15-001` (*"Light lane cannot satisfy the pr_title_present invariant — no writer
on that path"*) — plus a settled note, and **no staged plan**. The sender flagged recurrence risk as high:
light routing is the expected default for bounded, well-specified changes.

The observation's other half (`2-refine` left `in_progress` while `3-outline` was transitioned) was
**fixed by #1399** (`d03ca621c`): the orchestrator now transitions and captures `2-refine` before it
dispatches the light envelope. That fix is what makes the `pr_title` half fail LOUDLY today rather than
silently — and it is also the reason this spec exists as a transition-time rule rather than a one-off fix.

## Objective

**On the light lane, the orchestrator captures the `2-refine` invariants before the light envelope runs,
the `pr_title_present` invariant applies from `2-refine` onward, and the only writers of
`metadata.pr_title` live in `phase-2-refine` — which the light lane never dispatches.** So every
light-routed plan hits `pr_title_missing` at the `2-refine` capture and needs a manual repair. Fix the
light lane so it authors the PR title on its own path, and add the general rule that would have caught
both halves at the transition that created them: **at most one non-terminal phase, and every phase before
`current_phase` is `done`** — checked at every `manage-status transition`, so a lane that elides a phase's
work can never also elide its terminal bookkeeping.

## Deliverables

1. **D0 — re-ground at HEAD before implementing.** Re-verify both halves below against the implementing
   source, and establish whether any light-lane plan has passed the `2-refine` capture since #1399 (a
   green one refutes the `pr_title` half and re-scopes this spec). Name the artifact each check read.
2. **D1 — the light lane authors `metadata.pr_title` on its own path**, before the orchestrator's
   `2-refine` capture reads it, derived the same way `phase-2-refine` Step 13 derives it. ⛔ Do NOT relax
   `pr_title_present` for the light lane: the invariant is correct and is what surfaced the gap.
3. **D2 — a transition-time phase-array invariant.** `manage-status transition` refuses (structured error,
   nothing written) when the result would carry more than one non-terminal phase, or a phase before
   `current_phase` that is not `done`. The refusal names the offending phase(s). Loop-back re-entry, which
   legitimately re-opens an earlier phase, is enumerated explicitly as the one sanctioned exception rather
   than inferred.
4. **D3 — controls.** A light-lane test proving the capture passes with a derived `pr_title`; a transition
   test proving D2 refuses the exact pre-#1399 state (`2-refine` `in_progress`, `3-outline` transitioned);
   and a matched positive control proving a loop-back re-entry is still admitted. Each test must be shown
   to go red against the unfixed code.
5. **D4 — retire the two local lessons** `2026-09-04-12-001` and `2026-09-08-15-001` on landing, through
   the sanctioned `manage-lessons` retirement surface, naming this plan as the covering change.

## Claim Labels

- OBSERVED: `pr_title` has no writer on the light-lane path — `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` carries zero occurrences of `pr_title`, and the only writers are `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md` and `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md`, at `356973d80`.
- OBSERVED: the orchestrator transitions `2-refine` and runs `phase_handshake capture --phase 2-refine` BEFORE dispatching the light envelope — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` § the light-lane branch (steps a–c), at `356973d80`.
- OBSERVED: `pr_title_present` applies from phase `2-refine` onward and raises `PrTitleMissing` — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` § `PrTitleMissing`, at `356973d80`.
- OBSERVED: `cmd_transition` marks the completed phase `done` and the next `in_progress` and asserts nothing about earlier phases — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` § `cmd_transition` (:342-464), at `356973d80`.
- HYPOTHESIS: every light-routed plan since #1399 fails the `2-refine` capture with `pr_title_missing` — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` § the light-lane branch, by checking whether any step between the transition and the capture writes `pr_title` (verify-at-outline).
- HYPOTHESIS: loop-back re-entry is the only sanctioned way an earlier phase becomes non-`done` again — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` § `_loop_back_auto_override` and the loop-back re-entry marker write (verify-at-outline).
- Verify-first clause: D0 settles both HYPOTHESIS claims against the implementing source before D1/D2 are scoped; a refuted first claim re-scopes this spec down to D2 alone.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` — the light-lane envelope that gains the `pr_title` authoring step (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — the light-lane branch's transition/capture sequence (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — `cmd_transition`, the D2 invariant host
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — the `transition` refusal contract documented to callers (D2) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-status/` — the D2 controls (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/plan-marshall/` — the light-lane capture control (D3) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — `pr_title_present`, read-only (the invariant is correct and stays unchanged)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: `PLAN-TRUTH-127` touches the phase record of looped-back plans at archive time; its fix
  and D2 both reason about loop-back re-entry and must agree on what a legitimately re-opened phase looks
  like. Check disjointness at emit.
- Adjacent to: `PLAN-TRUTH-119` (early-phase gates) sits on `phase-2-refine` / `3-outline` gate quality —
  this spec touches no gate's scoring, only the light lane's handoff bookkeeping and the transition verb.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-141-the-light-lane-cannot-author-the-pr-title-its-own-entry-gate-requires.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-147-a-lane-reports-green-yields-or-transitions-without-the-artifact-its-own-gate-requires.md` (PLAN-TRUTH-147)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
