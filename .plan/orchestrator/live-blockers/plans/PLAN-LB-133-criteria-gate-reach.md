# PLAN-LB-133: The criteria gate's mechanisms are recorded, reachable from the light lane and checked, and the documents state what they do

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-133-criteria-gate-reach.md` and is queued as one row file, `queue/PLAN-LB-133.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Regrouped on the operator's word of 2026-11-09 from the parked PLAN-LB-75 (the remainder after PLAN-LB-105 and PLAN-LB-125 absorbed
> its D1 exemptions and its D3) and the review-support documentation deliverable of PLAN-LB-41. Every claim was re-grounded against
> `main` at `9cd644892` by a read-only leaf on 2026-11-09. Dropped with reason: the head-bound override (PLAN-LB-75 D4, first bullet):
> `_review_closed_reason` (`_criteria_snapshot.py` L812-839) is sticky for every head on purpose (its comment at L1895-1898 says so),
> so a later unmet criterion on a newer head is closed by design and not a defect; only the `superseded_by` check is carried. Shipped
> at `9cd644892` and not carried: `run_open_criteria` applies the review-dropped, review-closed, superseded and authorized exemptions
> (it delegates to `open_criteria`, `_criteria_snapshot.py` L1830-1935; PLAN-LB-125, `bbe421f15`); the `SKILL.md` routing of
> `refreeze_requires_decision` (`phase-3-outline/SKILL.md` L677-680). **Each deliverable is its own outline deliverable, and each
> Done-when is its own success criterion. Do not merge them.** Every Done-when below fails at `9cd644892` unless it says "holds at".
> No Sonar. No token or measurement work.

## Objective

