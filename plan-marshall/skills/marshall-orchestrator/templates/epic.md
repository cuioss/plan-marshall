# Epic: {Epic Title}

slug: {slug}

> Ledger document for one epic under `.plan/local/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-marshall-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

{2-5 sentences: the long-running goal this epic pursues, why it is too large for one plan,
and what "done" looks like at the epic level.}

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary --slug {slug}
     Paste the returned block verbatim between the markers. -->

<!-- BEGIN GENERATED: resume-summary -->
{generated resume summary — queue, running/parked plans, resume anchor}
<!-- END GENERATED: resume-summary -->

## Ordered Queue

{One row per staged/queued plan, in intended launch order. Status mirrors status.json
(`plans[].status`) — reconcile from status.json to here, never the reverse.}

| # | Plan | Workstream | Status | Surface (expected) | Notes |
|---|------|------------|--------|--------------------|-------|
| 1 | PLAN-01-{slug} | WS-01 | staged | {files/modules touched} | {sequencing or disjointness note} |

## Decisions

{One entry per recorded decision — append-only, newest last. Every entry here is also
logged via `manage-logging --store orchestrator` (decision verb).}

- {YYYY-MM-DD} — {decision statement, alternatives considered, rationale}

## Open Defects

{Known defects surfaced by landings or observations that are not yet owned by a staged
plan. When a defect is folded into a plan spec, move it out of this list and note the
owning PLAN-NN.}

- {defect statement} — {source: landing PLAN-NN / observation / operator paste}

## Watches

{Mid-flight observations that need monitoring but no immediate action — signals to
re-check at the next landing or session. Retire a watch when it resolves or graduates
into a defect/plan.}

- {watch statement} — {trigger to re-check}
