envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=candidate-lesson
created=2026-08-25T07:21:55Z

component=plan-marshall:phase-6-finalize
category=bug
title=A finalize step re-dispatched after outcome=failed skips the resolve seam the [DISPATCH] emission rides

# The finalize retry path has no dispatch instrumentation at all

## Context

`pre-submission-self-review` fired 7 times in this plan. `logs/work.log` carries `[DISPATCH]` lines for exactly 2 of them (18:18:33 and 19:34:38). Rounds 3 through 7 — five dispatched `execution-context-level-5` envelopes consuming an estimated 1.2M tokens — left no dispatch evidence whatsoever.

## Root cause

`phase-6-finalize/standards/dispatch-inline-split.md` states that the `[DISPATCH]` emission "rides the `effort resolve-target` **resolve seam** (a per-firing side effect of the resolve each dispatch performs)". `logs/decision.log` carries **zero** `(plan-marshall:manage-config) effort resolve-target` entries between 2026-08-24T19:34:38Z and 2026-08-25T05:38:07Z — the entire 10-hour window in which rounds 3-7 ran. The retry path re-dispatches a `failed` step without re-entering the resolve seam, so no emission is produced.

This also makes the failure invisible to the audit that exists to catch it: `execution-context-dispatch-audit`'s `shape_violation` check pairs a *resolve* against a *dispatch*. Here neither record exists, so the pairing finds nothing to be unmatched.

## Proposed action

Emit the `[DISPATCH]` line at the dispatch site rather than as a side effect of the resolve, or force the retry path back through `effort resolve-target`. Add a population-derived assertion: for each step in `phase_steps`, `firing_count` must equal the number of matching `[DISPATCH]` lines.

## Evidence

- aspect: execution-context-dispatch-audit — `dispatch_coverage_violation` x3
- `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]`: `firing_count: 5` for a step whose own `display_detail` says "7 rounds"
- `logs/decision.log`: no resolve entries in a 10h window spanning five dispatches
- `dispatch-inline-split.md` line 15 states the emission rides the resolve seam and asserts this "is **not** an explanation for any past missed `[DISPATCH]` emission" — on the retry path it is exactly the explanation
