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

{The ledger updates this landing drives — each action is executed, not just listed:
status.json plan entry updated (status/pr/landing), epic.md queue row reconciled,
folded queue items retired, defects/watches opened or closed, resume_anchor updated,
START-HERE block regenerated.}

- [ ] status.json `plans[]` entry updated
- [ ] epic.md queue reconciled from status.json
- [ ] {defect/watch opened or retired}
- [ ] resume_anchor updated
- [ ] START-HERE block regenerated

## Follow-Ups

{New work this landing surfaces: fold into an existing staged spec, stage a new
plans/PLAN-NN-{slug}.md, or record as watch/defect above.}

- {follow-up and where it went}
