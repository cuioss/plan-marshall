# Epic: {Epic Title}

slug: {slug}

> Hand-written narrative for one epic under `.plan/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. The ledger JSON files
> (`status.json`, the `queue/{PLAN-ID}.json` rows) and `resume_anchor.md` are the machine
> authority; any statement here that conflicts with them is stale prose.
>
> START HERE and the Ordered Queue are not in this file. They live in the generated,
> git-tracked `queue-view.md` next to it, written by `orchestrator regenerate-view` (and by
> `compact`). `queue-view.md` is never hand-edited. A merge conflict in it is never merged by
> hand: merge the source files, run
> `python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view --slug {slug}`
> on the merged tree, and `git add` the result.

## Vision

{2-5 sentences: the long-running goal this epic pursues, why it is too large for one plan,
and what "done" looks like at the epic level.}

## Queue annotations

{Per-row narrative the generated view cannot derive — why a row is parked, what a running plan
is waiting on, a sequencing caveat, a disjointness note, an operator caveat on a queue entry —
keyed by plan id. The row's status, workstream, and surface are in `queue-view.md`; this zone
carries only what they cannot express.}

- {PLAN-NN} — {annotation the generated view does not produce}

## Decisions

{One entry per recorded decision — append-only, newest last. This section is a curated
human-facing VIEW; the authoritative append-only record is `logs/decision.log`, written via
`manage-logging --store orchestrator` (decision verb). Because entries carry rationale and
alternatives the log summary need not, this section is NARRATIVE — no script writes it.}

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
