# Landing Analysis: PLAN-NN — {Plan Title}

epic: {slug}
workstream: WS-NN
pr: {PR number/URL}

> Landing record for one shipped plan. Lives at `landings/PLAN-NN.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

{Compare what landed against the staged spec (plans/PLAN-NN-{slug}.md), deliverable by
deliverable: shipped-as-specified, shipped-modified, dropped, or added-unplanned. Name
the evidence checked (files, tests, PR diff) for each verdict.}

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| {deliverable} | shipped-as-specified | {file/test/PR evidence} |

## Metrics and Anomalies

{Token/duration/loop-back figures from the plan's metrics, plus anything anomalous:
retries, harness kills, unusually expensive phases, verification loop iterations.}

- Tokens: {total, and per-phase outliers}
- Duration: {wall time}
- Anomalies: {or none}

## Routing and Merge Behavior

{How the plan moved through finalize: review bots and their findings' dispositions,
CI outcome, merge path (queue/direct), rebase conflicts or re-verify signals — surface
collisions observed here feed the next pairing decision.}

- Review: {bots, actionable findings, dispositions}
- CI/merge: {outcome, path, conflicts}

## Reconciliation Actions

{The ledger updates this landing drives — each action is executed, not just listed, and
each names the sanctioned verb that performs it. The four updates to the plan's queue
row, `queue/PLAN-NN.json`, are one call each: `queue --transition` for the status,
`queue --set-row` for each of the three result fields; each call rewrites only that one
row file. The queue has two sanctioned write forms — single append via `queue --add-row`
(also how `decompose` seeds a queue) and single mutate via `queue --transition` /
`queue --set-row` — stated once in
`persona-plan-orchestrator/standards/orchestration-model.md` § The queue-write boundary.
There is no whole-queue write form, and a ledger file is never edited by direct file
access.}

- [ ] row `status` → `shipped` — `orchestrator queue --transition PLAN-NN --status shipped`
- [ ] row `pr` stamped — `orchestrator queue --set-row PLAN-NN --field pr --value {pr}`
- [ ] row `landing` stamped — `orchestrator queue --set-row PLAN-NN --field landing --value landings/PLAN-NN.md`
- [ ] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-NN --field plan_marshall_plan_id --value {plan_id}`
- [ ] epic.md narrative reconciled against the queue rows (queue annotations, retired items)
- [ ] {defect/watch opened or retired}
- [ ] resume anchor updated in `resume_anchor.md` — `manage-status update-field --field resume_anchor --store orchestrator`
- [ ] `queue-view.md` regenerated and committed with the row change — `orchestrator regenerate-view` (START HERE carries no `(!) missing:` marker once `pr` and `landing` above are stamped — the marker checks those two result links, not `plan_marshall_plan_id`)

## Follow-Ups

{New work this landing surfaces: fold into an existing staged spec, stage a new
plans/PLAN-NN-{slug}.md, or record as watch/defect above.}

- {follow-up and where it went}
