# PLAN-LB-04: Light-lane plans pass the refine boundary without an override

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-04-light-lane-refine-boundary.md` and is queued as one row file, `queue/PLAN-LB-04.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

A plan routed to the light planning lane never runs `phase-2-refine`; the orchestrator closes `2-refine`
itself and then dispatches one collapsed refine+outline envelope. `phase-2-refine` Step 13 is the only place
that writes `status.metadata.pr_title`, and the `pr_title_present` handshake invariant demands that field
from the `2-refine` capture onward. The orchestrator's own `phase_handshake capture --phase 2-refine` on the
light lane therefore refuses with `pr_title_missing` on every light-lane plan, before the envelope is even
dispatched, and the plan stops until someone sets a title by hand or passes `--override --reason`. Give the
light lane its own producer for what the `2-refine` boundary demands, so small plans start without an
operator in the loop. Carries forward truthful-signals PLAN-TRUTH-172 deliverable D2 and process-compliance
PLAN-10 deliverable D1.

## Deliverables

1. **The light lane writes `pr_title` before its `2-refine` capture.** `planning.md`'s light-lane branch
   authors a commit-style PR title from the request (the same shape rules as `phase-2-refine` Step 13:
   at most 72 characters, imperative, `type(scope): summary`) and persists it with `manage-status metadata
   --set --field pr_title` BEFORE the orchestrator-side `phase_handshake capture --phase 2-refine`. The
   capture precedes the envelope dispatch for reasons the document states, so the producer sits on the
   orchestrator side of that boundary; the light-lane envelope may refine the title after it has read the
   code, and `create-pr.md`'s staleness check already re-derives it against the executed scope. The
   invariant itself is not weakened: no lane-conditional skip is added to `_capture_pr_title_present`.
   Done when: an end-to-end handshake test walks the light-lane sequence as `planning.md` documents it
   (transition `2-refine`, boundary stamp, capture) and the capture returns `status: success` with no
   `--override`; the same test with the producer step omitted still returns `error: pr_title_missing`; a
   document-contract test asserts that in the light-lane section the `pr_title` persist appears before the
   `2-refine` capture.
2. **A capture-source matrix for the `2-refine` boundary, and every row has a light-lane producer.** The
   plan enumerates every value the `2-refine` capture or a later phase requires that `phase-2-refine` Step
   13 produces on the deep lane (`pr_title`, `track`, `scope_estimate`, the module mapping, and whatever
   else the enumeration finds), and records for each which step produces it on the light lane. The matrix
   is published once, in `planning.md` beside the light-lane branch or in the phase-lifecycle standard it
   links, and a test derives the deep-lane producer set from `phase-2-refine/SKILL.md` Step 13 and fails
   when a member has no named light-lane producer. Any member found without one is given a producer in the
   same plan — expected for `track`, which `light-lane.md` says it persists but for which it shows only
   the `scope_estimate` command.
   Done when: the matrix exists, the derived test passes, and a light-lane fixture plan reaches
   `phase-4-plan`'s `manage-references get --field track` read with `track=simple` present.
3. **The refusal names the producer for the lane the plan is on.** `PrTitleMissing`'s message says
   "phase-2-refine Step 13 must author and persist a commit-style PR title", which sends an operator on a
   light-lane plan to a phase that plan never runs. The `pr_title_missing` payload from both `capture` and
   `verify` names the light-lane producer when `planning_lane` is `light` and the deep-lane one otherwise,
   and gives the exact `manage-status metadata --set --field pr_title` command either way.
   Done when: two tests, one per lane, read the refusal payload and find the lane-correct producer named;
   the `verify` and `capture` payloads stay identical in shape.

## Claim Labels

