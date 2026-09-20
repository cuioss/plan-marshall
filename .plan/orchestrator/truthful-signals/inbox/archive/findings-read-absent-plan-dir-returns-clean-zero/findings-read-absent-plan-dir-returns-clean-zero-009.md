envelope_version=1
sender_type=plan
sender_id=findings-read-absent-plan-dir-returns-clean-zero
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T14:16:29Z

component=plan-marshall:phase-6-finalize
category=bug
disposition=new
source_plan=findings-read-absent-plan-dir-returns-clean-zero
source_pr=1369
source_finding=814a5b

# review_commitments reconcile returns verdict clear over a population that is empty by step ordering, not by evidence

## Provenance

Q-Gate finding `814a5b` (6-finalize), resolved `taken_into_account` and explicitly **"Routed to
the truthful-signals epic, not fixed here."** No inbox message carried it.

## Observed live

`finalize-step-simplify` (order 9) ran `review_commitments reconcile` and received:

```
verdict: clear
deletions_considered: 26
commitments_considered: 0
conflicts[0]
```

The zero is **structural, not incidental**. The reconciler derives its commitments from
`pr-comment` findings. At order 9 the plan has no PR at all — `create-pr` is order 20. The
population it compares deletions against is therefore **necessarily empty on every run at this
position**, for every plan, forever.

## Why this is the epic's archetype located in step ordering

The verb itself is honest: it publishes `commitments_considered`, and its envelope already carries
`proves: removal_conflict_only` and `gates_merge: false`. But a caller reading `verdict: clear`
alone receives a confident pass from a check that had nothing to check. The defect is not in the
code — it is in **where the code is scheduled**.

It also fails to cover what a reader would assume it covers here. This run resolved 11 self-review
findings, several of them **by deleting prose**, and those are Q-Gate findings the seam does not
read. So the deletions most at risk of undoing an earlier commitment are exactly the ones outside
its population.

## What kept this run honest — and why that does not generalise

The `simplify` agent detected the vacuity itself, published `commitments_considered: 0` in its
report, **declined to cite the clear as corroboration**, and supplied per-item reasoning for all
26 deletions instead. That is agent judgement compensating for a structural defect. It is not a
property of the pipeline and cannot be relied on.

## Remedy (for the epic to scope) — three mutually exclusive options

1. Publish an explicit `vacuous` / `not_applicable` verdict, distinct from `clear`, whenever
   `commitments_considered == 0`. Cheapest; makes the zero legible without moving anything.
2. Move the reconcile after `create-pr`, so the population can be non-empty.
3. Widen the population to include the Q-Gate findings resolved in the same run — which is where
   the at-risk deletions actually live.

(1) and (3) are complementary; (2) alone still leaves prose-deletion conflicts unseen.
