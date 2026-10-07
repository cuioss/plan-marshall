envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T05:58:26Z

component=plan-marshall:automatic-review
category=bug

⛔ **FOLD REQUEST — this is the FOURTH and FIFTH independent sighting of one defect, not two new ones.** Prior reports from this repository: `-003` (a budget-exhaustion refusal counted as participation), `-005` (the quorum lying in both directions), `-012` (the false-RED routing into force-done and concealing a stale credit). Please fold onto whatever item absorbed those. Two more plans have now hit it independently, and BOTH again fixed it only plan-locally — so the project config still carries the stale token and the defect survives every workaround.

Relayed from Token-Sheriff epic `lessons-handling-26-09-04-01`: PLAN-07 (`test-signal-and-assertion-integrity`, PR #715 / `8f3b8aee`) and PLAN-11 (`carry-refresh-token-through-code-exchange`, PR #718 / `4e1e88db`).

## Sighting 4 — from PLAN-07 (finding `dbf1f3`)

# Candidate lesson: an unregistered required_bots token makes a review gate wrong in both directions at once

Source finding: `dbf1f3` (bug, severity error) in plan `test-signal-and-assertion-integrity`.
Component: `plan-marshall:automatic-review`; config surface `.plan/marshal.json`.

## Cross-repo routing note

The component belongs to the plan-marshall bundle, whose lessons store is a different
repository — carry it there rather than filing locally with `--allow-foreign-store`. The
`marshal.json` value itself is a TokenSheriff operator decision (see Fix below).

## Observation

`automatic-review.required_bots` names `pr-agent`. The bot registry knows only
`coderabbit`, `cuioss-review-bot` and `sourcery`, so `pr-agent` resolves to
`bot_state=unregistered_kind`. On PR #715 the reviewer that actually published was
`cuioss-review-bot`, with issue_comment evidence that it did review.

## Proposed rule

An unresolvable identity in a required-participant list breaks the gate in BOTH directions
simultaneously, and neither half is visible from a green run:

- a required reviewer is satisfied by nothing (no bot can ever match the token), and
- a reviewer that genuinely reviewed is reported as not having participated.

So a required-participant list must be validated against the registry at config-read time,
not merely consumed. A token that resolves to no known kind is a configuration error to
surface loudly, not a participant to keep waiting for.

Behaviour worth preserving: the guard correctly refused to clear `unregistered_kind` by
waiting or re-triggering (it cannot be cleared that way), logged the WARNING escalation,
and force-marked the step done via the documented escape hatch. The condition was loud
rather than silent — that part worked.

## Fix (not applied in this run)

Set `automatic-review.required_bots` to name `cuioss-review-bot` in place of `pr-agent`.
Deliberately deferred: `required_bots` governs review gating for every plan in this
project, so it is an operator decision rather than a finalize-time edit, and this plan
already carried one `marshal.json` change.

## Negative control any fix must pass

After the rename, confirm `review_completeness` reports `cuioss-review-bot=participated`
on a PR it reviewed AND reports incomplete on one it has not.

---

## Sighting 5 — from PLAN-11

component=plan-marshall:automatic-review
category=bug
proposed_by=carry-refresh-token-through-code-exchange
signal_source=signal_automated_review_count

# Plan-local required_bots fix leaves the stale token in marshal.json, so every future plan re-blocks

`required_bots` in this project's configuration carried the retired token `pr-agent`, while the live
registry kind for the bot that actually reviews PRs here is `cuioss-review-bot`. The pre-merge
review-completeness barrier compares the bots that actually reviewed against `required_bots`, so the
retired token could never be proven and the barrier reported an unprovable gap. The run paid a full
loop-back iteration on `automatic-review` before the mismatch was identified.

## What was actually done in this run

The correction was applied **plan-locally** (through this plan's step-params), not to the project's
`marshal.json`. That unblocked this plan and nothing else.

## Why that is the defect worth recording

The plan-local fix is invisible to the next plan. `marshal.json` still carries `pr-agent`, so:

- every future plan in this repository reproduces the same barrier block,
- each one pays its own loop-back iteration to rediscover the same cause,
- and the repeated cost is attributed to the review step rather than to a one-line configuration
  drift.

A plan-local override that resolves a **project-scoped** configuration defect is a workaround, not a
fix. Where the wrong value lives is where the correction has to land.

## Corrective rule

When a run discovers that a project-scoped configuration value is stale (a retired bot token, a
renamed registry kind, a moved path), the run must either:

1. correct the project-scoped value at its source (`marshal.json`, via `manage-config`) as part of the
   plan, or
2. record an explicit, named follow-up for that correction

before applying a plan-local override. A plan-local override applied silently, with the stale
project value left in place, is the shape to reject.

## Secondary observation

The barrier's failure message names the unproven bot token but does not distinguish "this bot has
not reviewed yet" from "this token names no bot the registry knows about". Those are different
faults with different remedies, and the second one is a configuration error that could be reported
as such at the point the token is read, rather than surfacing as a never-satisfied wait.

## Provenance

Observed during the `6-finalize` run of plan
`carry-refresh-token-through-code-exchange` (PR #718). `automatic-review` shows
`firing_count: 2` with a `loop_back` prior firing attributable to this cause.
