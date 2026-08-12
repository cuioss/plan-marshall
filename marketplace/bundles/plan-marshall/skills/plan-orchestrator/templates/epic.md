# Epic: {Epic Title}

slug: {slug}

> Ledger document for one epic under `.plan/local/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

{2-5 sentences: the long-running goal this epic pursues, why it is too large for one plan,
and what "done" looks like at the epic level.}

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug {slug}
     Paste the returned block verbatim between the markers.
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
{generated resume summary — queue, running/parked plans, resume anchor}
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. This is what makes the block above genuinely regenerable: the
     per-row notes the generator cannot produce (why a row is parked, what a running
     plan is waiting on, an operator caveat on a queue entry) have a home that a
     verbatim paste does not destroy. -->

- {PLAN-NN} — {annotation the generator does not produce}

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated in place by the compact stage (orchestrator.py compact --slug {slug}),
     which renders the derivable columns from status.json and the staged specs. Only the
     LIVE queue is rendered here — a shipped/landed row belongs in its landing record, not
     in the live queue. Per-row notes a reader wants to ADD go in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-01-{slug} | WS-01 | staged | {files/modules touched, from the spec's Expected Surface} |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers.
     A regeneration replaces only the table BETWEEN the markers, so everything written here
     survives it. This is where the per-row narrative the generator cannot derive lives — a
     sequencing caveat, a disjointness note, why a row is parked — keyed by plan id. -->

- {PLAN-NN} — {sequencing / disjointness / caveat the generator does not derive}

## Decisions

{One entry per recorded decision — append-only, newest last. This section is a curated
human-facing VIEW; the authoritative append-only record is `logs/decision.log`, written via
`manage-logging --store orchestrator` (decision verb). Because entries carry rationale and
alternatives the log summary need not, this section is NARRATIVE — the compact stage preserves
it verbatim and never regenerates it.}

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
