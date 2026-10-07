envelope_version=1
sender_type=plan
sender_id=misconfigured-reviewer-name-reads-missing-review
epic=review-apparatus
kind=candidate-lesson
created=2026-09-03T23:44:17Z

# The required_bots correction landed only in the plan-local manifest snapshot; tracked marshal.json still lists coderabbit as optional

**Component**: `plan-marshall:automatic-review`
**Category**: bug
**Source plan**: `misconfigured-reviewer-name-reads-missing-review` (PR #1392)
**State**: OPEN — an owed action, not a closed defect

## Context

Mid-run, the operator corrected this repository's review-bot configuration:

> "Operator correction: coderabbit is REQUIRED, not optional. The prior run settled
> `participation_complete=true` only because coderabbit's `refused_awaitable` sat in
> `optional_bots`, where the rate-window recovery is scoped out."

The correction was applied to the plan-local manifest snapshot only. Tracked
`.plan/marshal.json` was deliberately not touched, to avoid re-staling an already-green
push-freshness gate. That was the right call for this run and leaves a durable gap.

## Verified divergence

Read side by side, both at the time of this step:

`manage-execution-manifest step-params get --phase 6-finalize --step-id plan-marshall:automatic-review`
(the **plan-local snapshot**, corrected):

```text
required_bots: "cuioss-review-bot,coderabbit"
optional_bots: sourcery
review_rate_window_await: true
bot_lists_provenance: answered
```

`manage-config plan phase-6-finalize get --field steps` →
`plan-marshall:automatic-review` (**tracked `.plan/marshal.json`**, uncorrected):

```text
required_bots: cuioss-review-bot
optional_bots: "coderabbit,sourcery"
review_rate_window_await: false
bot_lists_provenance: answered
```

Two keys diverge, not one. `required_bots` / `optional_bots` is the operator's correction
and is unambiguously owed. `review_rate_window_await` (`true` in the snapshot, `false`
tracked) is a **second** divergence whose provenance this plan did not establish — it may
be a deliberate per-run knob rather than part of the correction, and it is reported here
as an observation to classify, not as an owed change.

Note that `bot_lists_provenance: answered` is identical on both sides. The provenance
marker says an operator answered the question; it does not say *which* answer is in force,
so it cannot discriminate the corrected snapshot from the uncorrected tracked config.

## Why this matters beyond one plan

Step params are snapshotted from tracked `marshal.json` into the plan-local manifest at
compose time. So every plan composed in this repository from now on starts from
`required_bots: cuioss-review-bot` with `coderabbit` in `optional_bots` — the exact
placement that let an empty `cuioss-review-bot` review satisfy the required-bot quorum
while no reviewer had read the diff. The correction does not propagate; it has to be
re-made per plan, by an operator who happens to remember, or `/marshall-steward` has to be
run once against the tracked config.

This is currently recorded only inside global lesson `2026-09-03-23-003` § "Proposed
action" item 4 — which is itself epic-invisible for the reason candidate 001 describes.
It is filed here so the epic holds it as an open item rather than inheriting it silently.

## Proposed action

1. Run `/marshall-steward` (Configuration) once against tracked `.plan/marshal.json` to
   move `coderabbit` from `optional_bots` into `required_bots`, and land it as an ordinary
   change through the normal PR flow.
2. Classify the `review_rate_window_await` divergence before touching it — establish
   whether `false` (tracked) or `true` (snapshot) is the intended default. Do not sweep it
   in with (1) on the assumption that both divergences share a cause.
3. Consider whether a bot-list placement that makes the required-bot quorum satisfiable
   with zero diff-readers should be rejected at config-read time. That is proposed action
   3 of lesson `2026-09-03-23-003` and belongs with it, not with this item.

## Evidence

- config: `manage-execution-manifest step-params get --plan-id misconfigured-reviewer-name-reads-missing-review --phase 6-finalize --step-id plan-marshall:automatic-review`
- config: `manage-config plan phase-6-finalize get --field steps` → `plan-marshall:automatic-review`
- global lesson `2026-09-03-23-003` § "Proposed action" item 4 (records the same owed item; epic-invisible)
- operator correction quoted above, decision.log `2026-09-03T18:27:30Z`
- sibling candidate 002 — the index of the epic-invisible corpus entries this one references
