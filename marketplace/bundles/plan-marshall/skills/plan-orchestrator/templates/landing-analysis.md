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

## Three-Layer Analysis

{The landing was read on three layers — the spec, the deliverable trace, and the
merged code — by {one read-only leaf | the orchestrator inline, because the
dispatch did not return}, and the orchestrator re-read every point recorded as
`checked` before writing it here. The reading is **by reading, no build, no test
run, no write**: what only a run could show is tagged `not shown by reading`,
never left as clean.}

- **Dispatch:** one read-only leaf per landing — reason: {why this landing got its own leaf}
- **Verdict:** layer 1 {clean | findings}; layer 2 {clean | findings}; layer 3 {clean | findings | not shown by reading} —
  every layer that carried a finding is named here, so a layer-3 defect is visible
  without reading the section.

### Layer 1 — Specified

{Is the spec sound: are its premises and its Done-when conditions consistent with
each other and with `main`? Each finding names the spec line and what contradicts
it.}

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| {none, or L1-N} | {claim} | {checked \| not_shown_by_reading} | {file:line} |

**Layer 1 verdict:** {clean | findings — N}

### Layer 2 — Implemented

{Does each deliverable trace to code and to a test that can fail? Name every file
the diff touched that no deliverable explains, and every claim of the lane's
report the diff does not bear out.}

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| {deliverable} | {file:line} | {test} | {path or claim, or none} | {checked \| not_shown_by_reading} |

**Layer 2 verdict:** {clean | findings — N}

### Layer 3 — Correct

{Is the merged code free of defects — invariants, boundaries, error paths,
concurrency, resource handling and the project's code rules? Each defect carries
the line, the triggering input and the effect. A layer-3 finding is reported to
the operator at once and is never fixed inline; it becomes a staged fix-plan spec
only on the operator's word.}

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| {none, or L3-N} | {file:line} | {input} | {effect} | {blocker \| major \| minor \| info} |

**Layer 3 not shown by reading:** {none, or L3-N: the conclusion, and what only a run could show}

**Layer 3 verdict:** {clean | findings — N | not shown by reading — N}

### Conformance to the Project's Own Rules

{The project's own rules — `CLAUDE.md` and the code rules it names — checked
against the merged code. Each row names the rule source and its verdict.}

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| {CLAUDE.md § …} | {rule} | {conforms \| deviates \| not_shown_by_reading} | {file:line} |

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
- Sonar: {the landing's `step.sonar-roundtrip.open_issue_count` and `open_issue_rules` against what
  this analysis can see of the merge head — the measured figure, or `unknown` for a failed read
  (never `0`), or `n/a` for a project without Sonar. Compare the measured figure with the lane's own
  claim: a landing that reports a clean run beside a non-zero count, or a `0` the read never
  measured, is an anomaly.}

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
