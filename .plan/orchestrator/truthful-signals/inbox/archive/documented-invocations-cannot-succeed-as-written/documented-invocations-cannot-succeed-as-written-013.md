envelope_version=1
sender_type=plan
sender_id=documented-invocations-cannot-succeed-as-written
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T19:00:00Z

component=plan-marshall:phase-3-outline
category=bug

# A deep-lane outline reached its Q-Gate with an empty assessment substrate and nothing upstream noticed

The deep lane's discovery pass is what normally files `CERTAIN_INCLUDE` assessments. This plan routed
`planning_lane: deep`, ran its outline, and arrived at the outline Q-Gate with **zero** assessments
filed. Nothing between the lane decision and the gate reported the omission.

## Observed

Q-Gate finding `270654` (3-outline, resolution `taken_into_account`):

> `manage-findings assessment list --certainty CERTAIN_INCLUDE` returns `total_count 0` with
> `findings_store_state 'present'` — the store was genuinely resolved and scanned, and it is
> genuinely empty. `status.metadata.planning_lane` is `deep`, the lane whose discovery pass is what
> normally files these assessments, so an empty assessment substrate is not the expected steady state
> for this plan.

Consequence, as the finding records it: validator 2.2 (Assessment Coverage) and Step 5 (Missing
Coverage) had an **empty reference set**, so neither could return a verdict about the declared
mutation paths. They were recorded as UNEVALUATED rather than passed, and no per-file
"missing assessment" findings were emitted — *"26 findings derived from an empty reference set would
assert a conclusion the substrate cannot support."*

## What the gate got right, and what is still open

The gate's handling was exemplary and is **not** the defect: it refused to report green over a
population it never had, and it named the substrate explicitly. The residue is upstream — the plan
reached that gate at all. The remedy applied was manual (24 `CERTAIN_INCLUDE` + 3 `CERTAIN_EXCLUDE`
assessments filed at triage time, each grounded rather than asserted), which means the next
deep-lane plan whose discovery pass files nothing depends on a reviewer noticing the same thing
again.

## Rule

The deep lane's exit condition should assert its own product. A `planning_lane: deep` outline that
completes with `assessment list --certainty CERTAIN_INCLUDE` at `total_count: 0` over a *present*
store is a lane that did not run its discovery pass, and that is derivable at lane exit from data the
lane already has — one count against one lane field. Report it where the lane ends rather than
letting two downstream validators discover it as an absence.
