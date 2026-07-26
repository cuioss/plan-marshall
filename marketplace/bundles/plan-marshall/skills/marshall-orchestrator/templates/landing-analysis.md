# Landing Analysis: PLAN-NN — {Plan Title}

epic: {slug}
workstream: WS-NN
pr: {PR number/URL}

> Landing record for one shipped plan. Lives at `landings/PLAN-NN.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the analysis and
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
each names the sanctioned verb that performs it. The four `status.json` row updates are
one call each: `queue --transition` for the status, `queue --set-row` for each of the
three result fields. Never edit `status.json` by direct file access, and never stamp a
landing with the whole-array `manage-status update-field --field plans` rewrite — that
form is reserved for `decompose`'s bulk queue seed.}

- [ ] row `status` → `shipped` — `orchestrator queue --transition PLAN-NN --status shipped`
- [ ] row `pr` stamped — `orchestrator queue --set-row PLAN-NN --field pr --value {pr}`
- [ ] row `landing` stamped — `orchestrator queue --set-row PLAN-NN --field landing --value landings/PLAN-NN.md`
- [ ] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-NN --field plan_marshall_plan_id --value {plan_id}`
- [ ] epic.md queue reconciled from status.json
- [ ] {defect/watch opened or retired}
- [ ] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [ ] START-HERE block regenerated — `orchestrator resume-summary` (carries no `(!) missing:` marker once the three fields above are stamped)

## Follow-Ups

{New work this landing surfaces: fold into an existing staged spec, stage a new
plans/PLAN-NN-{slug}.md, or record as watch/defect above.}

- {follow-up and where it went}