The completion gate computes a `criteria_gate` note that is returned by the transition and never persisted, reads a
`functional_review_drop_reason` metadata key nothing writes, lets a `superseded_by` name anything, and the light lane halts as an
error on a re-freeze decision it cannot ask the operator about. The documents state a rule the gate no longer has ("a criterion is
open until the sealed verdict grades it met") and the private `review_support` modules are documented nowhere. This plan makes the
mechanisms reachable and checked and the documents true.

## Deliverables

1. **`criteria_gate` is recorded, and the drop reason has a writer or is removed.**
   - `criteria_gate` (`_cmd_lifecycle.py` L1271-1274, L1830-1837) is set on the transition result after `write_status` (L1818), so it is
     not persisted. It is stored in the plan's status record and shown by the finalize output, not only returned by the transition.
   - `functional_review_drop_reason` (read at `_criteria_snapshot.py` L1821, delegated from `_cmd_lifecycle.py` L1255-1268) is read
     and never written; the reader falls back to scope or "not scheduled", so the dead key only loses the stated reason. It gets a
     writer where a dropped review is recorded, or the read is removed; decide at outline and record why.

   *Done when:* each of these fails at `9cd644892`: after a dropped-review completion, `criteria_gate` is readable from the status
   record; a dropped-review completion whose manifest carries a stated reason shows that reason (or the read is gone and a test
   asserts no other consumer reads the key).

2. **A re-freeze decision in the light lane has a documented path, and the decision is recorded.**
   - `phase-3-outline/workflow/light-lane.md` (L280) halts every non-success `snapshot-criteria` as `status: error`. It routes a
     `refreeze_requires_decision` result to a prompt-required envelope that the dispatching context turns into the operator question
     and `criteria-refreeze-authorize` (the `SKILL.md` already does so at L677-680); the lane runs as a dispatched envelope and cannot
     ask the operator itself.
   - `phase-6-finalize/workflow/functional-review.md` records the PLAN-LB-70 D3e decision (`criteria-authorize` wired,
     `verify-first` removed) beside the D4c record at L93.

   *Done when:* each of these fails at `9cd644892`: a doc test asserts `light-lane.md` names `refreeze_requires_decision`, the verb and
   the operator question; a doc test asserts `functional-review.md` records the D3e decision.

3. **`superseded_by` must name an existing deliverable.**
   - `_review_support_validate.py` (L443-445) requires a non-empty `superseded_by`, but it is free text; `open_criteria` closes a
     criterion on `verdict == superseded` alone (`_criteria_snapshot.py` L1910). A `superseded_by` that names no deliverable of the
     outline does not close its criteria, in the validator and in `open_criteria`.

   *Done when:* each of these fails at `9cd644892`: a deliverable with `superseded_by: "x"` that names no deliverable does not close
   its criteria and the validator names it. And this holds at `9cd644892` and must keep holding: a `superseded_by` naming an existing
   deliverable closes them; an override with a sealed verdict on the same head closes the criteria.

4. **The documents state what the gate does.**
   - `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` L68 ("A criterion is open until the review's sealed
     verdict grades it met") states the closing states listed at L51-55 plus authorized and superseded; "the gate refuses independently"
     stays true (`_cmd_lifecycle.py` L1353-1381) apart from the dropped-review exemption, and the text says so.
   - `phase-6-finalize/SKILL.md` L2341 (the `review_support` row of the scripts table) lists all the verbs of `review_support` (it
     lists attribution, domains and validate and not author-verdict, open-criteria or test-integrity) and carries a private-modules
     note naming what `_review_support_validate.py`, `_review_support_attribution.py` and `_review_support_integrity.py` own.

   *Done when:* each of these fails at `9cd644892`: a doc test asserts `triage.md` states the closing states and the exemptions and
   no longer states the old rule; a doc test asserts the `review_support` row lists every verb and names the three private modules.

Split guard: four deliverables, all in the criteria-gate family. D4 is documents only, D2 is one branch and one record, D3 is one
check in two places. If the outline finds D1's persistence needs a status-schema change, D1 splits off first.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- The gate stays as strict as it is: no exemption is added, and the sticky override is not changed.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where a Done-when says so.
- Executor regeneration only if a verb or a flag is added.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `run_open_criteria` (`phase-6-finalize/scripts/review_support.py` L611-614) delegates to `open_criteria` (`manage-solution-outline/scripts/_criteria_snapshot.py` L1830-1935), which applies review_dropped (L1892-1894), review_closed (L1899-1901), superseded (L1910) and authorized (L1916)
- OBSERVED: `criteria_gate` is assigned on the transition `result` after `write_status` (`manage-status/scripts/_cmd_lifecycle.py` L1271-1274, L1818, L1830-1837); a search over history finds it only in `_cmd_lifecycle.py` and `test_criteria_gate_completion_d1.py`
- OBSERVED: `functional_review_drop_reason` has no producer: it is read at `_criteria_snapshot.py` L1821 (the reader at L1798-1827) and written nowhere
- OBSERVED: `phase-3-outline/SKILL.md` L677-680 routes `refreeze_requires_decision` to the operator question, `criteria-refreeze-authorize` and one retry; `light-lane.md` L280 halts any non-success
- OBSERVED: `functional-review.md` L90 describes `criteria-authorize` and L93 carries the D4c record; no record of the D3e decision exists
- OBSERVED: `_review_closed_reason` (`_criteria_snapshot.py` L812-839, `OVERRIDE_HEADS_KEY` at L827) closes for any non-empty override-head list whatever the head, and the comment at L1895-1898 calls this intentional
- OBSERVED: the validator requires a non-empty `superseded_by` (`_review_support_validate.py` L443-445) but never checks it against the outline's deliverables
- OBSERVED: `triage.md` (`plan-marshall/workflow/triage.md` L40-68) was de-duplicated by PLAN-LB-125; L68 states the old rule; `phase-6-finalize/SKILL.md` L2341 lists attribution, domains and validate for `review_support`; no document names the three private modules
- HYPOTHESIS: persisting `criteria_gate` needs a metadata key and not a new status field — confirm at `manage-status` `write_status` and the finalize output (verify-at-outline, D1)
- HYPOTHESIS: no consumer other than the reader at L1821 reads `functional_review_drop_reason` — confirm by a content search over the tree before removing the read (verify-at-outline, D1)
- Verify-first clause (D1): decide whether the drop reason gets a writer or the read is removed; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — `criteria_gate` and the drop reason hand-off (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_criteria_snapshot.py` — the drop-reason read, `open_criteria` `superseded` (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/_review_support_validate.py` — the `superseded_by` check (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md` — L280 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — L93 (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` — L68 (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — L2341 (D4)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_criteria_gate_completion_d1.py` (D1, D4)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_criteria_integrity_d1.py` and `test/plan-marshall/phase-6-finalize/test_criteria_integrity_d2.py` (D3)
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_review_support.py` (D4)
- OBSERVED: `test/plan-marshall/manage-solution-outline/test_lb77_authorize_guard_d2.py` (D3)
- OBSERVED: `test/plan-marshall/phase-3-outline/test_phase_3_outline_qgate_bypass.py` — the directory's only test; a light-lane doc test is new in `test/plan-marshall/phase-3-outline/` (D2)

## Dependencies and Sequencing

- Depends on: PLAN-LB-70, PLAN-LB-105 and PLAN-LB-125 (shipped); `bbe421f15` is in the base.
- Overlaps with: PLAN-LB-138 on none of these files. PLAN-LB-131 (the foreign-PR gate) edits `phase-6-finalize/standards/archive-plan.md` and `manage-status/scripts/_cmd_lifecycle.py` (a comment at L877-879), so the two share `_cmd_lifecycle.py`: sequence them or accept the overlap prompt.
- Adjacent to: the finalize completion gate's refusal logic (`_cmd_lifecycle.py` L1353-1381), not edited.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-133-criteria-gate-reach.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
