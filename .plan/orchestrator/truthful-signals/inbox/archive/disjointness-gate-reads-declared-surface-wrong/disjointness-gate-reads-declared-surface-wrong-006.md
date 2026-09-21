envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:35:45Z

component=plan-marshall:phase-6-finalize
category=bug
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# The finalize dispatcher did not forward orchestrated/epic to plan-retrospective

## What happened

`plan-retrospective`'s Input Contract states:

> `orchestrated` — `true` when this plan was launched from an epic's staged plan spec
> ... In finalize-step mode the dispatcher forwards it (resolved once per finalize run
> at `phase-6-finalize/SKILL.md` Step 3 item 4b.a0); **this body MUST NOT recompute
> it.**

The `plan-marshall:plan-retrospective` dispatch for this plan carried `name`,
`plan_id`, `session_id`, `skills[]`, `workflow`, `WORKTREE` and `iteration` — and
**neither `orchestrated` nor `epic`**.

The plan is orchestrated. Its `request.md` `source_id` is
`.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-113-the-disjointness-gate-reads-a-declared-surface-wrong-in-both-directions.md`,
and `orchestrator inbox detect --source-id ...` returns `orchestrated: true`,
`epic: truthful-signals`.

## Why it matters

`orchestrated` is declared **optional** in the contract's Required column. The
ordinary reading of an absent optional boolean is `false`. On that reading, Step 5b
takes the `orchestrated: false` branch and every proposal is written to the **global
lessons store** via `manage-lessons add` — instead of to the epic inbox as
`kind: candidate-lesson` messages.

That is a silent wrong-destination corpus write returning `status: success`:

- the epic never receives the candidate lessons it owns;
- the global corpus gains lessons the orchestrator was supposed to adjudicate;
- the `already_closed` deletion path — explicitly prohibited on the orchestrated
  branch because "deleting a global lesson is a corpus mutation the orchestrator
  owns" — becomes reachable.

Nothing in the dispatch distinguishes "the dispatcher resolved this to false" from
"the dispatcher did not resolve it at all". The contract's own prohibition on
recomputing means a compliant body cannot defend itself.

## What this run did

Resolved `orchestrated` / `epic` through the documented two-call seam
(`manage-plan-documents request read --section source_id`, then
`orchestrator inbox detect --source-id`) — the seam the contract assigns to
user-invocable mode — and recorded the deviation, because defaulting to `false`
would have written to the wrong store.

## Remedy shape

Two options, not mutually exclusive:

1. Make `phase-6-finalize` Step 3 item 4b.a0 actually forward both fields on the
   `plan-marshall:plan-retrospective` dispatch (the resolution already happens once
   per finalize run).
2. Make the absence **distinguishable** rather than defaulted: require the field in
   finalize-step mode and refuse the dispatch when it is missing, the same way the
   dispatcher refuses a missing `plan_id`. An unresolved orchestration context should
   be a contract violation, not a `false`.
