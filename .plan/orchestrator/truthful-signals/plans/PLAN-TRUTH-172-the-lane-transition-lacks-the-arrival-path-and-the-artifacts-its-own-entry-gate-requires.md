# PLAN-TRUTH-172: The lane transition lacks an arrival path for one verdict shape, and the artifacts its own entry gate requires

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

**SPLIT OUT of `PLAN-TRUTH-147` on 2026-09-18 (cleanup A5).** That spec carried **13 deliverables against
the epic's operator-set ceiling of 12**, and its members fell into two groups that share no file: the
phase-5 / yield-naming half (which stays there) and the **lane-transition** half (which is here). The split
is along the seam the source spec's own objective already named — *"a phase hands back control"* versus
*"a lane transitions"*.

Both halves descend from superseded specs that stay on disk as the audit record:
`PLAN-TRUTH-104-a-clear-verdict-over-an-empty-population-is-reported-as-a-checked-negative.md` (D1) and
`PLAN-TRUTH-141-the-light-lane-cannot-author-the-pr-title-its-own-entry-gate-requires.md` (D2, D3).

## Objective

**A lane transitions without the artifact its own entry gate requires, and the finalize branch table has no
arrival path for one verdict shape — so a clear verdict over an empty population reads as a checked
negative, and a light-lane plan cannot satisfy a handshake invariant that lane can never produce.**

Two mechanisms, one seam: the moment a plan crosses from one lane or phase into the next, carrying (or
failing to carry) what the next gate will demand of it.

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: derive the verdict-arrival population and re-ground the light-lane premise at HEAD.**
Enumerate every verdict shape the finalize branch table can receive and which have an arrival path
(carried from `PLAN-TRUTH-104` D0, which the source spec never ran), and re-confirm that the light lane
still cannot author `metadata.pr_title` at HEAD. ⛔ Publish both populations with sizes.

**D1 — The finalize branch table gains the arrival path it is missing.** A clear verdict over an EMPTY
population must not arrive at the same branch as a verdict over a checked one — that collapse is what makes
an unexamined population read as a checked negative. (`PLAN-TRUTH-104` D1.)

**D2 — The light lane authors `metadata.pr_title` on its own path.** With `planning_lane=light` the
collapsed refine+outline+derive envelope never reaches `phase-2-refine` Step 13, the only producer of that
field, so the 2-refine `phase_handshake capture` refuses with `pr_title_missing` on **every** light-lane
plan — a false-RED gate whose only exit is a hand-authored value. ⚠ Two corpus lessons recorded this
independently (`2026-09-04-12-001`, which also names `track`, and `2026-09-08-15-001`), both retired into
this epic's archive on 2026-09-18. (`PLAN-TRUTH-141` D1.)

**D3 — A transition-time phase-array invariant, plus the controls.** The array a transition writes is
checked at the moment it is written rather than trusted later. Controls: three verdict shapes produce three
distinct outcomes with a matched negative control; a light-lane plan reaches capture with its own
`pr_title`; and the two local lessons `PLAN-TRUTH-141` identified are retired once the fix lands.
(`PLAN-TRUTH-141` D2 + the `-104`/`-141` control sets.)

## Claim Labels

⛔ Every claim is a POINTER at the superseded source spec that authored it; both are on disk in this epic's
`plans/`. Re-derive each from the source's own `## Claim Labels` at HEAD — D0 owns that re-grounding, which
`PLAN-TRUTH-147` never performed for these members.

- HYPOTHESIS: every scoping premise carried from `PLAN-TRUTH-104` still holds at HEAD — confirm/refute at
  that spec's `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-104 Claim Labels: 11 verdicts, 8 unverifiable, none contradicted.
- HYPOTHESIS: every scoping premise carried from `PLAN-TRUTH-141` still holds at HEAD — confirm/refute at
  that spec's `## Claim Labels` (verify-at-outline)
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Pointer at PLAN-TRUTH-141 Claim Labels: 7 top-level bullets, ZERO persisted verdicts - never re-grounded (same gap PLAN-TRUTH-147 c3 has).
- OBSERVED: the light-lane `pr_title` defect was re-confirmed first-party on 2026-09-17 —
  `pr_title_missing` is raised by `plan-marshall/scripts/_handshake_commands.py` line 470 (invariant
  documented at `_invariants.py` line 321), and neither `planning.md` nor `light-lane.md` mentions
  `pr_title`.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: All three limbs confirmed at HEAD: pr_title_missing raised at _handshake_commands.py:470 (and again 610); the invariant documented at _invariants.py:314-332; and a whole-file probe for pr_title returns ZERO hits in both planning.md and light-lane.md.
- OBSERVED: this spec carries no deliverable of its own invention — all four are `PLAN-TRUTH-147`'s D8–D11
  and their gate, moved without rewording. The split changed the owner, not the work.
  - verdict: corroborated | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: PLAN-TRUTH-147's deliverable list marks D8, D9 and D10 MOVED OUT 2026-09-18 to PLAN-TRUTH-172 and reassigns the -104/-141 control sets to -172 D3; -172's D0-D3 map onto exactly those members plus their gate.

## Expected Surface

Carried from `PLAN-TRUTH-147`, restricted to the members that moved:

- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py`
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md`
- `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md`
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py`
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py`
- `test/plan-marshall/plan-marshall/`
- `test/plan-marshall/manage-tasks/scripts/`

## Dependencies and Sequencing

- Depends on: none.
- ⛔ **Never pair with `PLAN-TRUTH-147`** — the two halves of one split share `phase-6-finalize` and
  `manage-status` surfaces, and the split was made to reduce plan size, not to license concurrency.
- ⚠ D2 touches `_invariants.py` and `manage-status/scripts/`, which `PLAN-TRUTH-170` (step records) and
  `PLAN-TRUTH-171` (state writers) also declare. Sequence.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-172-the-lane-transition-lacks-the-arrival-path-and-the-artifacts-its-own-entry-gate-requires.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