- OBSERVED: the invariant applies from `2-refine` onward on every plan and has no lane branch — `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` § `_capture_pr_title_present` (:1683-1713: returns `None` only for `1-init`, otherwise raises `PrTitleMissing` when `metadata.pr_title` is absent or blank), registered with `_always` (:1734) and scoped `blocking_at_every_boundary` (:1852).
- OBSERVED: `capture` and `verify` both turn the exception into a boundary refusal — `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_commands.py:467-474` (`cmd_capture`, `error: pr_title_missing`) and `:597-614` (the same payload on the verify path).
- OBSERVED: the only producer of `metadata.pr_title` is `phase-2-refine` Step 13 item 4 — `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md:268`; a search for `pr_title` in `plan-marshall/workflow/planning.md`, `phase-3-outline/workflow/light-lane.md`, `phase-3-outline/SKILL.md` and `phase-1-init/SKILL.md` returns no hit.
- OBSERVED: the light lane never dispatches `phase-2-refine`, and the orchestrator runs the `2-refine` transition, boundary stamp and capture itself before dispatching the envelope — `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` light-lane branch step 2 (:243-271; "The light lane never dispatches `phase-2-refine`" at :248; the capture call at :266-269).
- OBSERVED: the placement of that capture before the dispatch is deliberate and load-bearing (metrics attribution by spawn timestamp, and the envelope's entry protocol verifies the captured `2-refine` row) — `planning.md:243-246`. A producer inside the envelope would run after the capture it has to satisfy.
- OBSERVED: the refusal message names only the deep-lane producer — `_invariants.py` § `PrTitleMissing` (:313-332, "phase-2-refine Step 13 must ...").
- OBSERVED: the capture accepts an override that needs a reason — `_handshake_commands.py:427-431` ("`--override requires --reason`"); `planning.md` does not mention using it on the light lane.
- OBSERVED: `create-pr` reads `metadata.pr_title` as its only title source and re-derives a stale one against the executed scope — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md:256-292`.
- OBSERVED: `phase-2-refine` Step 13 also persists `scope_estimate` and `track` (items 2 and 3, `SKILL.md:266-267`), and `phase-4-plan` reads `track` from references — `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md:687` and `:706-708`.
- HYPOTHESIS: the light lane does not persist `track` — `light-lane.md:122` says "Persist the (possibly refined) scope/track to references.json" and the command block that follows sets only `scope_estimate` (:125-126); a search for `--field track` across `phase-1-init/`, `phase-3-outline/` and `plan-marshall/workflow/` returns nothing. Confirm/refute by reading `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` end to end and `manage-status planning-lane route` for a side effect that writes it (verify-at-outline).
- HYPOTHESIS: `planning_lane` is readable from plan status at capture time, so the refusal in Deliverable 3 can pick the lane-correct producer without a new input — confirm at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` § the `planning-lane` verbs (:765-830) and the `metadata` dict `_capture_pr_title_present` receives (verify-at-outline).
- HYPOTHESIS: every light-lane plan hits this refusal — recorded independently by two retired lessons (`2026-09-04-12-001`, which also names `track`, and `2026-09-08-15-001`) and by several plan runs that continued under `--override`; not reproduced here. Reproduce by walking the light-lane sequence against a fixture plan (verify-at-outline).
- Verify-first clause: reproduce `pr_title_missing` on the documented light-lane sequence at HEAD before changing anything. If a producer has appeared since, close Deliverable 1 with that finding and keep Deliverables 2 and 3.
- Verify-first clause: settle at outline whether the orchestrator can author a good-enough title before any code is read. The default is yes, from the request narrative, with the envelope free to overwrite it; if the outline rejects that, the alternative is to move the `2-refine` capture's `pr_title` requirement to the `3-outline` boundary for light-lane plans only — a change to the invariant that needs the operator's agreement, because it is the one option that relaxes a gate.
- Verify-first clause: build the Deliverable 2 matrix from Step 13 and the invariant registry before scoping; whatever it finds beyond `pr_title` and `track` is in scope only if it stops a light-lane plan at a boundary. Anything else is reported, not fixed here.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — light-lane branch: `pr_title` producer before the capture, capture-source matrix
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` — `track` persist, optional title refinement after the bounded read
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` — `PrTitleMissing` message; `_capture_pr_title_present` only if the alternative in the verify-first clause is chosen
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_handshake_commands.py` — lane-correct `pr_title_missing` payload on `capture` and `verify`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md` — Step 13, read as the deep-lane producer list; edited only to point at the matrix
- OBSERVED: `test/plan-marshall/plan-marshall/test_lifecycle_handshake_e2e.py` — light-lane walk through the `2-refine` capture
- OBSERVED: `test/plan-marshall/plan-marshall/test_phase_handshake_capture_verify.py` — per-lane refusal payload beside the existing `pr_title_present` cases
- OBSERVED: `test/plan-marshall/plan-marshall/test_invariants.py` — `PrTitleMissing` message cases
- HYPOTHESIS: `test/plan-marshall/plan-marshall/test_light_lane_capture_sources.py` — new derived test for the capture-source matrix (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none. No other `live-blockers` plan edits `planning.md`, `light-lane.md`, `_invariants.py` or `_handshake_commands.py`.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` and `triage.md` in the same `workflow/` directory, edited by PLAN-LB-05 and PLAN-LB-06; and `manage-status/scripts/`, edited by PLAN-LB-09 and PLAN-LB-10. This plan reads `planning_lane` from status and adds no `manage-status` verb.
- Left out on purpose: truthful-signals PLAN-TRUTH-172 D0, D1 and D3 (the finalize branch table's missing arrival path for an empty-population verdict, and the transition-time phase-array invariant). They are unrelated to the light-lane stop.
- Left out on purpose: process-compliance PLAN-10 D2–D5. D2 (the mailbox probe mis-reading `source_id`) is already fixed by PR #1685. D3 (file input for `recipe-match` / `aspect-classify`), D4 (`phase_steps_complete` reading non-step bullets) and D5 (handshake-capture backfill) do not stop a light-lane plan at the refine boundary.
- Left out on purpose: whether a large scope should be routed to the light lane at all (the lane router's sizing). This plan fixes the documented lane; it does not change who enters it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-04-light-lane-refine-boundary.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
